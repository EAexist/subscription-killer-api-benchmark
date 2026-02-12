#!/usr/bin/env python3
"""
Benchmark Comparison Script
Reads raw Prometheus metrics JSON files from all benchmark runs and generates comparison tables.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import modularized components
from gmail_metrics import extract_gmail_critical_io, calculate_orchestration_overhead
from ai_token_metrics import extract_ai_token_metrics
from benchmark_utils import (
    extract_latency_from_metrics,
    find_benchmark_directories,
    load_metrics_data,
    format_metric_value,
    get_output_filename
)


def extract_all_metrics(metrics_data: dict) -> Dict[str, Optional[float]]:
    """
    Extract all relevant metrics from Prometheus data.
    
    Args:
        metrics_data: Dictionary containing the raw Prometheus metrics data
        
    Returns:
        Dictionary mapping metric names to their values
    """
    metrics = {}
    
    # Extract Average Latency (from /api/benchmark/analyze endpoint)
    metrics['Average Latency'] = extract_latency_from_metrics(metrics_data)
    
    # Extract Gmail API Critical I/O using modularized function
    metrics['Gmail API Critical I/O'] = extract_gmail_critical_io(metrics_data)
    
    # Calculate Orchestration Overhead using modularized function
    metrics['Orchestration Overhead'] = calculate_orchestration_overhead(
        metrics['Average Latency'], 
        metrics['Gmail API Critical I/O']
    )
    
    # Extract AI token metrics using modularized function
    ai_token_metrics = extract_ai_token_metrics(metrics_data)
    metrics.update(ai_token_metrics)
    
    return metrics


def generate_comparison_table(benchmark_dirs: List[Tuple[str, str]]) -> str:
    """
    Generate markdown comparison table for benchmark results with commits as columns.
    
    Args:
        benchmark_dirs: List of (commit_hash, directory_path) tuples
        
    Returns:
        Markdown table string
    """
    if not benchmark_dirs:
        return "No benchmark data found."
    
    # Collect all metrics data for each commit
    commits_data = {}
    all_metrics = set()
    
    for commit_hash, dir_path in benchmark_dirs:
        metrics_file = Path(dir_path) / "data" / "raw-prometheus-metrics.json"
        metrics_data = load_metrics_data(str(metrics_file))
        
        if metrics_data:
            commit_metrics = extract_all_metrics(metrics_data)
            commits_data[commit_hash] = commit_metrics
            all_metrics.update(commit_metrics.keys())
        else:
            commits_data[commit_hash] = {}
    
    # Sort commits alphabetically for consistent column order
    sorted_commits = sorted(commits_data.keys())
    
    # Generate markdown table
    table_lines = []
    table_lines.append("# Benchmark Comparison")
    table_lines.append("")
    table_lines.append("## Performance Metrics Comparison")
    table_lines.append("")
    
    # Create header row with commits as columns
    header = "| Metric | " + " | ".join(sorted_commits) + " |"
    table_lines.append(header)
    
    # Create separator row
    separator_parts = ["--------"]  # First column separator
    separator_parts.extend(["--------"] * len(sorted_commits))  # Add separators for each commit column
    separator = "| " + " | ".join(separator_parts) + " |"
    table_lines.append(separator)
    
    # Add rows for each metric
    for metric in sorted(all_metrics):
        row_values = []
        for commit in sorted_commits:
            value = commits_data[commit].get(metric)
            if value is not None:
                # Format value using utility function
                formatted_value = format_metric_value(metric, value)
                row_values.append(formatted_value)
            else:
                row_values.append("N/A")
        
        row = f"| {metric} | " + " | ".join(row_values) + " |"
        table_lines.append(row)
    
    table_lines.append("")
    
    return "\n".join(table_lines)


def main():
    """Main function to run the benchmark comparison."""
    # Base path for benchmark results
    base_path = "results/benchmark"
    
    print("Scanning benchmark directories...")
    benchmark_dirs = find_benchmark_directories(base_path)
    
    if not benchmark_dirs:
        print(f"No benchmark directories found in {base_path}")
        return
    
    print(f"Found {len(benchmark_dirs)} benchmark(s)")
    for commit_hash, dir_path in benchmark_dirs:
        print(f"  - {commit_hash}: {dir_path}")
    
    print("\nGenerating comparison table...")
    table = generate_comparison_table(benchmark_dirs)
    
    # Generate timestamped filename
    output_filename = get_output_filename(benchmark_dirs)
    
    # Save to central reports directory since this report compares all commits
    reports_dir = Path("results/reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_file = reports_dir / output_filename
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(table)
    
    print(f"Comparison table saved to {output_file}")
    print("\n" + "="*50)
    print(table)
    print("="*50)

if __name__ == "__main__":
    main()
