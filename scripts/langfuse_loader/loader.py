#!/usr/bin/env python3
"""
Data loading utilities for Langfuse analytics.
"""

import os

import pandas as pd

from config import CSV_NAMING_PATTERN, get_raw_data_dir

def save_raw_data(
    df: pd.DataFrame,
    app_version: str,
) -> str:
    """Save raw DataFrame as CSV for further analysis."""
    # Use proper naming convention from config
    from datetime import datetime

    date_str = datetime.now().strftime("%Y%m%d")
    filename = CSV_NAMING_PATTERN.format(version=app_version, date=date_str)
    raw_data_dir = get_raw_data_dir()
    csv_path = raw_data_dir / filename
    os.makedirs(raw_data_dir, exist_ok=True)
    df.to_csv(csv_path, index=False)
    print(f"💾 Raw data saved to: {csv_path}")
    return str(csv_path)