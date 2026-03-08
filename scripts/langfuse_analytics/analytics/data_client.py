#!/usr/bin/env python3
"""
Langfuse Data Client for fetching benchmark data from Langfuse.
"""

import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

import pandas as pd
from langfuse import Langfuse

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LangfuseDataClient:
    """Client for fetching and processing Langfuse benchmark data."""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        public_key: Optional[str] = None,
        host: Optional[str] = None,
    ):
        """Initialize Langfuse client with credentials."""
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self.host = host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        self._validate_credentials()
        self.client = Langfuse(
            secret_key=self.secret_key, public_key=self.public_key, host=self.host
        )

    def _validate_credentials(self):
        """Validate that required credentials are available."""
        required_vars = ["LANGFUSE_SECRET_KEY", "LANGFUSE_PUBLIC_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            print(
                f"❌ Missing required environment variables: {', '.join(missing_vars)}"
            )
            print("Please set LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY")
            sys.exit(1)

    def fetch_benchmark_generations(
        self,
        version: str,
        expected_count: Optional[int] = None,
        max_retries: int = 5,
        initial_delay: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Fetch generations with retry logic to handle Langfuse cloud delays.

        Args:
            version: The version/tag to fetch
            expected_count: Expected number of generations (for retry logic)
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds (will increase exponentially)
        """
        logger.info(f"📊 Fetching generations for tag: {version}...")

        for attempt in range(max_retries):
            try:
                response = self.client.api.observations_v_2.get_many(
                    type="GENERATION",
                    limit=100,  # Increased limit for better efficiency
                    version=version,
                    fields="core,basic,usage,metadata",
                    expand_metadata="attributes",
                )
                observations = response.data
                count = len(observations)

                # If no expected count specified, return first successful fetch
                if expected_count is None:
                    logger.info(f"✅ Found {count} generations for version {version}")
                    return observations

                # If we have enough data, return it
                if count >= expected_count:
                    logger.info(
                        f"✅ Found all {count} generations for version {version}"
                    )
                    return observations

                # Otherwise, wait and retry with exponential backoff
                if attempt < max_retries - 1:  # Don't wait on the last attempt
                    delay = initial_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"⏳ Found {count}/{expected_count} generations. "
                        f"Retrying in {delay}s... (Attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                else:
                    logger.warning(
                        f"⚠️  Max retries reached. Proceeding with partial data ({count} generations)"
                    )
                    return observations

            except Exception as e:
                logger.error(
                    f"❌ Error fetching from Langfuse (attempt {attempt + 1}): {e}"
                )
                if attempt < max_retries - 1:
                    delay = initial_delay * (2**attempt)
                    logger.info(
                        f"Retrying in {delay}s... (Attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                else:
                    logger.error("❌ Max retries reached. Returning empty list.")
                    return []

        # This should not be reached, but just in case
        logger.error("❌ Unexpected error in fetch_benchmark_generations")
        return []

    def transform_to_dataframe(self, generations: List[Dict[str, Any]]) -> pd.DataFrame:
        """Transform Langfuse generations (as dicts) to a pandas DataFrame."""
        if not generations:
            return pd.DataFrame()

        data = []
        for gen in generations:
            try:
                # Extract usage details
                usage_details = gen.get("usageDetails", {})
                input_tokens = usage_details.get("input", 0)
                instruction_tokens = usage_details.get("instruction_tokens", 0)
                output = usage_details.get("output", 0)
                input_tokens_per_item = usage_details.get("input_tokens_per_item", 0)
                output_tokens_per_item = usage_details.get("output_tokens_per_item", 0)
                total = usage_details.get("total", 0)

                # Extract cost details
                cost_details = gen.get("costDetails", {})
                cost_input = cost_details.get("input", 0)
                cost_output = cost_details.get("output", 0)
                cost_total = cost_details.get("total", 0)

                data.append(
                    {
                        "id": gen.get("id"),
                        "trace_id": gen.get("traceId"),
                        "timestamp": gen.get("startTime"),
                        "task_name": gen.get("task_name", {}),
                        # Usage details
                        "input_tokens": input_tokens,
                        "instruction_tokens": instruction_tokens,
                        "output_tokens": output,
                        "input_tokens_per_item": input_tokens_per_item,
                        "output_tokens_per_item": output_tokens_per_item,
                        "total_tokens": total,
                        # Cost details
                        "cost_input": cost_input,
                        "cost_output": cost_output,
                        "cost_total": cost_total,
                        "version": gen.get("version", "Unknown"),
                    }
                )
            except Exception as e:
                print(f"⚠️  Error processing generation {gen.get('id', 'unknown')}: {e}")
                continue

        df = pd.DataFrame(data)
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")

        return df
