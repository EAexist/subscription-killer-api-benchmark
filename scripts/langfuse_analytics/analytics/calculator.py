#!/usr/bin/env python3
"""
Data calculation utilities for benchmark analytics.
"""

import pandas as pd


class BenchmarkCalculator:
    """Calculator for processing and computing benchmark metrics."""

    @staticmethod
    def add_convergence_metrics(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
        """Calculates CMA for any given column and returns subset for plotting."""
        df_calc = df.copy()

        # 1. Aggregate target_col by sum, grouping by trace_id
        df_agg = df_calc.groupby(["trace_id", "version"], as_index=False)[
            target_col
        ].sum()

        # 2. Sort by timestamp within each version and create request_index
        # First, sort all data by timestamp to get the correct order
        df_sorted = df_calc.sort_values("timestamp")
        # Then assign request_index based on the order within each version
        df_sorted["request_index"] = df_sorted.groupby("version").cumcount()

        # Get the unique mapping of trace_id, version to request_index
        trace_mapping = df_sorted[
            ["trace_id", "version", "request_index"]
        ].drop_duplicates()

        # Merge the request_index back to aggregated data
        df_agg = df_agg.merge(trace_mapping, on=["trace_id", "version"], how="left")

        # 3. Calculate Derived Value (CMA)
        cma_col = "cma_cost"
        df_agg[cma_col] = (
            df_agg.groupby("version")[target_col]
            .expanding()
            .mean()
            .reset_index(level=0, drop=True)
        )

        # 4. Return subset DataFrame for plotting
        # Keep only the columns required by plot_cost_convergence
        subset_df = pd.DataFrame(df_agg[["request_index", cma_col, "version"]].copy())

        return subset_df
