#!/usr/bin/env python3
"""
Trace Data Processing Module
Handles extraction and processing of benchmark trace data.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from trace_parser import TraceParser
from trace_statistics import TraceStatistics


# Constants
BENCHMARK_ENDPOINT = "benchmark/analyze"


def is_benchmark_span(span: Dict[str, Any]) -> bool:
    """Check if span is a benchmark HTTP request."""
    return (
        'name' in span and
        'duration' in span and
        'http' in span['name'].lower() and
        BENCHMARK_ENDPOINT in span['name'].lower()
    )


def find_benchmark_directories(base_path: str) -> List[Tuple[str, str]]:
    """Find all benchmark directories and extract commit hashes."""
    benchmark_dirs = []
    base_dir = Path(base_path)

    if not base_dir.exists():
        print(f"Error: Base directory {base_path} does not exist")
        return benchmark_dirs

    for commit_dir in base_dir.iterdir():
        if not commit_dir.is_dir():
            continue

        commit_hash = commit_dir.name
        timestamp_dirs = [
            timestamp_dir for timestamp_dir in commit_dir.iterdir()
            if timestamp_dir.is_dir() and (timestamp_dir / "data" / "raw-zipkin-traces.json").exists()
        ]

        if timestamp_dirs:
            most_recent = max(timestamp_dirs, key=lambda x: x.name)
            benchmark_dirs.append((commit_hash, str(most_recent)))
        else:
            print(f"Info: Skipping commit {commit_hash} - no trace data found")

    return benchmark_dirs


def count_benchmark_traces(traces: List[List[Dict[str, Any]]]) -> int:
    """Count traces containing benchmark HTTP requests."""
    return sum(
        any(is_benchmark_span(span) for span in trace)
        for trace in traces
    )


def calculate_average(values: List[float], filter_zeros: bool = True) -> Optional[float]:
    """Calculate average from values, optionally filtering zeros."""
    if not values:
        return None

    filtered_values = [v for v in values if not filter_zeros or v > 0]
    return sum(filtered_values) / len(filtered_values) if filtered_values else None


def extract_benchmark_spans(traces: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Extract benchmark HTTP spans from traces."""
    benchmark_spans = []
    for trace in traces:
        for span in trace:
            if is_benchmark_span(span):
                benchmark_spans.append({
                    'duration_ms': span['duration'] / 1000
                })
    return benchmark_spans


def build_metrics_dict(benchmark_spans: List[Dict[str, Any]],
                     critical_io_data: Dict[str, List[Dict[str, Any]]],
                     token_data: List[Dict[str, Any]],
                     total_benchmark_traces: int,
                     real_iterations: int) -> Dict[str, Optional[float]]:
    """Build metrics dictionary from processed data."""
    if not benchmark_spans:
        return {}

    durations = [span['duration_ms'] for span in benchmark_spans]
    stats = TraceStatistics.calculate_basic_stats(durations)

    metrics = {
        'Indicative Latency': {
            'average': stats['mean'],
            'max': stats['max'],
            'std_dev': stats['std_dev']
        },
        'Min Latency': stats['min'],
        'Latency Std Dev': stats['std_dev'],
        'Latency CV': TraceStatistics.calculate_coefficient_of_variation(durations),
        'Total Benchmark Traces': total_benchmark_traces,
        'Test Iterations': real_iterations
    }

    # Critical I/O metrics
    metrics['Gmail API Critical I/O'] = calculate_average(
        [io['critical_io_ms'] for io in critical_io_data.get('gmail', [])]
    )
    metrics['AI Critical I/O'] = calculate_average(
        [io['critical_io_ms'] for io in critical_io_data.get('ai', [])]
    )
    metrics['Total Critical I/O'] = calculate_average(
        [io['critical_io_ms'] for io in critical_io_data.get('total', [])]
    )

    # AI token usage
    metrics['Input Token Count'] = calculate_average(
        [data['input_tokens'] for data in token_data]
    )
    
    metrics['Output Token Count'] = calculate_average(
        [data['output_tokens'] for data in token_data]
    )
    
    metrics['Total Tokens'] = calculate_average(
        [data['total_tokens'] for data in token_data]
    )
    
    # AI price calculation
    import os
    input_token_price = float(os.getenv('GEMINI_3_FLASH_PREVIEW_INPUT_TOKEN_PRICE_PER_MILLION', '0'))
    output_token_price = float(os.getenv('GEMINI_3_FLASH_PREVIEW_OUTPUT_TOKEN_PRICE_PER_MILLION', '0'))
    
    if input_token_price > 0 or output_token_price > 0:
        avg_input_tokens = calculate_average(
            [data['input_tokens'] for data in token_data]
        )
        avg_output_tokens = calculate_average(
            [data['output_tokens'] for data in token_data]
        )
        
        if avg_input_tokens is not None and avg_output_tokens is not None:
            input_price = (avg_input_tokens / 1_000_000) * input_token_price
            output_price = (avg_output_tokens / 1_000_000) * output_token_price
            metrics['AI Cost'] = input_price + output_price
        else:
            metrics['AI Cost'] = None
    else:
        metrics['AI Cost'] = None

    # Orchestration Overhead
    if metrics['Indicative Latency']['average'] is not None and metrics['Total Critical I/O'] is not None:
        orchestration_overhead = metrics['Indicative Latency']['average'] - metrics['Total Critical I/O']
        metrics['Orchestration Overhead'] = max(orchestration_overhead, 0)
    else:
        metrics['Orchestration Overhead'] = None

    return metrics


def read_execution_summary(dir_path: str) -> Dict[str, Any]:
    """Read execution summary data including iteration counts."""
    summary_file = Path(dir_path) / "data" / "execution-summary.json"
    
    if not summary_file.exists():
        print(f"Warning: No execution summary found at {summary_file}")
        return {}
    
    try:
        with open(summary_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error reading execution summary: {e}")
        return {}


def read_benchmark_metadata(dir_path: str) -> Dict[str, Any]:
    """Read benchmark metadata including git tag."""
    metadata_file = Path(dir_path) / "data" / "benchmark-metadata.json"
    
    if not metadata_file.exists():
        print(f"Warning: No benchmark metadata found at {metadata_file}")
        return {}
    
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error reading benchmark metadata: {e}")
        return {}


def extract_commit_metrics(commit_hash: str, dir_path: str) -> Dict[str, Optional[float]]:
    """Extract performance metrics from a single commit's trace data."""
    traces_file = Path(dir_path) / "data" / "raw-zipkin-traces.json"

    if not traces_file.exists():
        print(f"Warning: No trace data found for {commit_hash} at {traces_file}")
        return {}

    try:
        # Read execution summary to get warmup iterations
        execution_summary = read_execution_summary(dir_path)
        warmup_iterations = execution_summary.get('warmupIterations', 0) if execution_summary else 0
        
        parser = TraceParser(str(traces_file), warmup_iterations)

        # Get trace counts (after warmup exclusion)
        total_benchmark_traces = count_benchmark_traces(parser.traces)

        # Extract benchmark spans
        benchmark_spans = extract_benchmark_spans(parser.traces)
        if not benchmark_spans:
            print(f"Warning: No benchmark HTTP spans found for {commit_hash}")
            return {}

        # Get critical I/O and token data
        critical_io_data = {
            'gmail': parser.get_gmail_api_critical_io(),
            'ai': parser.get_ai_api_critical_io(),
            'total': parser.get_total_critical_io()
        }
        token_data = parser.get_ai_token_usage()
        
        # Get real iterations from execution summary
        real_iterations = execution_summary.get('realIterations', 1) if execution_summary else 1

        return build_metrics_dict(benchmark_spans, critical_io_data, token_data, total_benchmark_traces, real_iterations)

    except Exception as e:
        print(f"Error processing {commit_hash}: {e}")
        return {}


def load_all_commit_data(new_commit_hash: str, new_dir_path: str) -> Tuple[Dict[str, Dict[str, Any]], List[Tuple[str, str]]]:
    """Load all commit data including new commit."""
    import os
    base_path = os.path.join(os.path.dirname(__file__), "..", "results", "ai-benchmark")
    all_benchmark_dirs = find_benchmark_directories(base_path)
    
    commits_data = {}
    
    # Load data for existing commits
    for commit_hash, dir_path in all_benchmark_dirs:
        try:
            metrics = extract_commit_metrics(commit_hash, dir_path)
            if metrics:
                metadata = read_benchmark_metadata(dir_path)
                metrics['_tag'] = metadata.get('tag', commit_hash[:8])
                commits_data[commit_hash] = metrics
                print(f"Info: Loaded metrics for {commit_hash}: {len(metrics)-1} metrics")
        except Exception as e:
            print(f"Error processing existing commit {commit_hash}: {e}")
    
    # Process new commit
    new_metrics = extract_commit_metrics(new_commit_hash, new_dir_path)
    if not new_metrics:
        print(f"Error: No valid benchmark data for {new_commit_hash}")
        return {}, []
    
    metadata = read_benchmark_metadata(new_dir_path)
    new_metrics['_tag'] = metadata.get('tag', new_commit_hash[:8])
    commits_data[new_commit_hash] = new_metrics
    print(f"Info: Loaded metrics for new commit {new_commit_hash}: {len(new_metrics)-1} metrics")
    
    if not commits_data:
        print("Error: No valid benchmark data found")
        return {}, []
    
    # Sort commits by tag and prepare directories
    sorted_commits = sorted(commits_data.keys(), key=lambda x: commits_data[x]['_tag'])
    final_dirs = []
    
    for commit in sorted_commits:
        matching_dir = None
        for bh_commit, bh_dir in all_benchmark_dirs:
            if bh_commit == commit:
                matching_dir = bh_dir
                break
        if commit == new_commit_hash:
            matching_dir = new_dir_path
        if matching_dir:
            final_dirs.append((commit, matching_dir))
    
    return commits_data, final_dirs
