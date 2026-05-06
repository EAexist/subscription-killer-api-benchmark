#!/usr/bin/env python3
"""
Data calculation utilities for benchmark analytics.
"""

import pandas as pd


class BenchmarkCalculator:
    """Calculator for processing and computing benchmark metrics."""

    @staticmethod
    def add_marginal_metrics(df: pd.DataFrame, input_price: float, output_price: float) -> pd.DataFrame:
        df['marginal_cost'] = df['input_tokens_per_item'] * input_price + df['output_tokens_per_item'] * output_price
        return df

    @staticmethod
    def add_convergence_metrics(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
        """Calculates CMA for any given column and returns subset for plotting."""

        df_sorted = df.sort_values("request_index")

        # 1. Aggregate target_col by sum, grouping by request_index
        df_agg = (
            df_sorted.groupby(["request_index", "app_version"], sort=False)[target_col]
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

    @staticmethod
    def normalize_request_count(df: pd.DataFrame, n_request: int) -> pd.DataFrame:
        """
        Fill missing request indices with appropriate values up to n_request for each app version and task name combination.
        Also removes any rows with request_index larger than n_request.
        
        Args:
            df: DataFrame with any columns (typically from load_and_merge_csv_files)
            n_request: Maximum number of requests to fill up to
            
        Returns:
            DataFrame with complete range of request indices from 1 to n_request for each app_version/task_name pair
        """
        # Handle empty DataFrame
        if df.empty:
            return df.copy()
        
        result_dfs = []
        
        # First, filter out any rows with request_index > n_request
        df_filtered = df[df['request_index'] <= n_request].copy()
        
        # Group by both app_version and task_name to fill missing indices for each combination
        for (app_version, task_name), group_data in df_filtered.groupby(['app_version', 'task_name'], dropna=False):
            # Create complete range from 1 to n_request
            full_range = pd.DataFrame({'request_index': range(1, n_request + 1)})
            
            # Merge with actual data to fill missing indices
            merged_data = full_range.merge(group_data, on='request_index', how='left')
            merged_data['app_version'] = app_version
            merged_data['task_name'] = task_name
            
            # Smart fillna based on column types
            for col in merged_data.columns:
                if col in ['request_index', 'app_version', 'task_name']:
                    continue  # Skip these columns
                    
                # Fill based on column dtype
                if merged_data[col].dtype in ['int64', 'float64']:
                    merged_data[col] = merged_data[col].fillna(0)
                elif merged_data[col].dtype == 'object':
                    merged_data[col] = merged_data[col].fillna('')
                elif merged_data[col].dtype == 'bool':
                    merged_data[col] = merged_data[col].fillna(False)
                else:
                    # Fallback for other types
                    merged_data[col] = merged_data[col].fillna(0)
            
            result_dfs.append(merged_data)
        
        # Combine all groups
        if result_dfs:
            return pd.concat(result_dfs, ignore_index=True)
        else:
            # Return empty DataFrame with original columns if no groups were processed
            return df[df.columns.intersection(['request_index', 'app_version', 'task_name'])].copy()
