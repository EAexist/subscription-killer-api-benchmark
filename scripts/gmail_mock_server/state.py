from typing import Any, Dict, List, Optional, cast
import json

from datasets_shared.schema.models import Sample
from models import GmailMessage
from services.message_selector import MessageSelector
from utils.data_utils import DataProcessor, MessageUtils
from huggingface_hub import hf_hub_download
from datasets import load_dataset
from config import settings


class AppState:
    """
    Global application state singleton for managing data and services.
    Replaces scattered global variables with a centralized state management approach.
    """

    def __init__(self):
        self.samples: List[Sample] = []
        self.gmail_messages: List[GmailMessage] = []
        self.message_map: Dict[str, GmailMessage] = {}
        self._message_selector: Optional[MessageSelector] = (
            None  # Will be initialized in initialize()
        )
        self._initialized: bool = False

    def initialize(self):
        """
        Initialize all data and services on startup.
        This should be called once when the application starts.
        """
        if self._initialized:
            return  # Prevent multiple initializations

        try:
            # Load datasets repo truth data
            self.samples = self._load_latest_samples()
            print(f"✅ Loaded {len(self.samples)} items from datasets repo truth data")

            # Convert to GmailMessage format
            self.gmail_messages = DataProcessor.convert_to_gmail_messages(
                [s.to_raw_gmail_message() for s in self.samples]
            )
            print(f"✅ Processed {len(self.gmail_messages)} Gmail messages")

            # Create lookup map for performance
            self.message_map = MessageUtils.create_message_lookup_map(
                self.gmail_messages
            )

            # Initialize message selector service
            self._set_message_selector(MessageSelector(
                self.samples, 
                chunk_size=settings.n_emails_per_request,
                companies_per_chunk=settings.n_companies_per_chunk
            ))

            # Type assertion for the type checker - we know it's initialized now
            selector: MessageSelector = cast(MessageSelector, self._message_selector)

            # Print configuration
            print("🔧 Configuration:")

            # Print distribution statistics
            stats = selector.get_distribution_stats()
            print("📊 Distribution Statistics:")
            for field, value in stats.items():
                print(f"   {field}: {value}")

            self._initialized = True
            print("✅ AppState initialization completed successfully")

        except Exception as e:
            print(f"❌ Failed to initialize AppState: {e}")
            raise

    def _load_latest_samples(self)->List[Sample]:

        REPO_ID = "hyeon-expression/subscription-killer-synthetic-emails"
        EMAILS_LATEST_JSON_FILENAME = "data/emails/latest.json"

        local_file_path = hf_hub_download(
            repo_id=REPO_ID, 
            filename=EMAILS_LATEST_JSON_FILENAME,
            repo_type="dataset"
        )

        samples_path:str

        with open(local_file_path, "r") as f:
            data = json.loads(f.read())
            samples_path = data["relative_path"] 
        
        samples_dataset = load_dataset(
            REPO_ID,
            data_files=f"data/emails/{samples_path}",
            field=None,
            split="train"
        )
        
        samples = [Sample(**cast(dict[str, Any], item)) for item in samples_dataset]
        
        return samples

    def is_initialized(self) -> bool:
        """Check if the application state has been initialized."""
        return self._initialized

    @property
    def message_selector(self) -> MessageSelector:
        """Get the message selector, ensuring it's initialized."""
        if self._message_selector is None:
            raise RuntimeError("AppState not initialized. Call initialize() first.")
        return self._message_selector

    def _set_message_selector(self, selector: Optional[MessageSelector]) -> None:
        """Internal method to set the message selector."""
        self._message_selector = selector

    def reset(self):
        """Reset the application state (useful for testing)."""
        self.samples = []
        self.gmail_messages = []
        self.message_map = {}
        self._message_selector = None
        self._initialized = False


# Create a single instance - this is the singleton that will be used throughout the application
app_state = AppState()
