#!/usr/bin/env python3
"""
CSV Operations Module
Handles reading, writing, and formatting of CSV benchmark data.
"""

import csv
import os
from typing import Any, Dict, List, Optional, Tuple


# Constants
AI_METRICS = [
    'AI Cost', 'Input Token Count', 'Output Token Count', 'Total Tokens'
]

SUPPLEMENTARY_METRICS = [
    'Indicative Latency', 'Gmail API Critical I/O',
    'AI Critical I/O', 'Total Critical I/O', 'Orchestration Overhead'
]


def format_csv_value(metric_name: str, value: Optional[float],
                    std_dev: Optional[float] = None) -> str:
    """Format metric value for CSV output - raw values only, no units."""
    if value is None:
        return "N/A"

    # Handle percentage-based metrics
    if 'CV' in metric_name:
        return f"{value:.1f}"

    # Handle token counts - return raw integer
    if 'Token Count' in metric_name or 'Total Tokens' in metric_name:
        return f"{int(value)}"
    
    # Handle AI price - return raw cost per request
    if 'AI Cost' in metric_name:
        return f"{value:.6f}"

    # Handle standard deviation for average values
    if std_dev is not None and ('Average' in metric_name or 'Indicative Average' in metric_name):
        return f"{value:.2f},{std_dev:.2f}"

    # Return raw milliseconds for time-based metrics
    return f"{value:.2f}"


def format_csv_indicative_latency(latency_data: Dict[str, Any], test_iterations: int = 1) -> str:
    """Format Indicative Latency for CSV output - raw values only."""
    if not latency_data or latency_data.get('average') is None:
        return "N/A"
    
    avg_ms = latency_data['average']
    
    # For single iteration, only show average
    if test_iterations == 1:
        return f"{avg_ms:.2f}"
    
    # For multiple iterations, show average,std_dev,max
    max_ms = latency_data['max']
    std_dev_ms = latency_data['std_dev']
    
    return f"{avg_ms:.2f},{std_dev_ms:.2f},{max_ms:.2f}"


def parse_existing_csv(csv_path: str) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
    """Parse existing CSV file to extract headers and data."""
    if not os.path.exists(csv_path):
        return [], {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            
            data = {}
            for row in reader:
                version_name = row.get('Version', '')
                if version_name:
                    data[version_name] = {header: row.get(header, '') for header in headers}
            
            return headers, data
    except Exception as e:
        print(f"Error parsing CSV {csv_path}: {e}")
        return [], {}


def extract_metric_value(value: Any) -> Optional[float]:
    """Extract numeric value from metric data."""
    if isinstance(value, dict):
        return value.get('average') or value.get('value') or next(
            (v for v in value.values() if isinstance(v, (int, float))), None
        )
    return float(value) if value is not None else None


def format_ai_cost_value(actual_value: Optional[float], first_value: float, col_index: int) -> str:
    """Format AI Cost value - raw values only, no percentage calculations."""
    return format_csv_value('AI Cost', actual_value)


def update_csv_with_new_column(csv_path: str, existing_headers: List[str], 
                               existing_data: Dict[str, Dict[str, str]], 
                               new_commit: str, new_tag: str, 
                               new_metrics: Dict[str, Any], metrics_list: List[str]) -> bool:
    """Update CSV file by adding new row (version) instead of column."""
    try:
        # Check if version already exists
        if new_tag in existing_data:
            print(f"Replacing existing row for version: {new_tag}")
        else:
            print(f"Adding new row for version: {new_tag}")
        
        # Update metrics for this version
        version_data = {}
        for metric_name in metrics_list:
            if metric_name in new_metrics:
                value = new_metrics[metric_name]
                
                # Extract and format value
                actual_value = extract_metric_value(value)
                
                # Handle all metrics with simple formatting
                if metric_name == 'Indicative Latency':
                    test_iterations = new_metrics.get('Test Iterations', 1)
                    formatted_value = format_csv_indicative_latency(value, test_iterations)
                else:
                    std_dev = value.get('std_dev') if isinstance(value, dict) else None
                    formatted_value = format_csv_value(metric_name, actual_value, std_dev)
                
                version_data[metric_name] = formatted_value
        
        # Store version data (this will add new or replace existing)
        existing_data[new_tag] = version_data
        
        # Write updated CSV
        with open(csv_path, 'w', encoding='utf-8', newline='\n') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(['Version'] + metrics_list)
            
            # Write data rows (versions) - preserve all existing versions
            for version_name in sorted(existing_data.keys()):
                row = [version_name] + [existing_data[version_name].get(metric, '') for metric in metrics_list]
                writer.writerow(row)
        
        return True
        
    except Exception as e:
        print(f"Error updating CSV {csv_path}: {e}")
        return False


def build_csv_content(commits_data: Dict[str, Dict[str, Any]], 
                      sorted_commits: List[str], 
                      display_names: List[str]) -> Tuple[str, str]:
    """Build CSV content for AI metrics and Supplementary metrics tables."""
    
    # AI Metrics CSV
    ai_csv_lines = []
    ai_headers = ['Metric'] + display_names
    ai_csv_lines.append(','.join(ai_headers))
    
    for metric in AI_METRICS:
        if any(metric in commits_data[commit] for commit in sorted_commits):
            row_values = [metric]
            for commit in sorted_commits:
                value = commits_data[commit].get(metric)
                std_dev = commits_data[commit].get('Latency Std Dev') if metric == 'Average Latency' else None
                
                # Simple formatting for all metrics
                row_values.append(format_csv_value(metric, value, std_dev))
            
            ai_csv_lines.append(','.join(row_values))
    
    # Supplementary Metrics CSV
    supplementary_csv_lines = []
    supplementary_headers = ['Metric'] + display_names
    supplementary_csv_lines.append(','.join(supplementary_headers))
    
    for metric in SUPPLEMENTARY_METRICS:
        if any(metric in commits_data[commit] for commit in sorted_commits):
            row_values = [metric]
            for commit in sorted_commits:
                value = commits_data[commit].get(metric)
                
                if metric == 'Indicative Latency':
                    test_iterations = commits_data[commit].get('Test Iterations', 1)
                    row_values.append(format_csv_indicative_latency(value, test_iterations))
                else:
                    std_dev = commits_data[commit].get('Latency Std Dev') if 'Average' in metric else None
                    row_values.append(format_csv_value(metric, value, std_dev))
            
            supplementary_csv_lines.append(','.join(row_values))
    
    return '\n'.join(ai_csv_lines), '\n'.join(supplementary_csv_lines)
