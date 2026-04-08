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

def get_plots_dir():
    """Get plots directory lazily."""
    return get_data_storage_root() / "results" / "plots"

# File naming patterns
CSV_NAMING_PATTERN = "benchmark_{version}_{date}.csv"
PLOT_NAMING_PATTERN = "{metric}_results.png"

# Ensure directories exist when imported
def ensure_directories():
    """Create data directories if they don't exist."""
    for directory in [get_raw_data_dir(), get_plots_dir()]:
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
        "legend.fontsize": 16,
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
