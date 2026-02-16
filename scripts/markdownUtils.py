#!/usr/bin/env python3
"""
Markdown Utils Module
Handles conversion of CSV data to markdown format for README display.
"""

import argparse
import csv
import os
import sys
from typing import List, Tuple

from csvUtils import AI_METRICS, SUPPLEMENTARY_METRICS
from dataUtils import read_execution_summary


def format_markdown_value(metric_name: str, raw_value: str, baseline_value: str = None, show_percentage: bool = False) -> str:
    """Format raw CSV value for markdown display with appropriate units and optional percentage change."""
    if raw_value == "N/A":
        return "N/A"
    
    try:
        # Handle comma-separated values (for stats)
        if ',' in raw_value:
            parts = raw_value.split(',')
            if len(parts) == 2:  # avg,std_dev
                avg, std_dev = float(parts[0]), float(parts[1])
                if 'Token' in metric_name or 'Total Tokens' in metric_name:
                    formatted = f"{int(avg)} ± {int(std_dev)} tokens"
                elif 'AI Cost' in metric_name:
                    price_per_1k = avg * 1000
                    formatted = f"${price_per_1k:.3f} / 1K requests"
                    # Add percentage change for AI Cost if baseline provided
                    if show_percentage and baseline_value and baseline_value != "N/A":
                        try:
                            baseline_avg = float(baseline_value.split(',')[0]) if ',' in baseline_value else float(baseline_value)
                            if baseline_avg != 0:
                                change_pct = ((avg - baseline_avg) / baseline_avg) * 100
                                if change_pct > 0:
                                    formatted += f" (+{change_pct:+.1f}%)"
                                else:
                                    formatted += f" ({change_pct:+.1f}%)"
                        except (ValueError, ZeroDivisionError):
                            pass
                else:  # time metrics
                    avg_sec, std_dev_sec = avg / 1000, std_dev / 1000
                    formatted = f"{avg_sec:.2f} ± {std_dev_sec:.2f} s"
            elif len(parts) == 3:  # avg,std_dev,max for latency
                avg, std_dev, max_val = float(parts[0]), float(parts[1]), float(parts[2])
                avg_sec, std_dev_sec, max_sec = avg / 1000, std_dev / 1000, max_val / 1000
                formatted = f"{avg_sec:.2f} ± {std_dev_sec:.2f} s (max: {max_sec:.2f} s)"
        
        # Handle single values
        else:
            value = float(raw_value)
            
            # Handle token counts
            if 'Token Count' in metric_name or 'Total Tokens' in metric_name:
                formatted = f"{int(value)} tokens"
            
            # Handle AI price
            elif 'AI Cost' in metric_name:
                if value == 0:
                    formatted = "$0.000 / 1K requests"
                else:
                    price_per_1k = value * 1000
                    formatted = f"${price_per_1k:.3f} / 1K requests"
                
                # Add percentage change for AI Cost if baseline provided
                if show_percentage and baseline_value and baseline_value != "N/A":
                    try:
                        baseline_val = float(baseline_value)
                        if baseline_val != 0:
                            change_pct = ((value - baseline_val) / baseline_val) * 100
                            if change_pct > 0:
                                formatted += f" (+{change_pct:+.1f}%)"
                            else:
                                formatted += f" ({change_pct:+.1f}%)"
                    except (ValueError, ZeroDivisionError):
                        pass
            
            # Handle percentage-based metrics
            elif 'CV' in metric_name:
                formatted = f"{value:.1f}%"
            
            # Convert to seconds for time-based metrics
            else:
                value_seconds = value / 1000
                formatted = f"{value_seconds:.2f} s"
        
        return formatted
        
    except (ValueError, TypeError):
        return raw_value


def convert_csv_to_markdown(ai_csv_path: str, supplementary_csv_path: str, 
                            benchmark_dirs: List[Tuple[str, str]]) -> str:
    """Convert CSV files to markdown format for README display."""
    try:
        # Read AI metrics CSV
        ai_data = {}
        ai_versions = []
        if os.path.exists(ai_csv_path):
            with open(ai_csv_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                ai_headers = reader.fieldnames or []
                
                for row in reader:
                    version_name = row.get('Version', '')
                    if version_name:
                        ai_data[version_name] = {header: row.get(header, '') for header in ai_headers}
                        ai_versions.append(version_name)
        
        # Read supplementary metrics CSV
        supplementary_data = {}
        supplementary_versions = []
        if os.path.exists(supplementary_csv_path):
            with open(supplementary_csv_path, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                supplementary_headers = reader.fieldnames or []
                
                for row in reader:
                    version_name = row.get('Version', '')
                    if version_name:
                        supplementary_data[version_name] = {header: row.get(header, '') for header in supplementary_headers}
                        supplementary_versions.append(version_name)
        
        # Use versions from AI metrics (they should be the same)
        display_versions = ai_versions if ai_versions else supplementary_versions
        
        if not display_versions:
            return "No benchmark data available."
        
        # Sort versions (usually chronological)
        display_versions.sort()
        
        # Build markdown content
        markdown_lines = []
        
        # AI Token Usage and Cost section
        markdown_lines.extend([
            "## 📊 Latest AI Cost Benchmark",
            "",
            "### AI Token Usage and Cost",
            "",
            f"| Metric | {' | '.join(display_versions)} |",
            "|" + "|".join(["--------"] * (len(display_versions) + 1)) + "|"
        ])
        
        # AI metrics rows (one per metric)
        for metric in AI_METRICS:
            row_values = []
            # Get baseline value (first version) for percentage calculation
            baseline_version = display_versions[0] if display_versions else None
            baseline_value = ai_data[baseline_version].get(metric, '') if baseline_version and baseline_version in ai_data else None
            
            for i, version in enumerate(display_versions):
                if version in ai_data:
                    # Show percentage change for AI Cost (except for baseline)
                    show_pct = (metric == 'AI Cost' and i > 0)
                    baseline_for_pct = baseline_value if show_pct else None
                    row_values.append(format_markdown_value(metric, ai_data[version].get(metric, ''), baseline_for_pct, show_pct))
                else:
                    row_values.append("N/A")
            markdown_lines.append(f"| {metric} | {' | '.join(row_values)} |")
        
        markdown_lines.extend([
            "",
            "*Model: gemini-3-flash-preview. Input Token Price: $" + os.getenv('GEMINI_3_FLASH_PREVIEW_INPUT_TOKEN_PRICE_PER_MILLION', '0') + " / million. Output Token Price: $" + os.getenv('GEMINI_3_FLASH_PREVIEW_OUTPUT_TOKEN_PRICE_PER_MILLION', '0') + " / million.",
            "",
            "### Supplementary Performance Indicators",
            "",
            "*Indicative metrics based on limited test iterations for development insights.*",
            "",
            f"| Metric | {' | '.join(display_versions)} |",
            "|" + "|".join(["--------"] * (len(display_versions) + 1)) + "|"
        ])
        
        # Supplementary metrics rows (one per metric)
        for metric in SUPPLEMENTARY_METRICS:
            row_values = []
            for version in display_versions:
                if version in supplementary_data:
                    row_values.append(format_markdown_value(metric, supplementary_data[version].get(metric, '')))
                else:
                    row_values.append("N/A")
            markdown_lines.append(f"| {metric} | {' | '.join(row_values)} |")
        
        markdown_lines.append("")
        
        # Add footer note with iteration info from execution summaries
        execution_summaries = {}
        for commit_hash, dir_path in benchmark_dirs:
            summary = read_execution_summary(dir_path)
            if summary:
                execution_summaries[commit_hash] = summary
        
        if execution_summaries:
            avg_iterations = sum(s.get('testIterations', 1) for s in execution_summaries.values()) / len(execution_summaries)
            warmup_iterations = sum(s.get('warmupIterations', 0) for s in execution_summaries.values()) / len(execution_summaries)
            
            markdown_lines.extend([
                "---",
                f"*AI Cost Benchmark: {avg_iterations:.0f} test iteration(s) per commit after {warmup_iterations:.0f} warmup exclusion.*"
            ])
        
        return "\n".join(markdown_lines)
        
    except Exception as e:
        print(f"Error converting CSV to markdown: {e}")
        return f"Error converting benchmark data to markdown: {e}"


def main():
    """Main function to generate markdown from CSV files."""
    parser = argparse.ArgumentParser(description='Markdown Generation Tool')
    parser.add_argument('--ai-csv', required=True, help='Path to AI metrics CSV file')
    parser.add_argument('--supplementary-csv', required=True, help='Path to supplementary metrics CSV file')
    parser.add_argument('--existing-report', required=True, help='Path to existing report directory (for execution summaries)')
    parser.add_argument('--commits', nargs='+', help='List of commit hashes for execution summary data')
    parser.add_argument('--dirs', nargs='+', help='List of directory paths for execution summary data')
    
    args = parser.parse_args()
    
    # Build benchmark directories list
    benchmark_dirs = []
    if args.commits and args.dirs and len(args.commits) == len(args.dirs):
        benchmark_dirs = list(zip(args.commits, args.dirs))
    
    # Generate markdown
    print(f"Generating markdown from CSV files...")
    try:
        markdown_content = convert_csv_to_markdown(
            args.ai_csv, 
            args.supplementary_csv, 
            benchmark_dirs
        )
        
        # Write markdown to file for GitHub Actions to use
        temp_markdown_file = "results/reports/latest-benchmark-results.md"
        with open(temp_markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"Markdown generated and saved to: {temp_markdown_file}")
        
    except Exception as e:
        print(f"Error generating markdown: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
