#!/usr/bin/env python3
"""
Centralized configuration for Langfuse analytics.
"""

import os
from pathlib import Path

# Base directory detection
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DATA_STORAGE_ROOT = Path(
    os.getenv("DATA_STORAGE_ROOT", str(PROJECT_ROOT / "data-storage"))
)

# Data paths
RAW_DATA_DIR = DATA_STORAGE_ROOT / "results" / "raw"
PLOTS_DIR = DATA_STORAGE_ROOT / "results" / "plots"

# File naming patterns
CSV_NAMING_PATTERN = "benchmark_{version}_{date}.csv"
PLOT_NAMING_PATTERN = "{metric}_results.png"

# Processing constants
DEFAULT_RETRY_COUNT = 5
DEFAULT_INITIAL_DELAY = 30
MAX_REQUEST_INDEX_TICKS = 5

# API endpoints and secrets
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")


# Ensure directories exist when imported
def ensure_directories():
    """Create data directories if they don't exist."""
    for directory in [RAW_DATA_DIR, PLOTS_DIR]:
        os.makedirs(directory, exist_ok=True)


# Auto-create directories on import
ensure_directories()


import matplotlib.pyplot as plt

def apply_custom_style():
    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams.update({
        # --- Figure ---
        "figure.autolayout": True,
        "figure.figsize": (12, 8),
        "figure.dpi": 300,
        # --- Fonts ---
        "axes.titlesize": 20,
        "axes.labelsize": 16,
        "xtick.labelsize": 14,
        "ytick.labelsize": 14,
        "legend.fontsize": 14,
        # --- Grid ---
        "axes.grid": True,
        "grid.alpha": 0.3,
        # --- Padding ---
        "axes.titlepad": 25.0,          # Space above plot
        "axes.labelpad": 15.0,          # Space between label and numbers
        "xtick.major.pad": 8.0,         # Space between numbers and axis
        "ytick.major.pad": 8.0,
        # --- Lines ---
        "lines.linewidth": 2.5,
        "lines.marker": "o",
        "lines.markersize": 3,
    })
