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
from config import settings


class MessageSelector:
    """Service for selecting messages using chunk-based distribution with company_id constraints."""

    def __init__(
        self,
        samples: List[Sample],
        chunk_size: Optional[int] = None,
        companies_per_chunk: Optional[int] = None,
        random_seed: Optional[int] = None,
    ):
        """
        Initialize message selector with samples and prepare chunks.

        Args:
            samples: List of Sample objects to select from
            chunk_size: Size of each chunk (config.n_emails_per_request)
            companies_per_chunk: Number of different companies per chunk (config.n_companies_per_chunk)
            random_seed: Optional seed for reproducible shuffling. If None, uses config value.
        """
        self.samples = samples
        self.chunk_size = chunk_size or settings.n_emails_per_request
        self.companies_per_chunk = companies_per_chunk or settings.n_companies_per_chunk
        
        # Use local Random instance for exact reproducibility
        # Priority: provided parameter > config value > None
        seed_to_use = random_seed or settings.random_seed
        self.rng = random.Random(seed_to_use) if seed_to_use is not None else random.Random()

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

        # Shuffle internal samples for randomness within company
        for cid in samples_by_company:
            temp_list = list(samples_by_company[cid])
            self.rng.shuffle(temp_list)
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
            self.rng.shuffle(current_chunk)
            chunks.append(current_chunk)

        # 6. Shuffle the final chunk list for random chunk order
        self.rng.shuffle(chunks)

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
