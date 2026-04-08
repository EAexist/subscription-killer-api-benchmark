#!/usr/bin/env python3
"""
Data loading utilities for Langfuse analytics.
"""

import os

import pandas as pd

from .config import get_raw_data_dir
from .constants import EXPECTED_COLUMNS, REQUIRED_COLUMNS, OPTIONAL_COLUMNS

def load_and_merge_csv_files() -> pd.DataFrame:
    """Load all CSV files from data directory and merge them."""

    raw_data_dir = get_raw_data_dir()
    csv_files = [f for f in os.listdir(raw_data_dir) if f.endswith(".csv")]

    if not csv_files:
        print(f"❌ No CSV files found in directory: {raw_data_dir}")
        return pd.DataFrame()

    print(f"📁 Found {len(csv_files)} CSV files: {csv_files}")

    dataframes = []
    for csv_file in csv_files:
        try:
            csv_path = raw_data_dir / csv_file
            df = pd.read_csv(csv_path)

            # Validate CSV structure against expected schema
            df_columns = set(df.columns)

            # Check for required columns
            missing_required = REQUIRED_COLUMNS - df_columns
            if missing_required:
                print(
                    f"  Skipping {csv_file}: Missing required columns: {sorted(missing_required)}"
                )
                continue

            # Check for reasonable data (at least one non-null value in required columns)
            required_cols_data = df[list(REQUIRED_COLUMNS)]
            # Use numpy's any() which works consistently
            has_valid_data = required_cols_data.notna().to_numpy().any()
            if not has_valid_data:
                print(f"  Skipping {csv_file}: No valid data found in required columns")
                continue

            # Warn about missing optional columns but still load the file
            missing_optional = OPTIONAL_COLUMNS - df_columns
            if missing_optional:
                print(
                    f"  ⚠️  {csv_file}: Missing optional columns: {sorted(missing_optional)}"
                )

            # Warn about unexpected columns but still load the file
            unexpected_columns = df_columns - EXPECTED_COLUMNS
            if unexpected_columns:
                print(
                    f"⚠️  {csv_file}: Contains unexpected columns: {sorted(unexpected_columns)}"
                )

            dataframes.append(df)
            print(f"✅ Loaded {csv_file}: {df.shape}")

        except pd.errors.EmptyDataError:
            print(f"⚠️  Skipping {csv_file}: Empty file")
            continue
        except pd.errors.ParserError as e:
            print(f"⚠️  Skipping {csv_file}: CSV parsing error - {e}")
            continue
        except Exception as e:
            print(f"❌ Error loading {csv_file}: {e}")
            continue

    if not dataframes:
        print("❌ No valid CSV files could be loaded")
        return pd.DataFrame()

    # Merge all dataframes
    merged_df = pd.concat(dataframes, ignore_index=True)
    print(f"📋 Merged {len(dataframes)} DataFrames into one: {merged_df.shape}")

    return merged_df
