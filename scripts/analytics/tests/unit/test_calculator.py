#!/usr/bin/env python3
"""
Unit tests for analytics.calculator module.
"""

import unittest
import pandas as pd
import numpy as np
from analytics.calculator import BenchmarkCalculator


class TestBenchmarkCalculator(unittest.TestCase):
    """Unit tests for BenchmarkCalculator class."""

    def setUp(self):
        """Set up test data."""
        self.sample_data = {
            "id": [1, 2, 3, 4, 5, 6],
            "request_index": [1, 2, 3, 1, 2, 3],
            "app_version": ["v1", "v1", "v1", "v2", "v2", "v2"],
            "task_name": ["task1", "task1", "task1", "task1", "task1", "task1"],
            "input_tokens_per_item": [2, 3, 4, 5, 6, 7],
            "output_tokens_per_item": [1, 2, 3, 4, 5, 6],
            "total_cost": [0.0018, 0.0027, 0.0036, 0.0045, 0.0054, 0.0063],
        }
        self.df = pd.DataFrame(self.sample_data)

    def test_add_marginal_metrics_basic(self):
        """Test add_marginal_metrics with basic input."""
        input_price = 0.0001
        output_price = 0.0002
        
        result = BenchmarkCalculator.add_marginal_metrics(self.df, input_price, output_price)
        
        # Check that marginal_cost column was added
        self.assertIn('marginal_cost', result.columns)
        
        # Check calculation for first row: 2*0.0001 + 1*0.0002 = 0.0004
        expected_first = 2 * input_price + 1 * output_price
        self.assertEqual(result.iloc[0]['marginal_cost'], expected_first)
        
        # Check calculation for last row: 7*0.0001 + 6*0.0002 = 0.0019
        expected_last = 7 * input_price + 6 * output_price
        self.assertEqual(result.iloc[-1]['marginal_cost'], expected_last)

    def test_add_marginal_metrics_zero_prices(self):
        """Test add_marginal_metrics with zero prices."""
        result = BenchmarkCalculator.add_marginal_metrics(self.df, 0, 0)
        
        # All marginal costs should be zero
        self.assertTrue(all(result['marginal_cost'] == 0))

    def test_add_marginal_metrics_negative_prices(self):
        """Test add_marginal_metrics with negative prices."""
        input_price = -0.0001
        output_price = -0.0002
        
        result = BenchmarkCalculator.add_marginal_metrics(self.df, input_price, output_price)
        
        # Should handle negative prices correctly
        expected_first = 2 * input_price + 1 * output_price
        self.assertEqual(result.iloc[0]['marginal_cost'], expected_first)

    def test_add_convergence_metrics_basic(self):
        """Test add_convergence_metrics with basic cost data."""
        result = BenchmarkCalculator.add_convergence_metrics(self.df, "total_cost")
        
        # Check expected columns
        expected_columns = ["request_index", "amortized_cost", "app_version"]
        for col in expected_columns:
            self.assertIn(col, result.columns)
        
        # Check that we have data for both versions
        versions = result["app_version"].unique()
        self.assertIn("v1", versions)
        self.assertIn("v2", versions)
        
        # Check CMA calculation for v1: [0.0018, (0.0018+0.0027)/2, (0.0018+0.0027+0.0036)/3]
        v1_data = result[result["app_version"] == "v1"].sort_values("request_index")
        expected_cma_v1 = [0.0018, (0.0018 + 0.0027) / 2, (0.0018 + 0.0027 + 0.0036) / 3]
        actual_cma_v1 = v1_data["amortized_cost"].tolist()
        
        for expected, actual in zip(expected_cma_v1, actual_cma_v1):
            self.assertAlmostEqual(expected, actual, places=6)

    def test_add_convergence_metrics_single_version(self):
        """Test add_convergence_metrics with single version data."""
        single_version_df = self.df[self.df["app_version"] == "v1"].copy()
        
        result = BenchmarkCalculator.add_convergence_metrics(single_version_df, "total_cost")
        
        # Should have only one version
        self.assertEqual(len(result["app_version"].unique()), 1)
        self.assertEqual(result["app_version"].iloc[0], "v1")

    def test_add_convergence_metrics_empty_dataframe(self):
        """Test add_convergence_metrics with empty DataFrame."""
        empty_df = pd.DataFrame(columns=self.df.columns)
        
        result = BenchmarkCalculator.add_convergence_metrics(empty_df, "total_cost")
        
        # Should return empty DataFrame with expected columns
        expected_columns = ["request_index", "amortized_cost", "app_version"]
        self.assertEqual(len(result), 0)
        for col in expected_columns:
            self.assertIn(col, result.columns)

    def test_add_convergence_metrics_missing_column(self):
        """Test add_convergence_metrics with non-existent target column."""
        # This should raise a KeyError when trying to access the missing column
        with self.assertRaises(KeyError):
            BenchmarkCalculator.add_convergence_metrics(self.df, "non_existent_column")

    def test_normalize_request_count_basic(self):
        """Test normalize_request_count with basic functionality."""
        n_request = 5
        
        result = BenchmarkCalculator.normalize_request_count(self.df, n_request)
        
        # Should have more rows than original due to filling missing indices
        self.assertGreater(len(result), len(self.df))
        
        # Check that each version-task combination has complete range 1-5
        for (app_version, task_name), group in result.groupby(['app_version', 'task_name']):
            request_indices = group['request_index'].sort_values().tolist()
            expected_indices = list(range(1, n_request + 1))
            self.assertEqual(request_indices, expected_indices)

    def test_normalize_request_count_filter_higher_indices(self):
        """Test normalize_request_count filters out indices > n_request."""
        # Add data with request_index > 3
        df_with_high_index = self.df.copy()
        df_with_high_index.loc[len(df_with_high_index)] = {
            "id": 7,
            "request_index": 10,  # This should be filtered out
            "app_version": "v1",
            "task_name": "task1",
            "input_tokens_per_item": 8,
            "output_tokens_per_item": 7,
            "total_cost": 0.0072,
        }
        
        n_request = 5
        result = BenchmarkCalculator.normalize_request_count(df_with_high_index, n_request)
        
        # Should not have any request_index > 5
        self.assertTrue(all(result['request_index'] <= n_request))

    def test_normalize_request_count_fill_missing_data(self):
        """Test normalize_request_count fills missing data appropriately."""
        n_request = 3
        
        result = BenchmarkCalculator.normalize_request_count(self.df, n_request)
        
        # Check that numeric columns are filled with 0 for missing data
        for col in ['input_tokens_per_item', 'output_tokens_per_item', 'total_cost']:
            self.assertFalse(result[col].isna().any())
        
        # Check that object columns would be filled with '' if they existed
        # (our test data doesn't have object columns besides app_version and task_name)

    def test_normalize_request_count_empty_dataframe(self):
        """Test normalize_request_count with empty DataFrame."""
        empty_df = pd.DataFrame(columns=self.df.columns)
        
        result = BenchmarkCalculator.normalize_request_count(empty_df, 3)
        
        # Should return empty DataFrame
        self.assertEqual(len(result), 0)

    def test_normalize_request_count_single_request(self):
        """Test normalize_request_count with n_request=1."""
        n_request = 1
        
        result = BenchmarkCalculator.normalize_request_count(self.df, n_request)
        
        # Should have exactly one row per version-task combination
        for (app_version, task_name), group in result.groupby(['app_version', 'task_name']):
            self.assertEqual(len(group), 1)
            self.assertEqual(group['request_index'].iloc[0], 1)

    def test_normalize_request_count_mixed_data_types(self):
        """Test normalize_request_count with mixed data types."""
        # Create DataFrame with mixed data types
        mixed_df = self.df.copy()
        mixed_df['boolean_col'] = [True, False, True, False, True, False]
        mixed_df['string_col'] = ['a', 'b', 'c', 'd', 'e', 'f']
        
        n_request = 2
        result = BenchmarkCalculator.normalize_request_count(mixed_df, n_request)
        
        # Check boolean column is filled with False
        self.assertFalse(result['boolean_col'].isna().any())
        self.assertTrue(all(val in [True, False] for val in result['boolean_col']))
        
        # Check string column is filled with empty string
        self.assertFalse(result['string_col'].isna().any())
        # Note: empty strings might be present for filled values

    def test_integration_convergence_after_normalization(self):
        """Test integration: convergence metrics after normalization."""
        n_request = 3
        
        # First normalize request count
        normalized_df = BenchmarkCalculator.normalize_request_count(self.df, n_request)
        
        # Then calculate convergence metrics
        result = BenchmarkCalculator.add_convergence_metrics(normalized_df, "total_cost")
        
        # Should have expected structure
        expected_columns = ["request_index", "amortized_cost", "app_version"]
        for col in expected_columns:
            self.assertIn(col, result.columns)
        
        # Should have data for both versions
        versions = result["app_version"].unique()
        self.assertIn("v1", versions)
        self.assertIn("v2", versions)


if __name__ == "__main__":
    unittest.main()
