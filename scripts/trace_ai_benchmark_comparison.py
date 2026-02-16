#!/usr/bin/env python3
"""
Trace-based Benchmark Comparison Script - Column Addition Only
This script adds columns to existing benchmark comparison reports.
For creating initial reports, use create_initial_benchmark_report.py (deprecated) or trace_ai_benchmark_comparison.py --mode create
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


def _load_all_commit_data(new_commit_hash: str, new_dir_path: str) -> Tuple[Dict[str, Dict[str, Any]], List[Tuple[str, str]]]:
    """Load all commit data including new commit."""
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
                    first_commit = sorted_commits[0]
                    first_value = commits_data[first_commit].get(metric)
                    
                    if commit == first_commit:
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
                
                if metric == 'Indicative Latency':
                    test_iterations = commits_data[commit].get('Test Iterations', 1)
                    row_values.append(format_indicative_latency(value, test_iterations))
                else:
                    std_dev = commits_data[commit].get('Latency Std Dev') if 'Average' in metric else None
                    row_values.append(format_metric_value(metric, value, std_dev))

            table_lines.append(f"| {metric} | {' | '.join(row_values)} |")

    table_lines.append("")

    # Add footer note with iteration info
    execution_summaries = {}
    for commit_hash, dir_path in benchmark_dirs:
        summary = read_execution_summary(dir_path)
        if summary:
            execution_summaries[commit_hash] = summary

    test_iterations = [commits_data[commit].get('Test Iterations', 0) for commit in sorted_commits]
    total_traces = [commits_data[commit].get('Total Benchmark Traces', 0) for commit in sorted_commits]

    if test_iterations and total_traces and execution_summaries:
        avg_iterations = sum(test_iterations) // len(test_iterations)
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


def _parse_existing_table(existing_content: str) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    """Parse existing table to extract headers and data."""
    lines = existing_content.split('\n')
    
    # Find header row
    header_row = None
    for line in lines:
        if line.startswith('| Metric |') and line.count('|') >= 2:
            header_row = line
            break
    
    if not header_row:
        return [], {}
    
    # Extract column headers (git tags)
    headers = [h.strip() for h in header_row.split('|')[2:-1]]  # Skip first "Metric" column
    
    # Parse data rows
    table_data = {}
    for line in lines:
        if line.startswith('| ') and ' | ' in line:
            parts = [p.strip() for p in line.split('|')[1:-1]]  # Remove first and last empty elements
            if len(parts) >= 2:  # At least metric name + one column
                metric_name = parts[0]
                column_values = parts[1:]  # Skip metric name
                table_data[metric_name] = {headers[i]: column_values[i] for i in range(min(len(headers), len(column_values)))}
    
    return headers, table_data


def _extract_metric_value(value: Any) -> Optional[float]:
    """Extract numeric value from metric data."""
    if isinstance(value, dict):
        return value.get('average') or value.get('value') or next(
            (v for v in value.values() if isinstance(v, (int, float))), None
        )
    return float(value) if value is not None else None


def _format_ai_cost_value(actual_value: Optional[float], first_value: float, col_index: int) -> str:
    """Format AI Cost value with percentage change if not first column."""
    if col_index == 0:
        return format_metric_value('AI Cost', actual_value)
    
    if first_value > 0 and actual_value is not None:
        # Convert to same unit (per 1K requests) for percentage calculation
        current_value_per_1k = actual_value * 1000
        percentage_change = ((current_value_per_1k - first_value) / first_value) * 100
        base_formatted = format_metric_value('AI Cost', actual_value)
        sign = '+' if percentage_change >= 0 else ''
        return f"{base_formatted} ({sign}{percentage_change:.1f}%)"
    
    return format_metric_value('AI Cost', actual_value)


def _update_table_with_new_column(existing_headers: List[str], existing_data: Dict[str, Dict[str, str]], 
                              new_commit: str, new_tag: str, new_metrics: Dict[str, Any]) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    """Update table by replacing existing column or adding new column."""
    
    # Determine column operation
    col_index = existing_headers.index(new_tag) if new_tag in existing_headers else len(existing_headers)
    if new_tag in existing_headers:
        print(f"Replacing existing column for tag: {new_tag}")
    else:
        existing_headers.append(new_tag)
        print(f"Adding new column for tag: {new_tag}")
    
    # Update metrics
    for metric_name, value in new_metrics.items():
        if metric_name == '_tag':
            continue
        
        # Ensure metric entry exists
        if metric_name not in existing_data:
            existing_data[metric_name] = {}
        
        # Extract and format value
        actual_value = _extract_metric_value(value)
        
        if metric_name == 'AI Cost':
            # Handle AI Cost with percentage calculations
            existing_cost_key = 'AI Cost*' if 'AI Cost*' in existing_data else 'AI Cost'
            first_tag = existing_headers[0] if existing_headers else None
            
            if first_tag and first_tag in existing_data.get(existing_cost_key, {}):
                first_value_str = existing_data[existing_cost_key][first_tag]
                first_value = float(first_value_str.split('$')[1].split()[0]) if '$' in first_value_str else 0
                formatted_value = _format_ai_cost_value(actual_value, first_value, col_index)
            else:
                formatted_value = format_metric_value(metric_name, actual_value)
            
            storage_key = existing_cost_key
        else:
            # Handle other metrics
            std_dev = value.get('std_dev') if isinstance(value, dict) else None
            formatted_value = format_metric_value(metric_name, actual_value, std_dev)
            storage_key = metric_name
        
        # Store formatted value
        existing_data[storage_key][new_tag] = formatted_value
    
    return existing_headers, existing_data


def _build_updated_table_content(headers: List[str], table_data: Dict[str, Dict[str, str]], 
                             benchmark_dirs: List[Tuple[str, str]]) -> str:
    """Build updated table content from parsed data."""
    table_lines = []
    
    # AI Token Usage and Cost section
    table_lines.extend([
        "### AI Token Usage and Cost",
        "",
        f"| Metric | {' | '.join(headers)} |",
        "|" + "|".join(["--------"] * (len(headers) + 1)) + "|"
    ])
    
    # AI metrics
    for metric in AI_METRICS:
        metric_key = 'AI Cost*' if metric == 'AI Cost' and 'AI Cost*' in table_data else metric
        if metric_key in table_data:
            metric_display = f"{metric}*" if metric == 'AI Cost' else metric
            row_values = [table_data[metric_key].get(header, '') for header in headers]
            table_lines.append(f"| {metric_display} | {' | '.join(row_values)} |")
    
    table_lines.extend([
        "",
        "*Model: gemini-3-flash-preview. Input Token Price: $" + os.getenv('GEMINI_3_FLASH_PREVIEW_INPUT_TOKEN_PRICE_PER_MILLION', '0') + " / million. Output Token Price: $" + os.getenv('GEMINI_3_FLASH_PREVIEW_OUTPUT_TOKEN_PRICE_PER_MILLION', '0') + " / million.",
        "",
        "### Supplementary Performance Indicators",
        "",
        f"| Metric | {' | '.join(headers)} |",
        "|" + "|".join(["--------"] * (len(headers) + 1)) + "|"
    ])
    
    # Supplementary metrics
    for metric in SUPPLEMENTARY_METRICS:
        if metric in table_data:
            row_values = [table_data[metric].get(header, '') for header in headers]
            table_lines.append(f"| {metric} | {' | '.join(row_values)} |")
    
    table_lines.append("")
    
    # Add footer note with iteration info
    execution_summaries = {}
    for commit_hash, dir_path in benchmark_dirs:
        summary = read_execution_summary(dir_path)
        if summary:
            execution_summaries[commit_hash] = summary

    if execution_summaries:
        avg_iterations = sum(s.get('testIterations', 1) for s in execution_summaries.values()) / len(execution_summaries)
        warmup_iterations = sum(s.get('warmupIterations', 0) for s in execution_summaries.values()) / len(execution_summaries)
        
        table_lines.extend([
            "---",
            f"*AI Cost Benchmark: {avg_iterations:.0f} test iteration(s) per commit after {warmup_iterations:.0f} warmup exclusion.*"
        ])
    
    return "\n".join(table_lines)


def _update_readme_with_new_content_smart(existing_readme_path: str, commits_data: Dict[str, Dict[str, Any]], 
                                     final_dirs: List[Tuple[str, str]]) -> bool:
    """Update README.md by replacing existing column or adding new column."""
    try:
        with open(existing_readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        lines = readme_content.split('\n')
        start_idx = None
        end_idx = None
        
        for i, line in enumerate(lines):
            if '<!-- BENCHMARK_RESULTS_START -->' in line:
                start_idx = i
            elif '<!-- BENCHMARK_RESULTS_END -->' in line:
                end_idx = i
                break
        
        if start_idx is None or end_idx is None:
            print("Error: Could not find benchmark section markers in README.md")
            return False
        
        # Extract existing benchmark content
        existing_benchmark_content = '\n'.join(lines[start_idx+1:end_idx])
        
        # Parse existing table
        existing_headers, existing_data = _parse_existing_table(existing_benchmark_content)
        
        # Get the new commit and its tag
        new_commit = list(commits_data.keys())[-1]  # Last commit is the new one
        new_tag = commits_data[new_commit]['_tag']
        new_metrics = commits_data[new_commit]
        
        # Update table with new column (replace or add)
        updated_headers, updated_data = _update_table_with_new_column(
            existing_headers, existing_data, new_commit, new_tag, new_metrics
        )
        
        # Build updated table content
        updated_table_content = _build_updated_table_content(updated_headers, updated_data, final_dirs)
        
        # Replace benchmark section in README
        updated_lines = (
            lines[:start_idx+1] + 
            [updated_table_content] + 
            lines[end_idx:]
        )
        
        with open(existing_readme_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(updated_lines))
        
        return True
        
    except Exception as e:
        print(f"Error updating README.md: {e}")
        return False


def _update_readme_with_new_content(existing_readme_path: str, new_content: str) -> bool:
    """Update README.md by replacing the benchmark section with new content."""
    try:
        with open(existing_readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        lines = readme_content.split('\n')
        start_idx = None
        end_idx = None
        
        for i, line in enumerate(lines):
            if '<!-- BENCHMARK_RESULTS_START -->' in line:
                start_idx = i
            elif '<!-- BENCHMARK_RESULTS_END -->' in line:
                end_idx = i
                break
        
        if start_idx is None or end_idx is None:
            print("Error: Could not find benchmark section markers in README.md")
            return False
        
        new_lines = lines[:start_idx] + [new_content] + lines[end_idx+1:]
        
        with open(existing_readme_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        
        return True
        
    except Exception as e:
        print(f"Error updating README.md: {e}")
        return False


def main():
    """Main function to add column to existing benchmark report."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Benchmark Column Addition Tool')
    parser.add_argument('--existing-report', required=True, help='Path to existing report')
    parser.add_argument('--commit', required=True, help='Commit hash for new column')
    parser.add_argument('--dir', required=True, help='Directory path for new benchmark data')
    
    args = parser.parse_args()
    
    # Load all commit data (shared logic for both modes)
    commits_data, final_dirs = _load_all_commit_data(args.commit, args.dir)
    if not commits_data:
        return False
    
    sorted_commits = sorted(commits_data.keys(), key=lambda x: commits_data[x]['_tag'])
    display_names = [commits_data[commit]['_tag'] for commit in sorted_commits]
    
    # Handle different output modes
    if 'README.md' in args.existing_report:
        print(f"Adding column for {args.commit} to README.md...")
        success = _update_readme_with_new_content_smart(args.existing_report, commits_data, final_dirs)
        if success:
            print(f"Successfully added column for {args.commit} to {args.existing_report}")
        else:
            print(f"Failed to update {args.existing_report}")
        return success
    else:
        # Handle intermediate report file
        print(f"Processing intermediate report for {args.commit}...")
        
        # Build markdown content for intermediate file
        new_content = _build_markdown_content(commits_data, sorted_commits, display_names, final_dirs)
        
        # Check if file already exists (extracted from README.md)
        if os.path.exists(args.existing_report):
            print(f"Intermediate file exists, updating with new column...")
            # File exists - update it with new content
            os.makedirs(os.path.dirname(args.existing_report), exist_ok=True)
            with open(args.existing_report, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Successfully updated intermediate report: {args.existing_report}")
        else:
            print(f"Creating new intermediate report...")
            # File doesn't exist - create it
            os.makedirs(os.path.dirname(args.existing_report), exist_ok=True)
            with open(args.existing_report, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Successfully created intermediate report: {args.existing_report}")
        
        return True


if __name__ == "__main__":
    main()
