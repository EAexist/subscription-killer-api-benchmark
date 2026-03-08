#!/usr/bin/env python3
"""
Trace Reporter Module
Handles generating reports from trace analysis results.
"""

from typing import List, Dict, Any
from datetime import datetime
import json


class TraceReporter:
    """Handles generating formatted reports from trace data."""
    
    def __init__(self):
        self.report_data = {}
    
    def generate_summary_report(self, 
                            http_requests: List[Dict[str, Any]], 
                            benchmark_requests: List[Dict[str, Any]],
                            span_analyses: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Generate a comprehensive summary report.
        
        Args:
            http_requests: All HTTP request spans
            benchmark_requests: Benchmark-specific requests
            span_analyses: Analysis of different span types
            
        Returns:
            Formatted markdown report string
        """
        from trace_statistics import TraceStatistics
        
        lines = []
        lines.append("# Trace Analysis Report")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        
        if benchmark_requests:
            durations = [req['duration_ms'] for req in benchmark_requests]
            stats = TraceStatistics.calculate_basic_stats(durations)
            cv = TraceStatistics.calculate_coefficient_of_variation(durations)
            
            lines.append(f"- **Benchmark Requests**: {len(benchmark_requests)} iterations")
            lines.append(f"- **Average Duration**: {stats['mean']:.2f}ms")
            lines.append(f"- **Duration Range**: {stats['min']:.2f}ms - {stats['max']:.2f}ms")
            lines.append(f"- **Performance Stability**: {self._get_stability_rating(cv)} (CV: {cv:.1f}%)")
            lines.append("")
        
        # Individual Request Timings
        lines.append("## Individual Request Timings")
        lines.append("")
        
        if benchmark_requests:
            lines.append("| Iteration | Request | Duration (ms) | Timestamp (μs) |")
            lines.append("|-----------|---------|---------------|----------------|")
            
            for i, req in enumerate(benchmark_requests, 1):
                lines.append(f"| {i} | {req['span_name']} | {req['duration_ms']:.2f} | {req['timestamp']:.0f} |")
            lines.append("")
        
        # Statistical Analysis
        lines.append("## Statistical Analysis")
        lines.append("")
        
        if benchmark_requests:
            durations = [req['duration_ms'] for req in benchmark_requests]
            formatted_stats = TraceStatistics.format_duration_stats(durations)
            
            lines.append("### Benchmark Request Statistics")
            lines.append("")
            for key, value in formatted_stats.items():
                lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")
            lines.append("")
            
            # Percentiles
            percentiles = TraceStatistics.calculate_percentiles(durations)
            lines.append("### Percentiles")
            lines.append("")
            for p, value in percentiles.items():
                lines.append(f"- **{p.upper()}**: {value:.2f}ms")
            lines.append("")
        
        # Task Breakdown Analysis
        lines.append("## Task Breakdown Analysis")
        lines.append("")
        
        for span_name, spans in span_analyses.items():
            if spans:
                durations = [span['duration_ms'] for span in spans]
                stats = TraceStatistics.calculate_basic_stats(durations)
                
                lines.append(f"### {span_name}")
                lines.append("")
                lines.append(f"- **Occurrences**: {len(spans)}")
                lines.append(f"- **Average**: {stats['mean']:.2f}ms")
                lines.append(f"- **Range**: {stats['min']:.2f}ms - {stats['max']:.2f}ms")
                lines.append("")
        
        # Performance Insights
        lines.append("## Performance Insights")
        lines.append("")
        insights = self._generate_insights(benchmark_requests, span_analyses)
        for insight in insights:
            lines.append(f"- {insight}")
        lines.append("")
        
        return "\n".join(lines)
    
    def generate_json_report(self, 
                           http_requests: List[Dict[str, Any]], 
                           benchmark_requests: List[Dict[str, Any]],
                           span_analyses: Dict[str, List[Dict[str, Any]]]) -> str:
        """
        Generate a JSON report for programmatic consumption.
        
        Args:
            http_requests: All HTTP request spans
            benchmark_requests: Benchmark-specific requests
            span_analyses: Analysis of different span types
            
        Returns:
            JSON formatted report string
        """
        from trace_statistics import TraceStatistics
        
        report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'total_http_requests': len(http_requests),
                'benchmark_requests': len(benchmark_requests)
            },
            'benchmark_requests': benchmark_requests,
            'span_analyses': span_analyses
        }
        
        # Add statistics for benchmark requests
        if benchmark_requests:
            durations = [req['duration_ms'] for req in benchmark_requests]
            report['benchmark_statistics'] = TraceStatistics.calculate_basic_stats(durations)
            report['benchmark_percentiles'] = TraceStatistics.calculate_percentiles(durations)
            report['performance_stability'] = TraceStatistics.analyze_performance_stability(durations)
        
        # Add statistics for each span type
        report['span_statistics'] = {}
        for span_name, spans in span_analyses.items():
            if spans:
                durations = [span['duration_ms'] for span in spans]
                report['span_statistics'][span_name] = {
                    'basic_stats': TraceStatistics.calculate_basic_stats(durations),
                    'percentiles': TraceStatistics.calculate_percentiles(durations),
                    'stability': TraceStatistics.analyze_performance_stability(durations)
                }
        
        return json.dumps(report, indent=2)
    
    def _get_stability_rating(self, cv: float) -> str:
        """Get stability rating based on coefficient of variation."""
        if cv < 10:
            return "Excellent"
        elif cv < 20:
            return "Good"
        elif cv < 30:
            return "Fair"
        else:
            return "Poor"
    
    def _generate_insights(self, 
                         benchmark_requests: List[Dict[str, Any]], 
                         span_analyses: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """Generate performance insights from the data."""
        insights = []
        
        if not benchmark_requests:
            return ["No benchmark requests found for analysis"]
        
        durations = [req['duration_ms'] for req in benchmark_requests]
        
        # Performance consistency
        from trace_statistics import TraceStatistics
        cv = TraceStatistics.calculate_coefficient_of_variation(durations)
        
        if cv < 10:
            insights.append("Performance is highly consistent across iterations")
        elif cv > 30:
            insights.append("High performance variability detected - investigate potential causes")
        
        # Identify slowest operations
        slowest_spans = []
        for span_name, spans in span_analyses.items():
            if spans:
                avg_duration = sum(span['duration_ms'] for span in spans) / len(spans)
                slowest_spans.append((span_name, avg_duration))
        
        slowest_spans.sort(key=lambda x: x[1], reverse=True)
        
        if slowest_spans:
            insights.append(f"Slowest operation: {slowest_spans[0][0]} (avg: {slowest_spans[0][1]:.2f}ms)")
        
        # Performance range analysis
        if len(durations) >= 2:
            range_ratio = max(durations) / min(durations)
            if range_ratio > 2:
                insights.append(f"Significant performance variation detected ({range_ratio:.1f}x difference between fastest and slowest)")
        
        return insights
