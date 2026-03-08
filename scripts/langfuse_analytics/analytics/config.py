#!/usr/bin/env python3
"""
Centralized configuration for Langfuse analytics.
"""

import os
from pathlib import Path

# Base directory detection
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_STORAGE_ROOT = Path(
    os.getenv("DATA_STORAGE_ROOT", str(PROJECT_ROOT / "data-storage"))
)

# Data paths
RAW_DATA_DIR = DATA_STORAGE_ROOT / "results" / "raw"
PLOTS_DIR = DATA_STORAGE_ROOT / "results" / "plots"
REPORTS_DIR = DATA_STORAGE_ROOT / "reports"
LANGFUSE_DIR = DATA_STORAGE_ROOT / "langfuse"

# File naming patterns
CSV_NAMING_PATTERN = "benchmark_{version}_{date}.csv"
PLOT_NAMING_PATTERN = "{metric}_results.png"

# Processing constants
DEFAULT_RETRY_COUNT = 5
DEFAULT_INITIAL_DELAY = 30
MAX_REQUEST_INDEX_TICKS = 5

# API endpoints and secrets
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")


# Ensure directories exist when imported
def ensure_directories():
    """Create data directories if they don't exist."""
    for directory in [RAW_DATA_DIR, PLOTS_DIR, REPORTS_DIR, LANGFUSE_DIR]:
        os.makedirs(directory, exist_ok=True)


# Auto-create directories on import
ensure_directories()
