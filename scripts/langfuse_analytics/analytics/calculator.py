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

        df_sorted = df.sort_values("timestamp")

        # 1. Aggregate target_col by sum, grouping by trace_id
        df_agg = (
            df_sorted.groupby(["trace_id", "app_version"], sort=False)[target_col]
            .sum()
            .reset_index()
        )

        df_agg["request_index"] = df_agg.groupby("app_version").cumcount()

        amortized_cost_col = "amortized_cost"
        df_agg[amortized_cost_col] = (
            df_agg.groupby("app_version")[target_col]
            .expanding()
            .mean()
            .reset_index(level=0, drop=True)
        )

        return df_agg[["request_index", amortized_cost_col, "app_version"]].copy()
