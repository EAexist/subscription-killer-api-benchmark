#!/usr/bin/env python3
"""
Trace Statistics Module
Handles statistical analysis of trace data.
"""

import statistics
from typing import List, Dict, Any, Optional, Tuple
import math


class TraceStatistics:
    """Handles statistical calculations for trace data."""
    
    @staticmethod
    def calculate_basic_stats(values: List[float]) -> Dict[str, float]:
        """
        Calculate basic statistics for a list of values.
        
        Args:
            values: List of numeric values
            
        Returns:
            Dictionary containing basic statistics
        """
        if not values:
            return {
                'count': 0,
                'mean': 0.0,
                'median': 0.0,
                'min': 0.0,
                'max': 0.0,
                'range': 0.0,
                'std_dev': 0.0,
                'variance': 0.0
            }
        
        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'min': min(values),
            'max': max(values),
            'range': max(values) - min(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0,
            'variance': statistics.variance(values) if len(values) > 1 else 0.0
        }
    
    @staticmethod
    def calculate_percentiles(values: List[float], percentiles: List[float] = None) -> Dict[str, float]:
        """
        Calculate percentiles for a list of values.
        
        Args:
            values: List of numeric values
            percentiles: List of percentiles to calculate (default: [50, 90, 95, 99])
            
        Returns:
            Dictionary containing percentile values
        """
        if percentiles is None:
            percentiles = [50, 90, 95, 99]
        
        if not values:
            return {f'p{p}': 0.0 for p in percentiles}
        
        sorted_values = sorted(values)
        result = {}
        
        for p in percentiles:
            index = (p / 100) * (len(sorted_values) - 1)
            if index.is_integer():
                result[f'p{p}'] = sorted_values[int(index)]
            else:
                lower = sorted_values[int(index)]
                upper = sorted_values[int(index) + 1]
                result[f'p{p}'] = lower + (upper - lower) * (index - int(index))
        
        return result
    
    @staticmethod
    def calculate_coefficient_of_variation(values: List[float]) -> float:
        """
        Calculate coefficient of variation (CV).
        
        Args:
            values: List of numeric values
            
        Returns:
            Coefficient of variation (0.0 if mean is 0)
        """
        if not values:
            return 0.0
        
        mean = statistics.mean(values)
        if mean == 0:
            return 0.0
        
        std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
        return (std_dev / mean) * 100
    
    @staticmethod
    def format_duration_stats(durations: List[float], unit: str = 'ms') -> Dict[str, str]:
        """
        Format duration statistics for display.
        
        Args:
            durations: List of duration values
            unit: Time unit for display ('ms' or 's')
            
        Returns:
            Dictionary with formatted statistics strings
        """
        stats = TraceStatistics.calculate_basic_stats(durations)
        cv = TraceStatistics.calculate_coefficient_of_variation(durations)
        
        # Convert to seconds if requested
        if unit == 's':
            for key in ['mean', 'median', 'min', 'max', 'range', 'std_dev', 'variance']:
                stats[key] = stats[key] / 1000
        
        return {
            'count': f"{stats['count']} iterations",
            'mean': f"{stats['mean']:.2f} {unit}",
            'median': f"{stats['median']:.2f} {unit}",
            'min': f"{stats['min']:.2f} {unit}",
            'max': f"{stats['max']:.2f} {unit}",
            'range': f"{stats['range']:.2f} {unit}",
            'std_dev': f"{stats['std_dev']:.2f} {unit}",
            'cv': f"{cv:.1f}%",
            'variance': f"{stats['variance']:.2f} {unit}²"
        }
    
    @staticmethod
    def analyze_performance_stability(durations: List[float]) -> Dict[str, Any]:
        """
        Analyze performance stability and categorize results.
        
        Args:
            durations: List of duration values
            
        Returns:
            Dictionary with stability analysis
        """
        if not durations:
            return {'stability': 'unknown', 'reason': 'no data'}
        
        cv = TraceStatistics.calculate_coefficient_of_variation(durations)
        stats = TraceStatistics.calculate_basic_stats(durations)
        
        # Categorize stability
        if cv < 10:
            stability = 'excellent'
            reason = 'low variability (CV < 10%)'
        elif cv < 20:
            stability = 'good'
            reason = 'moderate variability (CV < 20%)'
        elif cv < 30:
            stability = 'fair'
            reason = 'high variability (CV < 30%)'
        else:
            stability = 'poor'
            reason = 'very high variability (CV ≥ 30%)'
        
        # Check for outliers
        q1 = statistics.quantiles(durations, n=4)[0] if len(durations) >= 4 else min(durations)
        q3 = statistics.quantiles(durations, n=4)[2] if len(durations) >= 4 else max(durations)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers = [d for d in durations if d < lower_bound or d > upper_bound]
        
        return {
            'stability': stability,
            'reason': reason,
            'coefficient_of_variation': cv,
            'outliers': {
                'count': len(outliers),
                'values': outliers,
                'percentage': (len(outliers) / len(durations)) * 100
            },
            'stats': stats
        }
