#!/usr/bin/env python3
"""
Benchmark Utilities Module
Common utility functions for benchmark processing and file operations.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def extract_latency_from_metrics(metrics_data: dict) -> Optional[float]:
    """
    Extract average latency for /api/benchmark/analyze endpoint from Prometheus metrics.
    
    Args:
        metrics_data: Dictionary containing the raw Prometheus metrics data
        
    Returns:
        Average latency in seconds, or None if not found
    """
    import re
    
    raw_data = metrics_data.get('rawData', '')
    
    # Pattern to match http_server_requests_seconds_sum for /api/benchmark/analyze
    pattern = r'http_server_requests_seconds_sum\{[^}]*uri="/api/benchmark/analyze"[^}]*\}\s+([\d.]+)'
    
    match = re.search(pattern, raw_data)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    
    return None


def find_benchmark_directories(base_path: str) -> List[Tuple[str, str]]:
    """
    Find all benchmark directories and extract commit hashes.
    
    Args:
        base_path: Base path to results/benchmark directory
        
    Returns:
        List of tuples (commit_hash, directory_path)
    """
    benchmark_dirs = []
    base_dir = Path(base_path)
    
    if not base_dir.exists():
        print(f"Error: Base directory {base_path} does not exist")
        return benchmark_dirs
    
    # Look for subdirectories (commit hashes)
    for commit_dir in base_dir.iterdir():
        if commit_dir.is_dir():
            commit_hash = commit_dir.name
            
            # Find all timestamp subdirectories and select the most recent one
            timestamp_dirs = []
            for timestamp_dir in commit_dir.iterdir():
                if timestamp_dir.is_dir():
                    # Check if raw-prometheus-metrics.json exists
                    metrics_file = timestamp_dir / "data" / "raw-prometheus-metrics.json"
                    if metrics_file.exists():
                        timestamp_dirs.append(timestamp_dir)
            
            # Sort by timestamp (directory name) and take the most recent
            if timestamp_dirs:
                most_recent = max(timestamp_dirs, key=lambda x: x.name)
                benchmark_dirs.append((commit_hash, str(most_recent)))
    
    return benchmark_dirs


def load_metrics_data(file_path: str) -> Optional[dict]:
    """
    Load metrics data from JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary containing metrics data, or None if failed
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        print(f"Error loading {file_path}: {e}")
        return None


def format_metric_value(metric_name: str, value: float) -> str:
    """
    Format metric value with appropriate units and precision.
    
    Args:
        metric_name: Name of the metric
        value: Numeric value to format
        
    Returns:
        Formatted string representation
    """
    if metric_name in ['AI Total Tokens', 'AI Cached Tokens']:
        # Token counts should be displayed as whole numbers
        return f"{int(value)} tokens"
    elif value < 0.001:
        return f"{value * 1000:.3f} ms"
    elif value < 1:
        return f"{value:.3f} s"
    else:
        return f"{value:.2f} s"


def get_output_filename(benchmark_dirs: List[Tuple[str, str]]) -> str:
    """
    Generate output filename with first commit hash and total commits.
    Uses timestamp from the most recent benchmark directory to match the benchmark run.
    
    Args:
        benchmark_dirs: List of (commit_hash, directory_path) tuples
        
    Returns:
        Timestamped filename string
    """
    # Get first commit hash (alphabetically for consistency)
    first_commit = sorted([commit for commit, _ in benchmark_dirs])[0]
    num_commits = len(benchmark_dirs)
    
    # Extract timestamp from the most recent benchmark directory
    # Directory format: results/benchmark/{commit}/{timestamp}
    # Sort by timestamp (directory name) and take the most recent
    most_recent_dir = max(benchmark_dirs, key=lambda x: Path(x[1]).name)  # Compare by timestamp directory name
    timestamp = Path(most_recent_dir[1]).name  # Extract timestamp from directory name
    
    return f"benchmark_{first_commit}_{num_commits}commits_{timestamp}.md"
