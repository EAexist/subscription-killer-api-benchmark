#!/usr/bin/env python3
"""
Gmail API Metrics Module
Handles extraction and calculation of Gmail API Critical I/O metrics from Prometheus data.
"""

import re
from typing import Optional, Dict


def extract_gmail_critical_io(metrics_data: dict) -> Optional[float]:
    """
    Extract Gmail API Critical I/O from Prometheus metrics data.
    
    Gmail API Critical I/O = gmail_createClient_seconds_sum + gmail_getFirstMessageId_seconds_sum
    
    Args:
        metrics_data: Dictionary containing the raw Prometheus metrics data
        
    Returns:
        Gmail API Critical I/O time in seconds, or None if not found
    """
    raw_data = metrics_data.get('rawData', '')
    
    # Extract gmail_createClient_seconds_sum
    gmail_create_pattern = r'gmail_createClient_seconds_sum\{[^}]*\}\s+([\d.]+)'
    gmail_create_match = re.search(gmail_create_pattern, raw_data)
    gmail_create_total = float(gmail_create_match.group(1)) if gmail_create_match else 0
    
    # Extract gmail_getFirstMessageId_seconds_sum
    gmail_first_msg_pattern = r'gmail_getFirstMessageId_seconds_sum\{[^}]*\}\s+([\d.]+)'
    gmail_first_msg_match = re.search(gmail_first_msg_pattern, raw_data)
    gmail_first_msg_total = float(gmail_first_msg_match.group(1)) if gmail_first_msg_match else 0
    
    # Calculate Gmail API Critical I/O (sum of Gmail operations)
    gmail_critical_io = gmail_create_total + gmail_first_msg_total
    
    return gmail_critical_io if gmail_critical_io > 0 else None


def calculate_orchestration_overhead(average_latency: Optional[float], gmail_critical_io: Optional[float]) -> Optional[float]:
    """
    Calculate Orchestration Overhead = Average Latency - Gmail API Critical I/O.
    
    Args:
        average_latency: Average latency in seconds
        gmail_critical_io: Gmail API Critical I/O time in seconds
        
    Returns:
        Orchestration overhead in seconds, or None if inputs are invalid
    """
    if average_latency is not None and gmail_critical_io is not None:
        orchestration_overhead = average_latency - gmail_critical_io
        return orchestration_overhead if orchestration_overhead > 0 else 0
    else:
        return None
