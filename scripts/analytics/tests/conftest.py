"""
Pytest configuration and fixtures for analytics tests.
"""
import pytest
import pandas as pd
from pathlib import Path


@pytest.fixture
def valid_csv_data():
    """Get valid CSV data structure that matches EXPECTED_COLUMNS."""
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


@pytest.fixture
def valid_csv_data_variant():
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


@pytest.fixture
def longer_csv_data():
    """Get longer CSV data structure for testing calculator methods with more rows."""
    return {
        "id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "request_index": [1, 2, 3, 1, 2, 3, 1, 2, 3, 4],
        "app_version": ["v1", "v1", "v1", "v2", "v2", "v2", "v3", "v3", "v3", "v3"],
        "task_name": ["task1", "task1", "task1", "task1", "task1", "task1", "task2", "task2", "task2", "task2"],
        "input_tokens": [10, 15, 20, 25, 30, 35, 40, 45, 50, 55],
        "instruction_tokens": [5, 7, 10, 12, 15, 17, 20, 22, 25, 27],
        "output_tokens": [8, 12, 16, 20, 24, 28, 32, 36, 40, 44],
        "input_tokens_per_item": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
        "output_tokens_per_item": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "total_tokens": [23, 34, 46, 57, 69, 80, 92, 103, 115, 126],
        "cost_input": [0.001, 0.0015, 0.002, 0.0025, 0.003, 0.0035, 0.004, 0.0045, 0.005, 0.0055],
        "cost_output": [0.0008, 0.0012, 0.0016, 0.002, 0.0024, 0.0028, 0.0032, 0.0036, 0.004, 0.0044],
        "cost_total": [0.0018, 0.0027, 0.0036, 0.0045, 0.0054, 0.0063, 0.0072, 0.0081, 0.009, 0.0099],
    }


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    import tempfile
    import shutil
    
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)
