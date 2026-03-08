from typing import Dict, List, Optional, cast

from config import settings
from datasets_shared.loader.loader import Loader
from datasets_shared.schema.models import Sample
from models import GmailMessage
from services.message_selector import MessageSelector
from utils.data_utils import DataProcessor, MessageUtils


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
            loader = Loader()
            self.samples = loader.load_latest_samples()
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
            self._set_message_selector(MessageSelector(self.gmail_messages))

            # Type assertion for the type checker - we know it's initialized now
            selector: MessageSelector = cast(MessageSelector, self._message_selector)

            # Print configuration
            print("🔧 Configuration:")
            print(f"   Data file path: {settings.data_file_path}")

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
