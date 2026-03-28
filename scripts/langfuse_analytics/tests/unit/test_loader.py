#!/usr/bin/env python3
"""
Unit tests for analytics.loader module.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from analytics.loader import load_and_merge_csv_files, save_raw_data


class TestLoader(unittest.TestCase):
    """Unit tests for data loading utilities."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @staticmethod
    def get_valid_csv_data():
        """Get a valid CSV data structure that matches EXPECTED_COLUMNS."""
        return {
            "id": [1, 2],
            "request_index": [1, 2],
            "app_version": ["v1", "v1"],
            "task_name": ["task1", "task2"],
            "input_tokens": [10, 15],
            "instruction_tokens": [5, 7],
            "output_tokens": [8, 12],
            "input_tokens_per_item": [2, 3],
            "output_tokens_per_item": [1, 2],
            "total_tokens": [23, 34],
            "cost_input": [0.001, 0.0015],
            "cost_output": [0.0008, 0.0012],
            "cost_total": [0.0018, 0.0027],
        }

    @staticmethod
    def get_valid_csv_data_variant():
        """Get a variant of valid CSV data for testing multiple files."""
        return {
            "id": [3, 4],
            "request_index": [1, 2],
            "app_version": ["v2", "v2"],
            "task_name": ["task3", "task4"],
            "input_tokens": [20, 25],
            "instruction_tokens": [10, 12],
            "output_tokens": [16, 20],
            "input_tokens_per_item": [4, 5],
            "output_tokens_per_item": [3, 4],
            "total_tokens": [46, 57],
            "cost_input": [0.002, 0.0025],
            "cost_output": [0.0016, 0.002],
            "cost_total": [0.0036, 0.0045],
        }

    def test_save_raw_data(self):
        """Test save_raw_data function with test data."""
        # Create test DataFrame with required columns using shared data
        data = self.get_valid_csv_data()
        df = pd.DataFrame(data)

        # Test save_raw_data function (uses configured RAW_DATA_DIR)
        csv_path = save_raw_data(df, "test_version")

        # Verify file was created
        self.assertTrue(os.path.exists(csv_path))
        self.assertTrue(csv_path.endswith(".csv"))
        self.assertIn("test_version", csv_path)

        # Verify content
        saved_df = pd.read_csv(csv_path)
        self.assertEqual(len(saved_df), len(df))
        self.assertGreater(len(saved_df.columns), 0)

        # Verify data integrity
        self.assertEqual(list(saved_df.columns), list(df.columns))
        self.assertEqual(saved_df["id"].tolist(), [1, 2])
        self.assertEqual(saved_df["app_version"].tolist(), ["v1", "v1"])
        self.assertEqual(saved_df["cost_total"].tolist(), [0.0018, 0.0027])

        # Clean up created file
        os.remove(csv_path)

    def test_save_raw_data_default_params(self):
        """Test save_raw_data with version parameter."""
        data = self.get_valid_csv_data()
        df = pd.DataFrame(data)

        csv_path = save_raw_data(df, "default_version")

        # Verify filename contains version and date
        self.assertTrue(os.path.exists(csv_path))
        self.assertIn("default_version", csv_path)
        self.assertTrue(csv_path.endswith(".csv"))

        # Clean up created file
        os.remove(csv_path)

    def test_load_and_merge_csv_files_empty_directory(self):
        """Test load_and_merge_csv_files with empty directory."""
        # Patch get_raw_data_dir to use temp directory as Path object
        with patch("analytics.loader.get_raw_data_dir", return_value=Path(self.temp_dir)):
            result = load_and_merge_csv_files()
            self.assertTrue(result.empty)

    def test_load_and_merge_csv_files_nonexistent_directory(self):
        """Test load_and_merge_csv_files with nonexistent directory."""
        # Temporarily patch get_raw_data_dir to a nonexistent path
        with patch("analytics.loader.get_raw_data_dir", return_value=Path("/nonexistent/path")):
            with self.assertRaises(FileNotFoundError):
                load_and_merge_csv_files()

    def test_load_and_merge_csv_files_with_data(self):
        """Test load_and_merge_csv_files with actual CSV files."""
        # Create test CSV files using shared data structures
        data1 = self.get_valid_csv_data()
        data2 = self.get_valid_csv_data_variant()

        df1 = pd.DataFrame(data1)
        df2 = pd.DataFrame(data2)

        csv1_path = os.path.join(self.temp_dir, "test1.csv")
        csv2_path = os.path.join(self.temp_dir, "test2.csv")

        df1.to_csv(csv1_path, index=False)
        df2.to_csv(csv2_path, index=False)

        # Test merging with patched get_raw_data_dir as Path object
        with patch("analytics.loader.get_raw_data_dir", return_value=Path(self.temp_dir)):
            result = load_and_merge_csv_files()

            # Verify results
            self.assertEqual(len(result), 4)  # 2 rows from each file
            self.assertIn("id", result.columns)
            self.assertIn("request_index", result.columns)
            self.assertIn("app_version", result.columns)
            self.assertIn("cost_total", result.columns)

            # Verify data integrity
            self.assertEqual(result["id"].tolist(), [1, 2, 3, 4])
            self.assertEqual(result["request_index"].tolist(), [1, 2, 1, 2])
            self.assertEqual(result["app_version"].tolist(), ["v1", "v1", "v2", "v2"])

    def test_load_and_merge_csv_files_with_mixed_files(self):
        """Test load_and_merge_csv_files with CSV and non-CSV files."""
        # Create CSV file using shared data structure
        csv_data = self.get_valid_csv_data()
        df_csv = pd.DataFrame(csv_data)
        csv_path = os.path.join(self.temp_dir, "data.csv")
        df_csv.to_csv(csv_path, index=False)

        # Create non-CSV file
        txt_path = os.path.join(self.temp_dir, "readme.txt")
        with open(txt_path, "w") as f:
            f.write("This is not a CSV file")

        # Test loading with patched get_raw_data_dir as Path object (should only load CSV files)
        with patch("analytics.loader.get_raw_data_dir", return_value=Path(self.temp_dir)):
            result = load_and_merge_csv_files()

            # Verify only CSV data was loaded
            self.assertEqual(len(result), 2)
            self.assertEqual(result["id"].tolist(), [1, 2])


if __name__ == "__main__":
    unittest.main()
