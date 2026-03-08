import os
import random
import sys
from typing import List, Optional

# Add the datasets path to Python path
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "datasets", "src"),
)

from models import GmailMessage


class MessageSelector:
    """Service for selecting messages using chunk-based worst case distribution."""

    def __init__(
        self,
        messages: List[GmailMessage],
        random_seed: Optional[int] = None,
    ):
        """
        Initialize the message selector with a list of messages.

        Args:
            messages: List of GmailMessage objects to select from (assumed to be unique templates)
            raw_data: Optional Sample objects (not used in simplified implementation)
            random_seed: Optional seed for reproducible shuffling. If None, shuffling is random.
        """
        self.messages = messages
        # Shuffle the entire dataset for randomization
        self.shuffled_messages = self.messages.copy()

        if random_seed is not None:
            random.seed(random_seed)

        random.shuffle(self.shuffled_messages)

        self._current_chunk_index = 0
        self._returned_message_indices = set()  # Track indices of returned messages

    def select_messages(self, count: int = 1) -> List[GmailMessage]:
        """
        Select messages using chunk-based worst case distribution strategy.

        This implements the "Cold Start" worst case where the system sees
        zero repeat templates in the first N/chunk_size requests.

        Args:
            count: Number of messages to select (defaults to 1)

        Returns:
            List of selected GmailMessage objects

        Raises:
            ValueError: When all messages have been exhausted and no new messages are available
        """

        # Check if we have enough unreturned messages
        available_messages = len(self.shuffled_messages) - len(
            self._returned_message_indices
        )
        if available_messages < count:
            raise ValueError(
                f"Cannot select {count} messages. Only {available_messages} unreturned messages available out of {len(self.shuffled_messages)} total messages."
            )

        selected_messages = []
        messages_to_select = count

        # Calculate starting position for this selection
        start_index = self._current_chunk_index

        # Find the next available unreturned message
        while messages_to_select > 0:
            current_idx = start_index % len(self.shuffled_messages)

            # Skip already returned messages
            if current_idx not in self._returned_message_indices:
                selected_messages.append(self.shuffled_messages[current_idx])
                self._returned_message_indices.add(current_idx)
                messages_to_select -= 1

            start_index += 1

            # Safety check - should never happen due to the earlier availability check
            if len(selected_messages) == len(self.shuffled_messages):
                break

        # Update current chunk index for next call
        self._current_chunk_index = start_index % len(self.shuffled_messages)

        return selected_messages

    def get_distribution_stats(self):
        """
        Get statistics about the current distributions.

        Returns:
            Dictionary with distribution statistics
        """
        return {
            "total_messages": len(self.messages),
            "returned_messages": len(self._returned_message_indices),
            "available_messages": len(self.shuffled_messages)
            - len(self._returned_message_indices),
            "current_chunk_index": self._current_chunk_index,
            "chunk_size": 50,  # Default chunk size
        }
