import json
import os
from pathlib import Path
from typing import cast
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    
    # Number of different companies per chunk (no default value)
    n_companies_per_chunk: int = Field(..., alias="N_COMPANIES_PER_CHUNK")
    
    # Random seed for reproducible message selection
    random_seed: int = Field(default=42, alias="RANDOM_SEED")

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
