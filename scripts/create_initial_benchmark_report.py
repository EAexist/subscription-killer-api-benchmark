#!/usr/bin/env python3
"""
DEPRECATED: Initial Benchmark Report Creation Script
This script contains the deprecated functionality for creating initial benchmark reports.
Use trace_ai_benchmark_comparison.py --mode create for new implementations.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Fix console encoding for emoji support
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
elif sys.platform.startswith('darwin'):
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from trace_parser import TraceParser
from trace_statistics import TraceStatistics


# Constants
BENCHMARK_ENDPOINT = "benchmark/analyze"
AI_METRICS = [
    'AI Cost', 'Input Token Count', 'Output Token Count', 'Total Tokens'
]

SUPPLEMENTARY_METRICS = [
    'Indicative Latency', 'Gmail API Critical I/O',
    'AI Critical I/O', 'Total Critical I/O', 'Orchestration Overhead'
]


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


def format_metric_value(metric_name: str, value: Optional[float],
                      std_dev: Optional[float] = None) -> str:
    """Format metric value with appropriate units and precision."""
    if value is None:
        return "N/A"

    # Handle percentage-based metrics
    if 'CV' in metric_name:
        return f"{value:.1f}%"

    # Handle token counts
    if 'Token Count' in metric_name or 'Total Tokens' in metric_name:
        return f"{int(value)} tokens"
    
    # Handle AI price
    if 'AI Cost' in metric_name:
        if value == 0:
            return "$0.000 / 1K requests"
        price_per_1k = value * 1000
        return f"${price_per_1k:.3f} / 1K requests"

    # Convert to seconds for display
    value_seconds = value / 1000

    # Handle standard deviation for average values
    if std_dev is not None and ('Average' in metric_name or 'Indicative Average' in metric_name):
        std_dev_seconds = std_dev / 1000
        return f"{value_seconds:.2f} ± {std_dev_seconds:.2f} s"

    return f"{value_seconds:.2f} s"


def format_indicative_latency(latency_data: Dict[str, Any], test_iterations: int = 1) -> str:
    """Format Indicative Latency with average and max."""
    if not latency_data or latency_data.get('average') is None:
        return "N/A"
    
    avg_seconds = latency_data['average'] / 1000
    
    # For single iteration, only show average
    if test_iterations == 1:
        return f"{avg_seconds:.2f} s"
    
    # For multiple iterations, show average ± std_dev (max: max)
    max_seconds = latency_data['max'] / 1000
    std_dev_seconds = latency_data['std_dev'] / 1000
    
    return f"{avg_seconds:.2f} ± {std_dev_seconds:.2f} s (max: {max_seconds:.2f} s)"


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


def create_initial_benchmark_report(commit_hash: str, dir_path: str) -> str:
    """Create initial benchmark report with single column."""
    metrics = extract_commit_metrics(commit_hash, dir_path)
    if not metrics:
        return "No valid benchmark data found."
    
    # Store metadata with metrics
    metadata = read_benchmark_metadata(dir_path)
    metrics['_tag'] = metadata.get('tag', commit_hash[:8])
    
    commits_data = {commit_hash: metrics}
    sorted_commits = [commit_hash]
    display_names = [metrics['_tag']]
    
    return _build_markdown_content(commits_data, sorted_commits, display_names, [(commit_hash, dir_path)])


def _build_markdown_content(commits_data: Dict[str, Dict[str, Any]], 
                           sorted_commits: List[str], 
                           display_names: List[str],
                           benchmark_dirs: List[Tuple[str, str]]) -> str:
    """Build the complete markdown content for benchmark report."""
    table_lines = []

    # AI Token Count and Price Table
    table_lines.extend([
        "## 📊 Latest AI Cost Benchmark",
        "",
        "### AI Token Usage and Cost",
        "",
        f"| Metric | {' | '.join(display_names)} |",
        "|" + "|".join(["--------"] * (len(display_names) + 1)) + "|"
    ])

    for metric in AI_METRICS:
        if any(metric in commits_data[commit] for commit in sorted_commits):
            row_values = []
            for commit in sorted_commits:
                value = commits_data[commit].get(metric)
                std_dev = commits_data[commit].get('Latency Std Dev') if metric == 'Average Latency' else None
                
                # Add percentage change for AI Cost (except for first column)
                if metric == 'AI Cost' and value is not None:
                    # Get first column value for comparison
                    first_commit = sorted_commits[0]
                    first_value = commits_data[first_commit].get(metric)
                    
                    if commit == first_commit:
                        # First column - no percentage
                        row_values.append(format_metric_value(metric, value, std_dev))
                    elif first_value is not None and first_value > 0:
                        percentage_change = ((value - first_value) / first_value) * 100
                        if percentage_change >= 0:
                            formatted_value = f"{format_metric_value(metric, value, std_dev)} (+{percentage_change:.1f}%)"
                        else:
                            formatted_value = f"{format_metric_value(metric, value, std_dev)} ({percentage_change:.1f}%)"
                        row_values.append(formatted_value)
                    else:
                        row_values.append(format_metric_value(metric, value, std_dev))
                else:
                    row_values.append(format_metric_value(metric, value, std_dev))

            # Add reference mark for AI Cost
            metric_display = f"{metric}*" if metric == 'AI Cost' else metric
            table_lines.append(f"| {metric_display} | {' | '.join(row_values)} |")

    table_lines.append("")
    
    # Add AI pricing note
    input_price = os.getenv('GEMINI_3_FLASH_PREVIEW_INPUT_TOKEN_PRICE_PER_MILLION', '0')
    output_price = os.getenv('GEMINI_3_FLASH_PREVIEW_OUTPUT_TOKEN_PRICE_PER_MILLION', '0')
    table_lines.extend([
        rf"*Model: gemini-3-flash-preview. Input Token Price: \${input_price} / million. Output Token Price: \${output_price} / million.",
        ""
    ])

    # Supplementary Performance Indicators Table
    table_lines.extend([
        "### Supplementary Performance Indicators",
        "",
        "*Indicative metrics based on limited test iterations for development insights.*",
        "",
        f"| Metric | {' | '.join(display_names)} |",
        "|" + "|".join(["--------"] * (len(display_names) + 1)) + "|"
    ])

    for metric in SUPPLEMENTARY_METRICS:
        if any(metric in commits_data[commit] for commit in sorted_commits):
            row_values = []
            for commit in sorted_commits:
                value = commits_data[commit].get(metric)
                
                # Special handling for Indicative Latency
                if metric == 'Indicative Latency':
                    test_iterations = commits_data[commit].get('Test Iterations', 1)
                    row_values.append(format_indicative_latency(value, test_iterations))
                else:
                    std_dev = commits_data[commit].get('Latency Std Dev') if 'Average' in metric else None
                    row_values.append(format_metric_value(metric, value, std_dev))

            table_lines.append(f"| {metric} | {' | '.join(row_values)} |")

    table_lines.append("")

    # Add simple footer note with iteration info from execution summary
    test_iterations = [commits_data[commit].get('Test Iterations', 0) for commit in sorted_commits]
    total_traces = [commits_data[commit].get('Total Benchmark Traces', 0) for commit in sorted_commits]
    
    # Read execution summary for accurate iteration counts
    execution_summaries = {}
    for commit_hash, dir_path in benchmark_dirs:
        summary = read_execution_summary(dir_path)
        if summary:
            execution_summaries[commit_hash] = summary

    if test_iterations and total_traces and execution_summaries:
        avg_iterations = sum(test_iterations) // len(test_iterations)
        avg_total_traces = sum(total_traces) // len(total_traces)
        
        # Get warmup iterations from execution summary
        warmup_iterations = 0
        if execution_summaries:
            first_commit = sorted_commits[0]
            summary = execution_summaries.get(first_commit, {})
            warmup_iterations = summary.get('warmupIterations', 0)
        
        table_lines.extend([
            "---",
            f"*AI Cost Benchmark: {avg_iterations} test iteration(s) per commit after {warmup_iterations} warmup exclusion.*"
        ])

    return "\n".join(table_lines)


def main():
    """Main function for deprecated initial report creation."""
    import argparse
    
    parser = argparse.ArgumentParser(description='DEPRECATED: Initial Benchmark Report Creation Tool')
    parser.add_argument('--commit', required=True, help='Commit hash for initial report')
    parser.add_argument('--dir', required=True, help='Directory path for benchmark data')
    
    args = parser.parse_args()
    
    print("DEPRECATED: This script is archived. Use trace_ai_benchmark_comparison.py --mode create for new implementations.")
    print(f"Creating initial benchmark report for {args.commit}...")
    
    content = create_initial_benchmark_report(args.commit, args.dir)
    
    if content == "No valid benchmark data found.":
        print("No valid benchmark data found.")
        return
    
    # Save report
    from pathlib import Path
    reports_dir = Path(os.path.join(os.path.dirname(__file__), "..", "results", "reports"))
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_file = reports_dir / f"ai-benchmark_{args.commit}_1commit_{Path(args.dir).name}.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Initial benchmark report saved to {output_file}")


if __name__ == "__main__":
    main()
