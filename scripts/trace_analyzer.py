#!/usr/bin/env python3
"""
Main Trace Analyzer Script
Analyzes Zipkin trace data to extract individual request timings and generate professional reports.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any

# Import modularized components
from trace_parser import TraceParser
from trace_statistics import TraceStatistics
from trace_reporter import TraceReporter


def analyze_trace_data(trace_file: str, output_format: str = 'markdown') -> str:
    """
    Analyze trace data and generate report.
    
    Args:
        trace_file: Path to the raw-zipkin-traces.json file
        output_format: Output format ('markdown' or 'json')
        
    Returns:
        Generated report as string
    """
    try:
        # Initialize parser and load data
        parser = TraceParser(trace_file)
        reporter = TraceReporter()
        
        # Extract different types of data
        http_requests = parser.get_http_requests()
        benchmark_requests = parser.get_benchmark_requests()
        
        # Analyze specific span types
        span_analyses = {
            'gmail_create_client': parser.get_spans_by_name('create_client'),
            'gmail_list_message_ids': parser.get_spans_by_name('list_message_ids'),
            'gmail_get_first_message_id': parser.get_spans_by_name('get_first_message-id'),
            'gmail_get_messages': parser.get_spans_by_name('get_messages'),
            'analyze_google_account': parser.get_spans_by_name('analyze_google_account'),
            'analyze_service_provider': parser.get_spans_by_name('analyze_service_provider'),
            'email_categorization': parser.get_spans_by_name('categorization'),
            'security_filterchain': parser.get_spans_by_name('security filterchain')
        }
        
        # Generate report based on format
        if output_format.lower() == 'json':
            return reporter.generate_json_report(http_requests, benchmark_requests, span_analyses)
        else:
            return reporter.generate_summary_report(http_requests, benchmark_requests, span_analyses)
            
    except Exception as e:
        return f"Error analyzing trace data: {e}"


def print_console_summary(trace_file: str) -> None:
    """
    Print a quick console summary of trace analysis.
    
    Args:
        trace_file: Path to the raw-zipkin-traces.json file
    """
    try:
        parser = TraceParser(trace_file)
        
        # Get basic information
        traces = parser.get_all_traces()
        http_requests = parser.get_http_requests()
        benchmark_requests = parser.get_benchmark_requests()
        
        print(f"=== Trace Analysis Summary ===")
        print(f"Total traces: {len(traces)}")
        print(f"HTTP requests: {len(http_requests)}")
        print(f"Benchmark requests: {len(benchmark_requests)}")
        print()
        
        # Show individual benchmark request timings
        if benchmark_requests:
            print("=== Individual Benchmark Request Timings ===")
            for i, req in enumerate(benchmark_requests, 1):
                print(f"  {i}. {req['span_name']}: {req['duration_ms']:.2f}ms")
            print()
            
            # Calculate and show statistics
            durations = [req['duration_ms'] for req in benchmark_requests]
            if len(durations) >= 2:
                stats = TraceStatistics.calculate_basic_stats(durations)
                cv = TraceStatistics.calculate_coefficient_of_variation(durations)
                
                print("=== Statistics ===")
                print(f"  Average: {stats['mean']:.2f}ms")
                print(f"  Min: {stats['min']:.2f}ms")
                print(f"  Max: {stats['max']:.2f}ms")
                print(f"  Range: {stats['range']:.2f}ms")
                print(f"  Std Dev: {stats['std_dev']:.2f}ms")
                print(f"  CV: {cv:.1f}%")
                print()
        
        # Show task breakdown
        print("=== Task Breakdown ===")
        task_spans = {
            'Gmail Create Client': parser.get_spans_by_name('create_client'),
            'Gmail List Messages': parser.get_spans_by_name('list_message_ids'),
            'Gmail Get First Message': parser.get_spans_by_name('get_first_message-id'),
            'Analyze Google Account': parser.get_spans_by_name('analyze_google_account'),
            'Security Filter Chain': parser.get_spans_by_name('security filterchain')
        }
        
        for task_name, spans in task_spans.items():
            if spans:
                durations = [span['duration_ms'] for span in spans]
                avg_duration = sum(durations) / len(durations)
                print(f"  {task_name}: {len(spans)} occurrences, avg {avg_duration:.2f}ms")
        
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Main function to run trace analysis."""
    parser = argparse.ArgumentParser(description='Analyze Zipkin trace data for performance benchmarking')
    parser.add_argument('trace_file', help='Path to raw-zipkin-traces.json file')
    parser.add_argument('--format', choices=['markdown', 'json'], default='markdown',
                       help='Output format (default: markdown)')
    parser.add_argument('--output', '-o', help='Output file path (default: stdout)')
    parser.add_argument('--summary-only', action='store_true',
                       help='Only show console summary, no full report')
    
    args = parser.parse_args()
    
    # Validate input file
    trace_path = Path(args.trace_file)
    if not trace_path.exists():
        print(f"Error: Trace file not found: {args.trace_file}")
        sys.exit(1)
    
    if not trace_path.name.endswith('raw-zipkin-traces.json'):
        print("Warning: Expected raw-zipkin-traces.json file")
    
    # Show console summary
    print_console_summary(args.trace_file)
    
    # Generate full report unless summary-only is specified
    if not args.summary_only:
        report = analyze_trace_data(args.trace_file, args.format)
        
        if args.output:
            # Save to file
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            print(f"Report saved to: {output_path}")
        else:
            # Print to console
            print("\n" + "="*50)
            print("FULL REPORT")
            print("="*50)
            print(report)


if __name__ == "__main__":
    main()
