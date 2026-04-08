import os
import random
import re
import sys
from typing import Any, Dict, List, Optional
from collections import defaultdict, Counter, deque
from datetime import datetime, timezone
import uuid

# Add the datasets path to Python path
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "datasets", "src"),
)

from datasets_shared.schema.models import EmailTemplate, EmailTextParameterSet, Sample
from models import GmailMessage
from utils.data_utils import DataProcessor
from config import settings
from logging_config import setup_logging, get_logger

# Setup logging configuration
setup_logging()
logger = get_logger(__name__)


class MessageSelector:
    """Service for selecting messages using chunk-based distribution with company_id constraints."""

    def __init__(
        self,
        templates: List[EmailTemplate],
        parameters: List[EmailTextParameterSet],
        chunk_size: Optional[int] = None,
        companies_per_chunk: Optional[int] = None,
        random_seed: Optional[int] = None,
        n_companies: Optional[int] = None,
    ):
        """
        Initialize message selector with samples and prepare chunks.

        Args:
            templates: List of EmailTemplate objects to select from
            parameters: List of EmailTextParameterSet objects to use for parameter generation
            chunk_size: Size of each chunk (config.n_emails_per_request)
            companies_per_chunk: Number of different companies per chunk (config.n_companies_per_chunk)
            random_seed: Optional seed for reproducible shuffling. If None, uses config value.
            n_companies: Number of companies to use for weight calculation. If None, uses actual number of companies.
        """
        self._alpha = 1.0
        self._chunk_size = chunk_size or settings.n_emails_per_request
        self._companies_per_chunk = companies_per_chunk or settings.n_companies_per_chunk
        self._n_companies = n_companies or 20  # Default to 20 if not specified
        self._templates_by_company = self._prepare_templates(templates)
        self._param_iter = iter(parameters)
        self._message_map: Dict[str, GmailMessage] = {}

        # Use local Random instance for exact reproducibility
        # Priority: provided parameter > config value > None
        seed_to_use = random_seed or settings.random_seed
        self._rng = random.Random(seed_to_use) if seed_to_use is not None else random.Random()
        ranks = list(range(1, self._n_companies + 1))
        weights = [1 / (rank ** self._alpha) for rank in ranks]
        total = sum(weights)
        self._probs = [w / total for w in weights]
        
        # # Prepare chunks with company_id constraints
        # self._chunks = self.generate_chunks(samples_to_use)
        # self._current_chunk_index = 0

    @property
    def chunk_size(self) -> int:
        return self._chunk_size

    def get_messages(self, message_ids: List[str]) -> List[GmailMessage]:
        """
        Get messages by IDs.
        
        Args:
            message_ids: List of message IDs to retrieve
            
        Returns:
            List of GmailMessage objects
        """
        return [self._message_map[mid] for mid in message_ids]

    def get_first_message_id(self, addresses: list[str]):
        """
        Gmail API endpoint for getting first message ID by addresses.
        Returns the first message ID found from the given addresses.
        """
        for msg in self._message_map.values():
            if msg.senderEmail in addresses:
                return msg.id

        return next(iter(self._message_map.values())).id

    def select_messages(self) -> List[GmailMessage]:
        """
        Select the next chunk of messages.

        Returns:
            List of GmailMessage objects for the current chunk.
            Returns empty list when all chunks have been exhausted or parameters are exhausted.
        """
        templates = self._generate_chunk()
        
        # Convert to GmailMessage format
        gmail_messages = []
        for template in templates:
            try:
                params = next(self._param_iter)
            except StopIteration:
                # Parameters exhausted, return empty list
                logger.warning(f"⚠️ Parameters exhausted. Cannot generate more messages.")
                return []
                
            subject, snippet = template.subject, template.snippet
            param_dict = params.model_dump(by_alias=False)

            # Merge placeholders
            for key, val in param_dict.items():
                p = f"{{{{{key}}}}}"
                subject = subject.replace(p, str(val))
                snippet = snippet.replace(p, str(val))

            sample = Sample(
                id=str(uuid.uuid4()),
                subject=subject,
                snippet=snippet[:200],
                subscription_event_type=template.subscription_event_type,
                company_id=template.company_id,
                template_id=template.id,
            )
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
                templateId=template.id,
            )
            gmail_messages.append(gmail_message)
            self._message_map[gmail_message.id] = gmail_message
            logger.debug(f"Message: {template.company_id} {template.subscription_event_type} {gmail_message.subject} {gmail_message.snippet}")
        
        return gmail_messages

    def _prepare_templates(self, templates: List[EmailTemplate]) -> dict:
        """
        Prepare a subset of templates according to specific criteria:
        1. Pick first 20 unique company_id values
        2. For each company_id and each subscriptionEventType, pick calculated number of template_ids
        3. Return dictionary of company_id to templates
        
        Args:
            templates: List of all available templates
            
        Returns:
            Dictionary mapping company_id to list of filtered templates
        """
        from collections import defaultdict
        
        TEMPLATES_PER_EVENT_TYPE = 2

        templates_by_company = defaultdict(lambda: defaultdict(list))
        
        for template in templates:
            company_id = template.company_id
            event_type = getattr(template, 'subscription_event_type', 'unknown')
            templates_by_company[company_id][event_type].append(template)
        
        # Get the first 20 unique company_ids
        all_company_ids = sorted(templates_by_company.keys())
        selected_company_ids = all_company_ids[:self._n_companies]
        
        # Filter templates and flatten to company_id -> list structure
        filtered_templates_by_company = {}
        
        for company_id in selected_company_ids:
            company_events = templates_by_company[company_id]
            company_templates = []
            
            # Get all event types for this company
            all_event_types = sorted(company_events.keys())
            
            for event_type in all_event_types:
                event_templates = company_events[event_type]
                selected_templates = event_templates[:TEMPLATES_PER_EVENT_TYPE]
                company_templates.extend(selected_templates)
            
            filtered_templates_by_company[company_id] = company_templates
        
        total_templates = sum(len(templates) for templates in filtered_templates_by_company.values())
        logger.info(f"📊 Prepared {len(selected_company_ids)} companies, {total_templates} templates, {self._chunk_size} chunk_size")
        
        return filtered_templates_by_company

    def _weighted_choice(self, items, weights):
        """Sample one item with weights (with replacement)."""
        return random.choices(items, weights=weights, k=1)[0]
    
    def _weighted_sample_without_replacement(self, items, weights, k):
        """Sample k unique items using weights."""
        items = items[:]
        weights = weights[:]
        
        chosen = []
        for _ in range(k):
            picked = self._weighted_choice(items, weights)
            idx = items.index(picked)
            
            chosen.append(picked)
            
            # remove selected item
            items.pop(idx)
            weights.pop(idx)
        
        return chosen

    def _generate_chunk(self) -> List[EmailTemplate]:
        chunk = []
        chosen_companies = self._weighted_sample_without_replacement(
            list(self._templates_by_company.keys()),
            self._probs,
            self._companies_per_chunk
        )

        n_templates = self._chunk_size // self._companies_per_chunk

        for company_id in chosen_companies:
            templates = self._templates_by_company[company_id]
            selected_templates = random.choices(templates, k=n_templates)
            chunk.extend(selected_templates)            

        return chunk

    # def generate_chunks(self, samples) -> List[List[Sample]]:
    #     # Group samples by company_id into deques for O(1) popping
    #     samples_by_company = defaultdict(deque)
    #     for sample in samples:
    #         samples_by_company[sample.company_id].append(sample)
        
    #     available_companies = list(samples_by_company.keys())
        
    #     if len(available_companies) < self._companies_per_chunk:
    #         raise ValueError(f"Need {self._companies_per_chunk} companies, found {len(available_companies)}")

    #     # Shuffle internal samples for randomness within company
    #     for cid in samples_by_company:
    #         temp_list = list(samples_by_company[cid])
    #         self._rng.shuffle(temp_list)
    #         samples_by_company[cid] = deque(temp_list)

    #     chunks = []
        
    #     # Continue as long as we have enough unique companies to fill a chunk
    #     while True:
    #         # 1. Sort companies by remaining samples (descending)
    #         # This is the "Planning" part: always use the most abundant resources first
    #         active_companies = sorted(
    #             [cid for cid in samples_by_company if len(samples_by_company[cid]) > 0],
    #             key=lambda cid: len(samples_by_company[cid]),
    #             reverse=True
    #         )

    #         if len(active_companies) < self._companies_per_chunk:
    #             break # Cannot satisfy unique company constraint anymore

    #         # 2. Select the top K companies to participate in this chunk
    #         selected_cids = active_companies[:self._companies_per_chunk]
            
    #         # Check if these K companies combined have enough samples for a full chunk
    #         total_available_in_selection = sum(len(samples_by_company[cid]) for cid in selected_cids)
    #         if total_available_in_selection < self._chunk_size:
    #             # Even using all samples from the top K companies isn't enough
    #             break

    #         current_chunk = []
            
    #         # 3. Mandatory Phase: Take 1 from each to satisfy uniqueness
    #         for cid in selected_cids:
    #             current_chunk.append(samples_by_company[cid].popleft())
            
    #         # 4. Filler Phase: Fill remaining slots using weighted random selection
    #         remaining_needed = self._chunk_size - len(current_chunk)
            
    #         while remaining_needed > 0:
    #             # Filter companies that still have samples
    #             active_cids = [cid for cid in selected_cids if samples_by_company[cid]]
    #             if not active_cids:
    #                 break
                
    #             # Weighted random selection based on remaining samples
    #             weights = [len(samples_by_company[cid]) for cid in active_cids]
    #             cid = self._rng.choices(active_cids, weights=weights)[0]
                
    #             current_chunk.append(samples_by_company[cid].popleft())
    #             remaining_needed -= 1

    #         # 5. Finalize Chunk
    #         self._rng.shuffle(current_chunk)
    #         chunks.append(current_chunk)

    #     # 6. Shuffle the final chunk list for random chunk order
    #     self._rng.shuffle(chunks)

    #     return chunks

    # def select_messages(self) -> List[GmailMessage]:
    #     """
    #     Select the next chunk of messages.

    #     Returns:
    #         List of GmailMessage objects for the current chunk.
    #         Returns empty list when all chunks have been exhausted.
    #     """
    #     if self._current_chunk_index >= len(self._chunks):
    #         print(f"⚠️ All chunks exhausted. Total chunks: {len(self._chunks)}")
    #         return []
        
    #     # Get the current chunk of samples
    #     current_chunk_samples = self._chunks[self._current_chunk_index]
        
    #     # Convert to GmailMessage format
    #     gmail_messages = []
    #     for sample in current_chunk_samples:
    #         raw_message = sample.to_raw_gmail_message()
            
    #         # Get headers like DataProcessor does
    #         from_header_value = raw_message.get_header("From") or ""
    #         subject_header_value = raw_message.get_header("Subject") or ""
            
    #         # Parse "Name <email>" format using regex
    #         regex = r"^(.+)\s+<(.+)>$"
    #         match = re.match(regex, from_header_value.strip())
            
    #         if match:
    #             name = match.group(1).strip()
    #             email = match.group(2).strip()
    #         else:
    #             name = ""
    #             email = from_header_value.strip()
            
    #         gmail_message = GmailMessage(
    #             id=raw_message.id or "",
    #             internalDate=int(
    #                 datetime.now(timezone.utc).timestamp() * 1000
    #             ),  # Use current time as fallback
    #             senderName=name if name else None,
    #             senderEmail=email,
    #             subject=subject_header_value,
    #             snippet=raw_message.snippet,
    #         )
    #         gmail_messages.append(gmail_message)
        
    #     # Move to next chunk
    #     self._current_chunk_index += 1
        
    #     return gmail_messages

    # def get_distribution_stats(self):
    #     """
    #     Get statistics about the current distributions.

    #     Returns:
    #         Dictionary with distribution statistics
    #     """
    #     if not self._chunks:
    #         return {
    #             "total_samples": len(self.samples),
    #             "total_chunks": 0,
    #             "chunk_size": self._chunk_size,
    #             "current_chunk_index": 0,
    #             "remaining_chunks": 0,
    #             "companies_per_chunk": 5,
    #         }
        
    #     # Analyze company distribution in first few chunks for verification
    #     sample_chunk = self._chunks[0] if self._chunks else []
    #     company_counts = Counter(sample.company_id for sample in sample_chunk)
        
    #     return {
    #         "total_samples": len(self.samples),
    #         "total_chunks": len(self._chunks),
    #         "chunk_size": self._chunk_size,
    #         "companies_per_chunk": self._companies_per_chunk,
    #         "current_chunk_index": self._current_chunk_index,
    #         "remaining_chunks": len(self._chunks) - self._current_chunk_index,
    #         "sample_chunk_companies": dict(company_counts),
    #     }

    # def _prepare_samples(self, samples: List[Sample]) -> List[Sample]:
    #     """
    #     Prepare a subset of samples according to specific criteria:
    #     1. Pick first 20 unique company_id values
    #     2. For each company_id and each subscriptionEventType, pick calculated number of template_ids
    #     3. Use all samples for selected template_ids (10 samples per template)
        
    #     Args:
    #         samples: List of all available samples
            
    #     Returns:
    #         List of filtered samples meeting the criteria
    #     """
    #     from collections import defaultdict
    #     from math import ceil
        
    #     # Calculate total emails needed and required templates
    #     total_emails_needed = settings.n_emails_per_request * settings.n_requests
    #     TEMPLATES_PER_EVENT_TYPE = 2
    #     NUM_EVENT_TYPES = 5
        
    #     # Calculate required templates per event type (ceiling up)
    #     # samples_per_template = ceil(total_emails_needed / (NUM_EVENT_TYPES * TEMPLATES_PER_EVENT_TYPE * self._n_companies))
    #     # print(f"📊 Sample prep: {total_emails_needed} emails, {samples_per_template} samples/template")
        
    #     # Group samples by company_id, subscriptionEventType, and template_id
    #     samples_by_hierarchy = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        
    #     for sample in samples:
    #         company_id = sample.company_id
    #         event_type = getattr(sample, 'subscription_event_type', 'unknown')
    #         template_id = getattr(sample, 'template_id', 'unknown')
    #         samples_by_hierarchy[company_id][event_type][template_id].append(sample)
        
    #     # Get the first 20 unique company_ids
    #     all_company_ids = sorted(samples_by_hierarchy.keys())
    #     selected_company_ids = all_company_ids[:self._n_companies]
        
    #     filtered_samples = []
        
    #     for company_id in selected_company_ids:
    #         company_events = samples_by_hierarchy[company_id]
            
    #         # Get all event types for this company
    #         all_event_types = sorted(company_events.keys())
            
    #         for event_type in all_event_types:
    #             event_templates = company_events[event_type]
                
    #             # Get the calculated number of template_ids for this event type
    #             all_template_ids = sorted(event_templates.keys())
    #             selected_template_ids = all_template_ids[:TEMPLATES_PER_EVENT_TYPE]
                
    #             for template_id in selected_template_ids:
    #                 # Add all samples for this template (should be 10 per template)
    #                 template_samples = event_templates[template_id]
    #                 filtered_samples.extend(template_samples)
        
    #     print(f"📊 Prepared {len(selected_company_ids)} companies, {len(filtered_samples)} samples")
        
    #     return filtered_samples
