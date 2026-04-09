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
from analytics.loader import load_and_merge_csv_files

class TestLoader(unittest.TestCase):
    """Unit tests for data loading utilities."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_and_merge_csv_files_empty_directory(self):
        """Test load_and_merge_csv_files with empty directory."""
        # Patch get_raw_data_dir to use temp directory as Path object
        with patch("analytics.loader.get_raw_data_dir", return_value=Path(self.temp_dir)):
            result = load_and_merge_csv_files()
            self.assertTrue(result.empty)

    def test_load_and_merge_csv_files_nonexistent_directory(self):
        """Test load_and_merge_csv_files with nonexistent directory."""
        # Test loading with patched get_raw_data_dir pointing to nonexistent directory
        nonexistent_path = Path("/nonexistent/directory/that/does/not/exist")
        with patch("analytics.loader.get_raw_data_dir", return_value=nonexistent_path):
            result = load_and_merge_csv_files()
            
            # Should return empty DataFrame for nonexistent directory
            self.assertTrue(result.empty)
