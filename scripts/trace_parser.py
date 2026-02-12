#!/usr/bin/env python3
"""
Trace Parser Module
Handles parsing and extraction of data from Zipkin trace files.
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path


class TraceParser:
    """Handles parsing of Zipkin trace data."""
    
    def __init__(self, trace_file_path: str, warmup_iterations: int = 0):
        """Initialize trace parser with file path and warmup iterations."""
        self.trace_file_path = trace_file_path
        self.warmup_iterations = warmup_iterations
        self.traces = []
        self._load_traces()
        self._exclude_warmup_iterations()

    def _load_traces_direct(self) -> List[List[Dict[str, Any]]]:
        """Load traces from JSON file without warmup exclusion."""
        try:
            with open(self.trace_file_path, 'r', encoding='utf-8-sig') as f:
                wrapper_data = json.load(f)
            return json.loads(wrapper_data.get('rawData', '[]'))
        except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
            raise ValueError(f"Failed to load traces from {self.trace_file_path}: {e}")

    def _load_traces(self) -> None:
        """Load traces from the JSON file."""
        self.traces = self._load_traces_direct()

    def _is_benchmark_trace(self, trace: List[Dict[str, Any]]) -> bool:
        """Check if trace contains benchmark HTTP request."""
        return any(
            'name' in span and
            'http' in span['name'].lower() and
            'benchmark/analyze' in span['name'].lower()
            for span in trace
        )

    def _exclude_warmup_iterations(self) -> None:
        """Exclude warmup iterations from traces based on warmup_iterations parameter."""
        warmup_iterations = self.warmup_iterations

        if warmup_iterations <= 0:
            return

        # Find benchmark traces
        benchmark_traces = [trace for trace in self.traces if self._is_benchmark_trace(trace)]

        if len(benchmark_traces) <= warmup_iterations:
            print(f"Warning: Only {len(benchmark_traces)} iterations found, but {warmup_iterations} warmup iterations to exclude")
            return

        # Sort by timestamp and exclude first N traces
        benchmark_traces.sort(key=lambda trace: min(span.get('timestamp', float('inf')) for span in trace))
        warmup_trace_ids = {
            trace[0].get('traceId', '')
            for trace in benchmark_traces[:warmup_iterations]
        }

        # Filter out warmup traces
        original_count = len(self.traces)
        self.traces = [
            trace for trace in self.traces
            if not (trace and trace[0].get('traceId', '') in warmup_trace_ids)
        ]

        excluded_count = original_count - len(self.traces)
        print(f"Excluded {excluded_count} warmup traces ({warmup_iterations} iterations)")

    def _create_span_dict(self, span: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized span dictionary with common fields."""
        return {
            'trace_id': span['traceId'],
            'span_name': span['name'],
            'duration_ms': span['duration'] / 1000,
            'timestamp': span.get('timestamp', 0) / 1000,
            'span_id': span.get('id', ''),
            'parent_id': span.get('parentId', 'ROOT'),
            'tags': span.get('tags', {})
        }

    def _filter_spans_by_pattern(self, pattern: str, startswith: bool = True) -> List[Dict[str, Any]]:
        """Filter spans by name pattern across all traces."""
        matching_spans = []

        for trace in self.traces:
            for span in trace:
                if ('name' in span and 'duration' in span):
                    name_lower = span['name'].lower()
                    pattern_lower = pattern.lower()

                    if (startswith and name_lower.startswith(pattern_lower)) or \
                       (not startswith and pattern_lower in name_lower):
                        matching_spans.append(self._create_span_dict(span))

        return matching_spans

    def get_spans_by_name(self, span_name: str) -> List[Dict[str, Any]]:
        """Get all spans matching a specific name pattern."""
        return self._filter_spans_by_pattern(span_name, startswith=False)

    def get_benchmark_requests(self) -> List[Dict[str, Any]]:
        """Extract only benchmark analyze endpoint requests."""
        return self._filter_spans_by_pattern('benchmark/analyze', startswith=False)

    def _get_critical_spans(self, patterns: List[str]) -> List[Dict[str, Any]]:
        """Get critical spans by multiple patterns."""
        critical_spans = []

        for trace in self.traces:
            for span in trace:
                if ('name' in span and 'duration' in span):
                    name_lower = span['name'].lower()
                    if any(name_lower.startswith(pattern) for pattern in patterns):
                        critical_spans.append(self._create_span_dict(span))

        return critical_spans

    def _aggregate_critical_spans(self, critical_spans: List[Dict[str, Any]],
                                 trace: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform hierarchical aggregation of critical spans."""
        if not critical_spans:
            return []

        span_lookup = {span['id']: span for span in trace}
        current_level_spans = []

        # Initialize with spans that have critical children or are critical themselves
        for span in trace:
            span_id = span.get('id', '')
            children_duration = self._get_children_critical_duration(span_id, critical_spans, span_lookup)
            span_duration = self._get_span_duration(span_id, critical_spans)

            if span_id in [s['span_id'] for s in critical_spans] or children_duration > 0:
                current_level_spans.append({
                    'span_id': span_id,
                    'parent_id': span.get('parentId', 'ROOT'),
                    'name': span['name'],
                    'duration_ms': span_duration if span_duration > 0 else children_duration,
                    'timestamp': span.get('timestamp', 0) / 1000,
                    'trace_id': span['traceId']
                })

        # Hierarchical aggregation
        for _ in range(10):  # Max iterations
            parent_groups = {}
            root_level_spans = []

            for span in current_level_spans:
                parent_id = span['parent_id']
                if parent_id == 'ROOT' or parent_id not in span_lookup:
                    root_level_spans.append(span)
                else:
                    parent_groups.setdefault(parent_id, []).append(span)

            if not parent_groups:
                break

            aggregated_spans = []
            for parent_id, group_spans in parent_groups.items():
                if len(group_spans) == 1:
                    aggregated_spans.extend(group_spans)
                else:
                    if self._check_concurrency(group_spans):
                        aggregated_spans.append(max(group_spans, key=lambda x: x['duration_ms']))
                    else:
                        aggregated_span = self._create_aggregated_span(
                            parent_id, group_spans, critical_spans, span_lookup)
                        if aggregated_span:
                            aggregated_spans.append(aggregated_span)

            aggregated_spans.extend(root_level_spans)
            if len(aggregated_spans) >= len(current_level_spans):
                break

            current_level_spans = aggregated_spans

        return current_level_spans

    def _check_concurrency(self, spans: List[Dict[str, Any]]) -> bool:
        """Check if spans are concurrent using timestamps."""
        if len(spans) <= 1:
            return False

        sorted_spans = sorted(spans, key=lambda x: x['timestamp'])

        for i in range(len(sorted_spans) - 1):
            current_end = sorted_spans[i]['timestamp'] + sorted_spans[i]['duration_ms']
            next_start = sorted_spans[i + 1]['timestamp']
            if next_start < current_end:
                return True

        return False

    def _get_span_duration(self, span_id: str, critical_spans: List[Dict[str, Any]]) -> float:
        """Get duration for a span if it's in critical spans, otherwise 0."""
        for critical_span in critical_spans:
            if critical_span['span_id'] == span_id:
                return critical_span['duration_ms']
        return 0

    def _get_children_critical_duration(self, parent_id: str, critical_spans: List[Dict[str, Any]],
                                     span_lookup: Dict[str, Any]) -> float:
        """Get total duration of critical spans under a parent."""
        return sum(
            self._get_span_duration(span_id, critical_spans)
            for span_id, span in span_lookup.items()
            if span.get('parentId') == parent_id and
               span_id in [s['span_id'] for s in critical_spans]
        )

    def _create_aggregated_span(self, parent_id: str, children_spans: List[Dict[str, Any]],
                              critical_spans: List[Dict[str, Any]],
                              span_lookup: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create an aggregated span representing critical children."""
        total_duration = sum(span['duration_ms'] for span in children_spans)
        min_timestamp = min(span['timestamp'] for span in children_spans)

        parent_span = span_lookup.get(parent_id)
        base_name = parent_span.get('name', parent_id) if parent_span else parent_id

        return {
            'span_id': f"aggregated_critical_{parent_id}",
            'parent_id': parent_span.get('parentId', 'ROOT') if parent_span else 'ROOT',
            'name': f"aggregated_critical_{base_name}",
            'duration_ms': total_duration,
            'timestamp': min_timestamp,
            'trace_id': children_spans[0]['trace_id']
        }

    def _calculate_final_critical_io(self, final_spans: List[Dict[str, Any]]) -> float:
        """Calculate final critical I/O from root-level spans."""
        if len(final_spans) == 1:
            return final_spans[0]['duration_ms']

        if self._check_concurrency(final_spans):
            return max(span['duration_ms'] for span in final_spans)
        else:
            return sum(span['duration_ms'] for span in final_spans)

    def _calculate_critical_io_for_pattern(self, pattern: str) -> List[Dict[str, Any]]:
        """Calculate critical I/O for a specific pattern (e.g., 'gmail', 'chat')."""
        critical_io_values = []

        for trace in self.traces:
            # Find spans matching pattern
            pattern_spans = self._filter_spans_by_pattern(pattern, startswith=True)

            if not pattern_spans:
                critical_io_values.append({
                    'trace_id': trace[0].get('traceId', '') if trace else '',
                    'critical_io_ms': 0,
                    'spans_count': 0,
                    'execution_pattern': f'no_{pattern}_spans'
                })
                continue

            final_spans = self._aggregate_critical_spans(pattern_spans, trace)
            critical_io = self._calculate_final_critical_io(final_spans)

            critical_io_values.append({
                'trace_id': trace[0].get('traceId', '') if trace else '',
                'critical_io_ms': critical_io,
                'spans_count': len(pattern_spans),
                'execution_pattern': 'root_aggregation' if len(final_spans) > 1 else 'single_span',
                'final_spans_count': len(final_spans)
            })

        return critical_io_values

    def get_gmail_api_critical_io(self) -> List[Dict[str, Any]]:
        """Calculate Gmail API Critical I/O using Union of Intervals method."""
        return self._get_critical_io_union_intervals(['gmail'])

    def get_ai_api_critical_io(self) -> List[Dict[str, Any]]:
        """Calculate AI API Critical I/O using Union of Intervals method."""
        return self._get_critical_io_union_intervals(['chat'])

    def get_total_critical_io(self) -> List[Dict[str, Any]]:
        """Calculate Total Critical I/O using Union of Intervals method."""
        return self._get_critical_io_union_intervals(['gmail', 'chat'])

    def _get_critical_io_union_intervals(self, patterns) -> List[Dict[str, Any]]:
        """Calculate critical I/O using Union of Intervals method."""
        critical_io_values = []
        
        # Normalize patterns to list
        if isinstance(patterns, str):
            patterns = [patterns]
        
        for trace in self.traces:
            if not trace:
                critical_io_values.append({
                    'trace_id': '',
                    'critical_io_ms': 0,
                    'spans_count': 0,
                    'execution_pattern': 'no_trace'
                })
                continue

            # Identify all I/O spans
            io_spans = [
                span for span in trace 
                if any(span.get('name', '').lower().startswith(pattern) for pattern in patterns)
            ]
            
            if not io_spans:
                critical_io_values.append({
                    'trace_id': trace[0].get('traceId', ''),
                    'critical_io_ms': 0,
                    'spans_count': 0,
                    'execution_pattern': 'no_io_spans'
                })
                continue

            # Convert spans to intervals
            intervals = []
            for span in io_spans:
                start_time = span.get('timestamp', 0) / 1000  # Convert to ms
                duration = span.get('duration', 0) / 1000  # Convert to ms
                end_time = start_time + duration
                
                intervals.append({
                    'start': start_time,
                    'end': end_time,
                    'duration': duration,
                    'span_id': span['id'],
                    'span_name': span.get('name', 'N/A')
                })
            
            # Sort intervals by start time
            intervals.sort(key=lambda x: x['start'])
            
            # Merge overlapping intervals
            merged_intervals = self._merge_intervals(intervals)
            
            # Sum durations of merged intervals (total elapsed time where at least one I/O was active)
            total_critical_io = sum(interval['duration'] for interval in merged_intervals)

            critical_io_values.append({
                'trace_id': trace[0].get('traceId', ''),
                'critical_io_ms': total_critical_io,
                'spans_count': len(io_spans),
                'execution_pattern': 'union_intervals'
            })

        return critical_io_values

    def _merge_intervals(self, intervals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge overlapping intervals into unique continuous blocks."""
        if not intervals:
            return []
        
        merged = []
        current_interval = intervals[0].copy()
        
        for i in range(1, len(intervals)):
            next_interval = intervals[i]
            
            if next_interval['start'] <= current_interval['end']:
                # Overlapping - merge them
                current_interval['end'] = max(current_interval['end'], next_interval['end'])
                current_interval['duration'] = current_interval['end'] - current_interval['start']
                # Keep span info for debugging
                if 'merged_spans' not in current_interval:
                    current_interval['merged_spans'] = [current_interval['span_id']]
                current_interval['merged_spans'].append(next_interval['span_id'])
            else:
                # No overlap - add current and start new
                merged.append(current_interval)
                current_interval = next_interval.copy()
        
        # Add the last interval
        merged.append(current_interval)
        
        return merged

    def _get_unified_critical_io(self) -> List[Dict[str, Any]]:
        """Calculate critical I/O treating all Gmail and Chat spans as unified I/O operations."""
        critical_io_values = []

        for trace in self.traces:
            if not trace:
                critical_io_values.append({
                    'trace_id': '',
                    'critical_io_ms': 0,
                    'spans_count': 0,
                    'execution_pattern': 'no_trace'
                })
                continue

            # Count ALL I/O spans (Gmail + Chat)
            io_spans = [
                span for span in trace 
                if span.get('name', '').lower().startswith(('gmail', 'chat'))
            ]
            
            if not io_spans:
                critical_io_values.append({
                    'trace_id': trace[0].get('traceId', ''),
                    'critical_io_ms': 0,
                    'spans_count': 0,
                    'execution_pattern': 'no_io_spans'
                })
                continue

            # Use unified recursive algorithm that treats all I/O spans equally
            critical_io = self._calculate_unified_critical_io_recursive(trace)

            critical_io_values.append({
                'trace_id': trace[0].get('traceId', ''),
                'critical_io_ms': critical_io,
                'spans_count': len(io_spans),
                'execution_pattern': 'unified_recursive_hierarchical'
            })

        return critical_io_values

    def _calculate_unified_critical_io_recursive(self, trace: List[Dict[str, Any]]) -> float:
        """Calculate critical I/O using recursive hierarchical aggregation treating all I/O spans equally."""
        # Build span hierarchy with ALL spans
        span_lookup = {span['id']: span for span in trace}
        root_spans = [span for span in trace if span.get('parentId') is None]
        
        if not root_spans:
            return 0
        
        # Recursive aggregation for each root span
        root_values = []
        for root_span in root_spans:
            value = self._aggregate_unified_span_recursive(root_span, span_lookup)
            root_values.append(value)
        
        # Final aggregation at root level
        if len(root_values) == 1:
            return root_values[0]
        
        # Check if root spans are concurrent
        root_span_dicts = []
        for root_span in root_spans:
            root_span_dicts.append({
                'timestamp': root_span.get('timestamp', 0) / 1000,
                'duration_ms': root_span.get('duration', 0) / 1000
            })
        
        if self._check_concurrency(root_span_dicts):
            return max(root_values)
        else:
            return sum(root_values)

    def _aggregate_unified_span_recursive(self, span: Dict[str, Any], 
                                         span_lookup: Dict[str, Dict[str, Any]]) -> float:
        """Recursively aggregate span value treating all I/O spans (gmail/chat) equally."""
        span_id = span['id']
        span_name = span.get('name', '').lower()
        
        # Find ALL children (not just critical ones) - SAME AS YOUR ORIGINAL
        children = [s for s in span_lookup.values() if s.get('parentId') == span_id]
        
        # Recursively get values from ALL children - SAME AS YOUR ORIGINAL
        child_values = []
        for child in children:
            child_value = self._aggregate_unified_span_recursive(child, span_lookup)
            child_values.append(child_value)
        
        # Determine this span's value - UNIFIED I/O approach
        if span_name.startswith('gmail') or span_name.startswith('chat'):
            # This is an I/O span - use its duration
            span_value = span.get('duration', 0) / 1000  # Convert to ms
        else:
            # This is not an I/O span - value comes from children only
            span_value = 0
        
        # Aggregate children values with this span's value - SAME AS YOUR ORIGINAL
        all_values = [span_value] + child_values
        
        if len(all_values) == 1:
            return all_values[0]
        
        # Check concurrency among children with I/O values only - SAME LOGIC AS YOUR ORIGINAL
        io_children = []
        for i, child in enumerate(children):
            if child_values[i] > 0:  # Only consider children that contribute to I/O
                io_children.append(child)
        
        if len(io_children) <= 1:
            # No I/O children or single I/O child - just add to span value
            return sum(all_values)
        
        # Create child span dictionaries for concurrency check using only I/O children
        child_span_dicts = []
        for child in io_children:
            child_span_dicts.append({
                'timestamp': child.get('timestamp', 0) / 1000,
                'duration_ms': child.get('duration', 0) / 1000
            })
        
        # Check concurrency among I/O children only - SAME AS YOUR ORIGINAL
        if self._check_concurrency(child_span_dicts):
            # I/O children are concurrent - take max of I/O children values, then add span value
            io_values = [child_values[i] for i, child in enumerate(children) if child_values[i] > 0]
            children_aggregated = max(io_values) if io_values else 0
        else:
            # I/O children are sequential - sum I/O children values, then add span value
            io_values = [child_values[i] for i, child in enumerate(children) if child_values[i] > 0]
            children_aggregated = sum(io_values)
        
        return span_value + children_aggregated

    def _collect_io_spans_in_subtree(self, span: Dict[str, Any], 
                                    span_lookup: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Collect all I/O spans (gmail/chat) in the subtree under this span."""
        io_spans = []
        span_name = span.get('name', '').lower()
        
        # Check if this span is an I/O span
        if span_name.startswith('gmail') or span_name.startswith('chat'):
            io_spans.append(span)
        
        # Recursively check children
        children = [s for s in span_lookup.values() if s.get('parentId') == span['id']]
        for child in children:
            io_spans.extend(self._collect_io_spans_in_subtree(child, span_lookup))
        
        return io_spans

    def _get_critical_io_by_pattern(self, patterns) -> List[Dict[str, Any]]:
        """Generic method to calculate critical I/O for given patterns using recursive hierarchical aggregation."""
        critical_io_values = []
        
        # Normalize patterns to list
        if isinstance(patterns, str):
            patterns = [patterns]
            pattern_name = patterns[0]
        else:
            pattern_name = 'total'

        for trace in self.traces:
            if not trace:
                critical_io_values.append({
                    'trace_id': '',
                    'critical_io_ms': 0,
                    'spans_count': 0,
                    'execution_pattern': 'no_trace'
                })
                continue

            # Count critical spans matching patterns
            critical_spans = [
                span for span in trace 
                if any(span.get('name', '').lower().startswith(pattern) for pattern in patterns)
            ]
            
            if not critical_spans:
                pattern_key = f'no_{pattern_name}_spans' if len(patterns) == 1 else 'no_critical_spans'
                critical_io_values.append({
                    'trace_id': trace[0].get('traceId', ''),
                    'critical_io_ms': 0,
                    'spans_count': 0,
                    'execution_pattern': pattern_key
                })
                continue

            # Use recursive algorithm
            critical_io = self._calculate_final_critical_io_recursive(trace, patterns)

            critical_io_values.append({
                'trace_id': trace[0].get('traceId', ''),
                'critical_io_ms': critical_io,
                'spans_count': len(critical_spans),
                'execution_pattern': 'recursive_hierarchical'
            })

        return critical_io_values

    def _calculate_final_critical_io_recursive(self, trace: List[Dict[str, Any]], 
                                           critical_patterns: List[str]) -> float:
        """Calculate critical I/O using recursive hierarchical aggregation on complete span tree."""
        # Build span hierarchy with ALL spans (not just critical ones)
        span_lookup = {span['id']: span for span in trace}
        root_spans = [span for span in trace if span.get('parentId') is None]
        
        if not root_spans:
            return 0
        
        # Recursive aggregation for each root span
        root_values = []
        for root_span in root_spans:
            value = self._aggregate_span_recursive(root_span, span_lookup, critical_patterns)
            root_values.append(value)
        
        # Final aggregation at root level
        if len(root_values) == 1:
            return root_values[0]
        
        # Check if root spans are concurrent
        root_span_dicts = []
        for root_span in root_spans:
            root_span_dicts.append({
                'timestamp': root_span.get('timestamp', 0) / 1000,
                'duration_ms': root_span.get('duration', 0) / 1000
            })
        
        if self._check_concurrency(root_span_dicts):
            return max(root_values)
        else:
            return sum(root_values)

    def _aggregate_span_recursive(self, span: Dict[str, Any], 
                                 span_lookup: Dict[str, Dict[str, Any]], 
                                 critical_patterns: List[str]) -> float:
        """Recursively aggregate span value from children up using complete hierarchy."""
        span_id = span['id']
        span_name = span.get('name', '').lower()
        
        # Find ALL children (not just critical ones)
        children = [s for s in span_lookup.values() if s.get('parentId') == span_id]
        
        # Recursively get values from ALL children
        child_values = []
        for child in children:
            child_value = self._aggregate_span_recursive(child, span_lookup, critical_patterns)
            child_values.append(child_value)
        
        # Determine this span's value
        if any(span_name.startswith(pattern) for pattern in critical_patterns):
            # This is a critical span - use its duration
            span_value = span.get('duration', 0) / 1000  # Convert to ms
        else:
            # This is not a critical span - value comes from children only
            span_value = 0
        
        # Aggregate children values with this span's value
        all_values = [span_value] + child_values
        
        if len(all_values) == 1:
            return all_values[0]
        
        # Check concurrency among children - only consider children that have critical values
        critical_children = []
        for i, child in enumerate(children):
            if child_values[i] > 0:  # Only consider children that contribute to critical I/O
                critical_children.append(child)
        
        if len(critical_children) <= 1:
            # No critical children or single critical child - just add to span value
            return sum(all_values)
        
        # Create child span dictionaries for concurrency check using only critical children
        child_span_dicts = []
        for child in critical_children:
            child_span_dicts.append({
                'timestamp': child.get('timestamp', 0) / 1000,
                'duration_ms': child.get('duration', 0) / 1000
            })
        
        # Check concurrency among critical children only
        if self._check_concurrency(child_span_dicts):
            # Critical children are concurrent - take max of critical children values, then add span value
            critical_values = [child_values[i] for i, child in enumerate(children) if child_values[i] > 0]
            children_aggregated = max(critical_values) if critical_values else 0
        else:
            # Critical children are sequential - sum critical children values, then add span value
            critical_values = [child_values[i] for i, child in enumerate(children) if child_values[i] > 0]
            children_aggregated = sum(critical_values)
        
        return span_value + children_aggregated

    
    def get_ai_token_usage(self) -> List[Dict[str, Any]]:
        """Calculate AI token usage per iteration (trace)."""
        token_usage_values = []

        for trace in self.traces:
            # Only consider traces that have benchmark HTTP requests
            if not self._is_benchmark_trace(trace):
                continue

            trace_id = trace[0].get('traceId', '') if trace else ''
            total_tokens = 0
            input_tokens = 0
            output_tokens = 0

            for span in trace:
                if ('name' in span and 'tags' in span and
                    span['name'].lower().startswith('chat')):

                    # Extract total tokens
                    if 'gen_ai.usage.total_tokens' in span['tags']:
                        try:
                            token_count = int(span['tags']['gen_ai.usage.total_tokens'])
                            total_tokens += token_count
                        except (ValueError, TypeError):
                            continue

                    # Extract input tokens
                    if 'gen_ai.usage.input_tokens' in span['tags']:
                        try:
                            input_token_count = int(span['tags']['gen_ai.usage.input_tokens'])
                            input_tokens += input_token_count
                        except (ValueError, TypeError):
                            continue

                    # Extract output tokens
                    if 'gen_ai.usage.output_tokens' in span['tags']:
                        try:
                            output_token_count = int(span['tags']['gen_ai.usage.output_tokens'])
                            output_tokens += output_token_count
                        except (ValueError, TypeError):
                            continue

            token_usage_values.append({
                'trace_id': trace_id,
                'total_tokens': total_tokens,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'ai_spans_with_tokens': len([
                    s for s in trace
                    if 'name' in s and 'tags' in s and
                       s['name'].lower().startswith('chat') and
                       'gen_ai.usage.total_tokens' in s.get('tags', {})
                ])
            })

        return token_usage_values

    def get_all_traces(self) -> List[List[Dict[str, Any]]]:
        """Get all traces."""
        return self.traces
