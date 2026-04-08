from typing import Any, Dict, List, Optional, cast
import json

from datasets_shared.schema.models import EmailTemplate, EmailTextParameterSet, Sample
from models import GmailMessage
from services.message_selector import MessageSelector
from utils.data_utils import DataProcessor, MessageUtils
from huggingface_hub import hf_hub_download
from datasets import load_dataset
from config import settings
from logging_config import setup_logging, get_logger

# Setup logging configuration
setup_logging()
logger = get_logger(__name__)


class AppState:
    """
    Global application state singleton for managing data and services.
    Replaces scattered global variables with a centralized state management approach.
    """

    def __init__(self):
        self.templates: List[EmailTemplate] = []
        self.parameters: List[EmailTextParameterSet] = []
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
            self.templates = self._load_latest_templates()
            self.parameters = self._load_latest_parameters()
            logger.info(f"✅ Loaded {len(self.templates)} templates, {len(self.parameters)} parameters from datasets repo")

            # Initialize message selector service
            self._set_message_selector(MessageSelector(
                self.templates,
                self.parameters,
                chunk_size=settings.n_emails_per_request,
                companies_per_chunk=settings.n_companies_per_chunk,
                random_seed=settings.random_seed
            ))

            # Type assertion for the type checker - we know it's initialized now
            selector: MessageSelector = cast(MessageSelector, self._message_selector)

            # Log configuration
            logger.info("🔧 Configuration:")

            # Print distribution statistics
            # stats = selector.get_distribution_stats()
            # print("📊 Distribution Statistics:")
            # for field, value in stats.items():
            #     print(f"   {field}: {value}")

            self._initialized = True
            logger.info("✅ AppState initialization completed successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize AppState: {e}")
            raise

    def _load_latest_data(self, data_type: str, model_class: type) -> List[Any]:
        """
        Shared helper method to load latest data from HuggingFace datasets.
        
        Args:
            data_type: Type of data ('emails', 'templates', or 'parameters')
            model_class: The model class to instantiate (Sample, EmailTemplate, or EmailTextParameterSet)
            
        Returns:
            List of instantiated model objects
        """
        REPO_ID = "hyeon-expression/subscription-killer-synthetic-emails"
        latest_json_filename = f"data/{data_type}/latest.json"

        local_file_path = hf_hub_download(
            repo_id=REPO_ID, 
            filename=latest_json_filename,
            repo_type="dataset"
        )

        data_path: str

        with open(local_file_path, "r") as f:
            data = json.loads(f.read())
            data_path = data["relative_path"] 
        
        dataset = load_dataset(
            REPO_ID,
            data_files=f"data/{data_type}/{data_path}",
            field=None,
            split="train"
        )
        
        # Convert datetime objects to strings before creating model instances
        processed_items = []
        for item in dataset:
            item_dict = cast(dict[str, Any], item)
            # Convert datetime objects to ISO format strings
            for key, value in item_dict.items():
                if hasattr(value, 'isoformat'):  # Check if it's a datetime-like object
                    item_dict[key] = value.isoformat()
            processed_items.append(model_class(**item_dict))
        
        return processed_items

    def _load_latest_templates(self) -> List[EmailTemplate]:
        """Load latest templates from HuggingFace datasets."""
        return self._load_latest_data("templates", EmailTemplate)

    def _load_latest_parameters(self) -> List[EmailTextParameterSet]:
        """Load latest parameters from HuggingFace datasets."""
        return self._load_latest_data("parameters", EmailTextParameterSet)

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
        self.templates = []
        self.parameters = []
        self._message_selector = None
        self._initialized = False


# Create a single instance - this is the singleton that will be used throughout the application
app_state = AppState()
