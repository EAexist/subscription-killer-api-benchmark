import os
import random
import re
import sys
from typing import List, Optional
from collections import defaultdict, Counter, deque
from datetime import datetime, timezone

# Add the datasets path to Python path
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "datasets", "src"),
)

from datasets_shared.schema.models import Sample
from models import GmailMessage
from utils.data_utils import DataProcessor


class MessageSelector:
    """Service for selecting messages using chunk-based distribution with company_id constraints."""

    def __init__(
        self,
        samples: List[Sample],
        chunk_size: int,
        companies_per_chunk: int,
        random_seed: Optional[int] = None,
    ):
        """
        Initialize the message selector with samples and prepare chunks.

        Args:
            samples: List of Sample objects to select from
            chunk_size: Size of each chunk (config.n_emails_per_request)
            companies_per_chunk: Number of different companies per chunk (config.n_companies_per_chunk)
            random_seed: Optional seed for reproducible shuffling. If None, shuffling is random.
        """
        self.samples = samples
        self.chunk_size = chunk_size
        self.companies_per_chunk = companies_per_chunk
        
        if random_seed is not None:
            random.seed(random_seed)

        # Prepare chunks with company_id constraints
        self._chunks = self._prepare_chunks()
        self._current_chunk_index = 0

    def _prepare_chunks(self) -> List[List[Sample]]:
        # Group samples by company_id into deques for O(1) popping
        samples_by_company = defaultdict(deque)
        for sample in self.samples:
            samples_by_company[sample.company_id].append(sample)
        
        available_companies = list(samples_by_company.keys())
        
        if len(available_companies) < self.companies_per_chunk:
            raise ValueError(f"Need {self.companies_per_chunk} companies, found {len(available_companies)}")

        # Shuffle internal samples for randomness within the company
        for cid in samples_by_company:
            temp_list = list(samples_by_company[cid])
            random.shuffle(temp_list)
            samples_by_company[cid] = deque(temp_list)

        chunks = []
        
        # Continue as long as we have enough unique companies to fill a chunk
        while True:
            # 1. Sort companies by remaining samples (descending)
            # This is the "Planning" part: always use the most abundant resources first
            active_companies = sorted(
                [cid for cid in samples_by_company if len(samples_by_company[cid]) > 0],
                key=lambda cid: len(samples_by_company[cid]),
                reverse=True
            )

            if len(active_companies) < self.companies_per_chunk:
                break # Cannot satisfy unique company constraint anymore

            # 2. Select the top K companies to participate in this chunk
            selected_cids = active_companies[:self.companies_per_chunk]
            
            # Check if these K companies combined have enough samples for a full chunk
            total_available_in_selection = sum(len(samples_by_company[cid]) for cid in selected_cids)
            if total_available_in_selection < self.chunk_size:
                # Even using all samples from the top K companies isn't enough
                break

            current_chunk = []
            
            # 3. Mandatory Phase: Take 1 from each to satisfy uniqueness
            for cid in selected_cids:
                current_chunk.append(samples_by_company[cid].popleft())
            
            # 4. Filler Phase: Fill the remaining slots from the same selection
            # Prioritize the companies that still have the most samples
            remaining_needed = self.chunk_size - len(current_chunk)
            
            while remaining_needed > 0:
                # Re-sort selection to keep it optimal, or just greedily drain the top
                selected_cids.sort(key=lambda cid: len(samples_by_company[cid]), reverse=True)
                
                cid = selected_cids[0]
                take_amount = min(remaining_needed, len(samples_by_company[cid]))
                
                for _ in range(take_amount):
                    current_chunk.append(samples_by_company[cid].popleft())
                
                remaining_needed -= take_amount

            # 5. Finalize Chunk
            random.shuffle(current_chunk)
            chunks.append(current_chunk)

        # 6. Shuffle the final chunk list for random chunk order
        random.shuffle(chunks)

        return chunks
    
    def _create_optimal_chunks(self, samples_by_company, available_companies, samples_per_company, target_chunks):
        """
        Create optimal chunks using mathematical planning to maximize sample utilization.
        """
        chunks = []
        company_usage = {company_id: 0 for company_id in available_companies}
        
        for chunk_idx in range(target_chunks):
            # Select companies with remaining samples, prioritizing those with most samples left
            companies_with_samples = [
                company_id for company_id in available_companies 
                if company_usage[company_id] < samples_per_company
            ]
            
            if len(companies_with_samples) < self.companies_per_chunk:
                break  # Not enough companies with remaining samples
            
            # Sort by remaining samples (descending) to prioritize companies with most samples left
            companies_with_samples.sort(key=lambda cid: samples_per_company - company_usage[cid])
            
            # Select companies for this chunk
            companies_for_chunk = companies_with_samples[:self.companies_per_chunk]
            
            # Calculate flexible distribution for this chunk
            chunk_samples = []
            remaining_size = self.chunk_size
            
            # Distribute samples evenly, but allow flexibility
            base_distribution = remaining_size // self.companies_per_chunk
            extra_samples = remaining_size % self.companies_per_chunk
            
            # Assign samples to companies
            for i, company_id in enumerate(companies_for_chunk):
                # Calculate how many samples this company can contribute
                max_possible = min(
                    base_distribution + (1 if i < extra_samples else 0),
                    samples_per_company - company_usage[company_id]
                )
                
                # Take samples from this company
                start_pos = company_usage[company_id]
                end_pos = start_pos + max_possible
                
                if end_pos <= len(samples_by_company[company_id]):
                    chunk_samples.extend(samples_by_company[company_id][start_pos:end_pos])
                    company_usage[company_id] += max_possible
                    remaining_size -= max_possible
            
            # If we still need more samples to reach chunk_size, distribute from companies with most remaining
            if remaining_size > 0:
                # Sort companies by remaining samples again
                remaining_companies = [
                    cid for cid in companies_for_chunk 
                    if company_usage[cid] < samples_per_company
                ]
                remaining_companies.sort(key=lambda cid: samples_per_company - company_usage[cid], reverse=True)
                
                for company_id in remaining_companies:
                    if remaining_size <= 0:
                        break
                    
                    can_take = min(remaining_size, samples_per_company - company_usage[company_id])
                    start_pos = company_usage[company_id]
                    end_pos = start_pos + can_take
                    
                    if end_pos <= len(samples_by_company[company_id]):
                        chunk_samples.extend(samples_by_company[company_id][start_pos:end_pos])
                        company_usage[company_id] += can_take
                        remaining_size -= can_take
            
            # Verify chunk requirements
            if len(chunk_samples) == self.chunk_size:
                company_ids_in_chunk = [sample.company_id for sample in chunk_samples]
                unique_companies = set(company_ids_in_chunk)
                
                if len(unique_companies) >= self.companies_per_chunk:
                    # Shuffle the chunk to randomize order
                    random.shuffle(chunk_samples)
                    chunks.append(chunk_samples)
                else:
                    print(f"⚠️ Chunk {chunk_idx} failed: only {len(unique_companies)} companies, need {self.companies_per_chunk}")
                    break
            else:
                print(f"⚠️ Chunk {chunk_idx} failed: only {len(chunk_samples)} samples, need {self.chunk_size}")
                break
        
        return chunks

    def select_messages(self) -> List[GmailMessage]:
        """
        Select the next chunk of messages.

        Returns:
            List of GmailMessage objects for the current chunk

        Raises:
            ValueError: When all chunks have been exhausted
        """
        if self._current_chunk_index >= len(self._chunks):
            raise ValueError(
                f"All chunks have been exhausted. Total chunks: {len(self._chunks)}"
            )
        
        # Get the current chunk of samples
        current_chunk_samples = self._chunks[self._current_chunk_index]
        
        # Convert to GmailMessage format
        gmail_messages = []
        for sample in current_chunk_samples:
            raw_message = sample.to_raw_gmail_message()
            
            # Get headers like DataProcessor does
            from_header_value = raw_message.get_header("From") or ""
            subject_header_value = raw_message.get_header("Subject") or ""
            
            # Parse "Name <email>" format using regex
            regex = r"^(.+)\s+<(.+)>$"
            match = re.match(regex, from_header_value.strip())
            
            if match:
                name = match.group(1).strip()
                email = match.group(2).strip()
            else:
                name = ""
                email = from_header_value.strip()
            
            gmail_message = GmailMessage(
                id=raw_message.id or "",
                internalDate=int(
                    datetime.now(timezone.utc).timestamp() * 1000
                ),  # Use current time as fallback
                senderName=name if name else None,
                senderEmail=email,
                subject=subject_header_value,
                snippet=raw_message.snippet,
            )
            gmail_messages.append(gmail_message)
        
        # Move to next chunk
        self._current_chunk_index += 1
        
        return gmail_messages

    def get_distribution_stats(self):
        """
        Get statistics about the current distributions.

        Returns:
            Dictionary with distribution statistics
        """
        if not self._chunks:
            return {
                "total_samples": len(self.samples),
                "total_chunks": 0,
                "chunk_size": self.chunk_size,
                "current_chunk_index": 0,
                "remaining_chunks": 0,
                "companies_per_chunk": 5,
            }
        
        # Analyze company distribution in first few chunks for verification
        sample_chunk = self._chunks[0] if self._chunks else []
        company_counts = Counter(sample.company_id for sample in sample_chunk)
        
        return {
            "total_samples": len(self.samples),
            "total_chunks": len(self._chunks),
            "chunk_size": self.chunk_size,
            "companies_per_chunk": self.companies_per_chunk,
            "current_chunk_index": self._current_chunk_index,
            "remaining_chunks": len(self._chunks) - self._current_chunk_index,
            "sample_chunk_companies": dict(company_counts),
        }
