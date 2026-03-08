#!/usr/bin/env python3
"""
Constants and schemas for Langfuse analytics.
"""

from enum import Enum
from typing import FrozenSet


class ExpectedColumns(Enum):
    """Expected column names for Langfuse benchmark data."""

    # Core identifiers
    ID = "id"
    TRACE_ID = "trace_id"
    TIMESTAMP = "timestamp"
    TASK_NAME = "task_name"
    VERSION = "version"

    # Usage details
    INPUT_TOKENS = "input_tokens"
    INSTRUCTION_TOKENS = "instruction_tokens"
    OUTPUT_TOKENS = "output_tokens"
    INPUT_TOKENS_PER_ITEM = "input_tokens_per_item"
    OUTPUT_TOKENS_PER_ITEM = "output_tokens_per_item"
    TOTAL_TOKENS = "total_tokens"

    # Cost details
    COST_INPUT = "cost_input"
    COST_OUTPUT = "cost_output"
    COST_TOTAL = "cost_total"


# Ground truth column list based on transform_to_dataframe method
EXPECTED_COLUMNS: FrozenSet[str] = frozenset(
    [
        ExpectedColumns.ID.value,
        ExpectedColumns.TRACE_ID.value,
        ExpectedColumns.TIMESTAMP.value,
        ExpectedColumns.TASK_NAME.value,
        ExpectedColumns.VERSION.value,
        ExpectedColumns.INPUT_TOKENS.value,
        ExpectedColumns.INSTRUCTION_TOKENS.value,
        ExpectedColumns.OUTPUT_TOKENS.value,
        ExpectedColumns.INPUT_TOKENS_PER_ITEM.value,
        ExpectedColumns.OUTPUT_TOKENS_PER_ITEM.value,
        ExpectedColumns.TOTAL_TOKENS.value,
        ExpectedColumns.COST_INPUT.value,
        ExpectedColumns.COST_OUTPUT.value,
        ExpectedColumns.COST_TOTAL.value,
    ]
)

# Required columns for minimum validation (must have these)
REQUIRED_COLUMNS: FrozenSet[str] = frozenset(
    [
        ExpectedColumns.ID.value,
        ExpectedColumns.TIMESTAMP.value,
        ExpectedColumns.VERSION.value,
    ]
)

# Optional columns that can be missing
OPTIONAL_COLUMNS: FrozenSet[str] = frozenset(
    [
        ExpectedColumns.TASK_NAME.value,
        ExpectedColumns.TRACE_ID.value,
    ]
)
