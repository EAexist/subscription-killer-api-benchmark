#!/usr/bin/env python3
"""
Centralized configuration for Langfuse analytics.
"""

import os
from pathlib import Path

# Base directory detection
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

def get_data_storage_root():
    """Get data storage root directory lazily."""
    return Path(
        os.getenv("DATA_STORAGE_ROOT", str(PROJECT_ROOT / "data-storage"))
    )

# Data paths (lazy evaluation)
def get_raw_data_dir():
    """Get raw data directory lazily."""
    return get_data_storage_root() / "results" / "raw"

# File naming patterns
CSV_NAMING_PATTERN = "benchmark_{version}_{date}.csv"

# Processing constants
DEFAULT_RETRY_COUNT = 5

# API endpoints and secrets (lazy evaluation)
def get_langfuse_host():
    """Get Langfuse host lazily."""
    return os.getenv("LANGFUSE_HOST")

def get_langfuse_secret_key():
    """Get Langfuse secret key lazily."""
    return os.getenv("LANGFUSE_SECRET_KEY")

def get_langfuse_public_key():
    """Get Langfuse public key lazily."""
    return os.getenv("LANGFUSE_PUBLIC_KEY")


# Ensure directories exist when imported
def ensure_directories():
    """Create data directories if they don't exist."""
    for directory in [get_raw_data_dir()]:
        os.makedirs(directory, exist_ok=True)


# Auto-create directories on import
ensure_directories()