import json
import os
from pathlib import Path
from typing import cast
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_latest_data_file() -> str:
    base_dir = os.getenv("DATASET_PATH", "./scripts/gmail_mock_server/dataset")
    emails_dir = os.path.join(base_dir, "data/emails")

    latest_json_path = os.path.join(emails_dir, "latest.json")

    if not os.path.exists(latest_json_path):
        raise FileNotFoundError(
            f"Critical: @latest.json not found at {latest_json_path}"
        )

    with open(latest_json_path, "r") as f:
        latest_info = json.load(f)

    relative_path = latest_info["relative_path"]
    samples_path = os.path.normpath(os.path.join(emails_dir, relative_path))

    # 3. Verify the actual data file exists before returning
    final_path = samples_path.replace("\\", "/")
    if not os.path.exists(final_path):
        raise FileNotFoundError(
            f"Critical: Data file defined in @latest.json does not exist at {final_path}"
        )

    return final_path

CURRENT_DIR = Path(__file__).parent.resolve()
ENV_PATH = CURRENT_DIR / ".env"

class Settings(BaseSettings):
    """Application configuration settings."""

    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8080

    # Logging configuration
    enable_debug_logging: bool = False

    # Required field (no default value)
    n_emails_per_request: int = Field(..., alias="N_EMAILS_PER_REQUEST")

    # Modern Pydantic v2 configuration
    model_config = SettingsConfigDict(env_file=str(ENV_PATH), extra="ignore", env_prefix="")

# Global settings instance
settings = Settings() # type: ignore

# class DistributionField(str, Enum):
#     """Fields available for distribution-based message selection."""
#     SENDER_EMAIL = "senderEmail"
#     SENDER_NAME = "senderName"
#     SUBJECT = "subject"
#     CATEGORY = "category"

# class DistributionType(str, Enum):
#     """Types of distribution available for message selection."""
#     UNIFORM = "uniform"
#     WEIGHTED = "weighted"
#     RANDOM = "random"
