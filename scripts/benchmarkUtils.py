#!/usr/bin/env python3
"""
Trace-based Benchmark Comparison Script - Column Addition Only
This script adds columns to existing benchmark comparison reports.
Modularized version using separate modules for different responsibilities.
"""

import os
import sys
from typing import Dict, List

# Import modularized components
from dataUtils import load_all_commit_data
from csvUtils import (
    parse_existing_csv, 
    update_csv_with_new_column,
    AI_METRICS,
    SUPPLEMENTARY_METRICS
)
from markdownUtils import convert_csv_to_markdown


def main():
    """Main function to add column to existing benchmark CSV reports."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Benchmark Column Addition Tool')
    parser.add_argument('--existing-report', required=True, help='Path to existing report directory')
    parser.add_argument('--commit', required=True, help='Commit hash for new column')
    parser.add_argument('--dir', required=True, help='Directory path for new benchmark data')
    parser.add_argument('--generate-markdown', action='store_true', help='Generate markdown from CSV and update README.md')
    
    args = parser.parse_args()
    
    # Load all commit data
    commits_data, final_dirs = load_all_commit_data(args.commit, args.dir)
    if not commits_data:
        return False
    
    sorted_commits = sorted(commits_data.keys(), key=lambda x: commits_data[x]['_tag'])
    display_names = [commits_data[commit]['_tag'] for commit in sorted_commits]
    
    # Set up CSV file paths
    reports_dir = os.path.join(args.existing_report, "reports")
    ai_metrics_csv = os.path.join("results", "reports", "ai-metrics.csv")
    supplementary_metrics_csv = os.path.join("results", "reports", "supplementary-metrics.csv")
    
    # Get the new commit and its tag (use the specific commit passed as parameter)
    new_commit = args.commit
    new_tag = commits_data[new_commit]['_tag']
    new_metrics = commits_data[new_commit]
    
    success = True
    
    # Update AI Metrics CSV
    print(f"Updating AI metrics CSV for {args.commit}...")
    existing_ai_headers, existing_ai_data = parse_existing_csv(ai_metrics_csv)
    ai_success = update_csv_with_new_column(
        ai_metrics_csv, existing_ai_headers, existing_ai_data, 
        new_commit, new_tag, new_metrics, AI_METRICS
    )
    if ai_success:
        print(f"Successfully updated AI metrics CSV: {ai_metrics_csv}")
    else:
        print(f"Failed to update AI metrics CSV: {ai_metrics_csv}")
        success = False
    
    # Update Supplementary Metrics CSV
    print(f"Updating supplementary metrics CSV for {args.commit}...")
    existing_supplementary_headers, existing_supplementary_data = parse_existing_csv(supplementary_metrics_csv)
    supplementary_success = update_csv_with_new_column(
        supplementary_metrics_csv, existing_supplementary_headers, existing_supplementary_data, 
        new_commit, new_tag, new_metrics, SUPPLEMENTARY_METRICS
    )
    if supplementary_success:
        print(f"Successfully updated supplementary metrics CSV: {supplementary_metrics_csv}")
    else:
        print(f"Failed to update supplementary metrics CSV: {supplementary_metrics_csv}")
        success = False
    
    # Generate markdown if requested
    if args.generate_markdown and success:
        print(f"Generating markdown from CSV files...")
        try:
            markdown_content = convert_csv_to_markdown(ai_metrics_csv, supplementary_metrics_csv, final_dirs)
            
            # Write markdown to a temporary file for GitHub Actions to use
            temp_markdown_file = os.path.join("results", "reports", "latest-benchmark-results.md")
            with open(temp_markdown_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            print(f"Markdown generated and saved to: {temp_markdown_file}")
            
        except Exception as e:
            print(f"Error generating markdown: {e}")
            success = False
    
    return success


if __name__ == "__main__":
    main()
