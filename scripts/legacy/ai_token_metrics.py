#!/usr/bin/env python3
"""
AI Token Metrics Module
Handles extraction and calculation of AI API token usage metrics from Prometheus data.
"""

import re
from typing import Dict, Optional


def extract_ai_token_metrics(metrics_data: dict) -> Dict[str, Optional[float]]:
    """
    Extract AI API token usage metrics from Prometheus data.
    
    Args:
        metrics_data: Dictionary containing the raw Prometheus metrics data
        
    Returns:
        Dictionary mapping token metric names to their values
    """
    raw_data = metrics_data.get('rawData', '')
    token_metrics = {}
    
    # Extract AI API Total Token Usage
    total_token_pattern = r'gen_ai_client_token_usage_total\{[^}]*gen_ai_token_type="total"[^}]*\}\s+([\d.]+)'
    total_token_match = re.search(total_token_pattern, raw_data)
    if total_token_match:
        try:
            token_metrics['AI Total Tokens'] = float(total_token_match.group(1))
        except ValueError:
            token_metrics['AI Total Tokens'] = None
    else:
        token_metrics['AI Total Tokens'] = None
    
    # Extract AI API Cached Token Usage (if available)
    # Note: Spring AI doesn't currently expose cached token metrics, but we'll look for them
    cached_token_pattern = r'gen_ai_client_token_usage_total\{[^}]*gen_ai_token_type="cached"[^}]*\}\s+([\d.]+)'
    cached_token_match = re.search(cached_token_pattern, raw_data)
    if cached_token_match:
        try:
            token_metrics['AI Cached Tokens'] = float(cached_token_match.group(1))
        except ValueError:
            token_metrics['AI Cached Tokens'] = None
    else:
        token_metrics['AI Cached Tokens'] = None
    
    return token_metrics
