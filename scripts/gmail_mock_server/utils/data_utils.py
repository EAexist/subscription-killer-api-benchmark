import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, List

# Add the datasets path to Python path
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "datasets", "src"),
)

from datasets_shared.schema.models import RawGmailMessage
from models import GmailMessage


class DataProcessor:
    """Utility class for processing raw data into GmailMessage objects."""

    @staticmethod
    def convert_to_gmail_messages(
        raw_messages: List[RawGmailMessage], max_snippet_size: int = 400
    ) -> List[GmailMessage]:
        """
        Convert RawGmailMessage objects to GmailMessage format.

        Args:
            raw_messages: List of RawGmailMessage objects
            max_snippet_size: Maximum size for snippet (default: 400)

        Returns:
            List of GmailMessage objects
        """
        gmail_messages = []
        do_hide_prices = True

        for raw_message in raw_messages:
            # Get headers
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

            # Clean and process text (placeholder functions for now)
            def clean_email_text(text: str) -> str:
                return text.strip()

            def hide_prices(text: str) -> str:
                # Simple price hiding - replace common price patterns
                price_patterns = [
                    r"\$\d+(?:\.\d{2})?",  # $XX.XX
                    r"\d+(?:\.\d{2})?\s*USD",  # XX.XX USD
                    r"\d+(?:,\d{3})*(?:\.\d{2})?",  # 1,234.56
                ]
                for pattern in price_patterns:
                    text = re.sub(pattern, "[PRICE]", text)
                return text

            # Process subject and snippet
            processed_subject = clean_email_text(subject_header_value)
            if do_hide_prices:
                processed_subject = hide_prices(processed_subject)

            processed_snippet = clean_email_text(raw_message.snippet)
            if do_hide_prices:
                processed_snippet = hide_prices(processed_snippet)
            processed_snippet = processed_snippet[:max_snippet_size]

            gmail_message = GmailMessage(
                id=raw_message.id or "",
                internalDate=int(
                    datetime.now(timezone.utc).timestamp() * 1000
                ),  # Use current time as fallback
                senderName=name if name else None,
                senderEmail=email,
                subject=processed_subject,
                snippet=processed_snippet,
            )
            gmail_messages.append(gmail_message)

        return gmail_messages

    @staticmethod
    def _create_snippet(content: str, max_length: int = 100) -> str:
        """
        Create a snippet from content.

        Args:
            content: Full content string
            max_length: Maximum length of snippet

        Returns:
            Truncated snippet with ellipsis if needed
        """
        if len(content) <= max_length:
            return content
        return content[:max_length] + "..."


class MessageUtils:
    """Utility class for message operations."""

    @staticmethod
    def create_message_lookup_map(
        messages: List[GmailMessage],
    ) -> Dict[str, GmailMessage]:
        """
        Create a lookup map for efficient message retrieval by ID.

        Args:
            messages: List of GmailMessage objects

        Returns:
            Dictionary mapping message IDs to GmailMessage objects
        """
        return {msg.id: msg for msg in messages}

    @staticmethod
    def extract_message_ids(messages: List[GmailMessage]) -> List[str]:
        """
        Extract message IDs from a list of GmailMessage objects.

        Args:
            messages: List of GmailMessage objects

        Returns:
            List of message ID strings
        """
        return [msg.id for msg in messages]
