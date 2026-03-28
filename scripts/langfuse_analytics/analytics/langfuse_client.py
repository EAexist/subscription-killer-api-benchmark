#!/usr/bin/env python3
"""
Langfuse Data Client for fetching benchmark data from Langfuse.
"""

import logging
import sys
import time
from typing import Any, Dict, List, Optional

import pandas as pd
from langfuse import Langfuse

from .config import (
    DEFAULT_INITIAL_DELAY,
    DEFAULT_RETRY_COUNT,
    get_langfuse_host,
    get_langfuse_public_key,
    get_langfuse_secret_key,
)

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ModelPrice:
    """Custom class to store model pricing information."""
    
    def __init__(self, model_name: str, input_price: float, output_price: float):
        self.model_name = model_name
        self.input_price = input_price  # Price per 1k input tokens
        self.output_price = output_price  # Price per 1k output tokens
    
    def __repr__(self):
        return f"ModelPrice(model_name='{self.model_name}', input_price=${self.input_price}/1k, output_price=${self.output_price}/1k)"


class LangfuseDataClient:
    """Client for fetching and processing Langfuse benchmark data."""

    def __init__(self):
        """Initialize Langfuse client with credentials from unified config."""
        # Use lazy evaluation for config values
        self.secret_key = get_langfuse_secret_key()
        self.public_key = get_langfuse_public_key()
        self.host = get_langfuse_host()

        self._validate_credentials()
        self.client = Langfuse(
            secret_key=self.secret_key, public_key=self.public_key, host=self.host
        )
        
        # Initialize cache for model prices
        self._model_prices_cache: Dict[str, ModelPrice] = {}
        # self._fetch_model_prices()

    def _validate_credentials(self):
        """Validate that required credentials are available."""
        missing_vars = []
        if not self.secret_key:
            missing_vars.append("LANGFUSE_SECRET_KEY")
        if not self.public_key:
            missing_vars.append("LANGFUSE_PUBLIC_KEY")

        if missing_vars:
            print(
                f"❌ Missing required environment variables: {', '.join(missing_vars)}"
            )
            print("Please set LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY")
            sys.exit(1)

    
    def _fetch_model_prices(self) -> Dict[str, ModelPrice]:
        """Fetch and cache all model prices from Langfuse.
        
        Args:
            
        Returns:
            Dictionary mapping model names to ModelPrice objects
        """
        # Return cached prices if already fetched
        if self._model_prices_cache:
            logger.info(f"📋 Using cached model prices for {len(self._model_prices_cache)} models")
            return self._model_prices_cache
        
        logger.info("🔄 Fetching model prices from Langfuse...")
        
        try:
            models = self.client.api.models.list()
            
            for model in models.data:
                if hasattr(model, 'model_name') and hasattr(model, 'input_price') and hasattr(model, 'output_price'):
                    model_price = ModelPrice(
                        model_name=model.model_name,
                        input_price=float(model.input_price) if model.input_price else 0.0,
                        output_price=float(model.output_price) if model.output_price else 0.0
                    )
                    self._model_prices_cache[model.model_name] = model_price
                    logger.debug(f"💰 Cached price for {model.model_name}: ${model_price.input_price}/${model_price.output_price} per 1k tokens")
            
            logger.info(f"✅ Fetched and cached prices for {len(self._model_prices_cache)} models")
            return self._model_prices_cache
            
        except Exception as e:
            logger.error(f"❌ Error fetching model prices: {e}")
            return self._model_prices_cache  # Return whatever we have in cache

    def _fetch_traces_paginated(self, version: str) -> List[Any]:
        """Fetch traces using page-based pagination.
        
        Args:
            version: The app version to fetch traces for
            
        Returns:
            List of all traces across all pages
        """
        page_size = 100
        page = 1
        all_items = []
        
        while True:
            logger.info(f"🔄 Fetching traces page {page} with limit {page_size}")
            response = self.client.api.trace.list(limit=page_size, page=page, version=version)
            
            page_items = response.data
            all_items.extend(page_items)
            logger.info(f"📊 Retrieved {len(page_items)} traces from page {page}, total so far: {len(all_items)}")
            
            # Check if there are more pages using page-based pagination
            if hasattr(response, 'meta') and response.meta:
                # Check for total_pages and current page
                if hasattr(response.meta, 'total_pages') and hasattr(response.meta, 'page'):
                    total_pages = response.meta.total_pages
                    current_page = response.meta.page
                    logger.info(f"🔍 Traces page info: current={current_page}, total_pages={total_pages}")
                    
                    if current_page < total_pages:
                        page += 1
                        logger.info(f"📄 More trace pages available, fetching page {page}")
                        continue
                    else:
                        logger.info(f"🏁 Reached final traces page {current_page}/{total_pages}")
                        break
                else:
                    # Fallback: if no page info, assume this is the last page
                    logger.info(f"⚠️  No page info in traces meta, assuming single page")
                    break
            else:
                # Fallback: if no meta info, assume this is the last page
                logger.info(f"⚠️  No meta object in traces response, assuming single page")
                break
            
        return all_items

    def _fetch_generations_paginated(self, version: str) -> List[Any]:
        """Fetch generations using cursor-based pagination.
        
        Args:
            version: The app version to fetch generations for
            
        Returns:
            List of all generations across all pages
        """
        page_size = 100
        cursor = None
        all_items = []
        
        while True:
            if cursor:
                logger.info(f"🔄 Making generations request with cursor: {cursor}")
            else:
                logger.info(f"🔄 Making initial generations request with limit: {page_size}")

            response = self.client.api.observations_v_2.get_many(
                limit=page_size, cursor=cursor, type="GENERATION", 
                version=version, fields="core,basic,usage,metadata",
                expand_metadata="attributes"
            )
            
            page_items = response.data
            all_items.extend(page_items)
            logger.info(f"📊 Retrieved {len(page_items)} generations, total so far: {len(all_items)}")
            
            # Check if there are more pages using cursor-based pagination
            if hasattr(response, 'meta') and response.meta:
                # Check for cursor in meta (v2 API format)
                if hasattr(response.meta, 'cursor') and response.meta.cursor:
                    cursor = response.meta.cursor
                    logger.info(f"📄 Found cursor, fetching next generations page...")
                else:
                    # No cursor available, assume no more pages
                    logger.info(f"🏁 No cursor found in generations meta, pagination complete")
                    break
            else:
                # Fallback: if no meta info, assume this is the last page
                logger.info(f"⚠️  No meta object in generations response, assuming single page")
                break
            
        return all_items

    def fetch_benchmark_generations(
        self,
        app_version: str,
        expected_count: Optional[int] = None,
        max_retries: int = DEFAULT_RETRY_COUNT,
        initial_delay: int = DEFAULT_INITIAL_DELAY,
    ) -> pd.DataFrame:
        """
        Fetch generations with retry logic to handle Langfuse cloud delays.

        Args:
            app_version: The app_version/tag to fetch
            expected_count: Expected number of generations (for retry logic)
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds (will increase exponentially)
        """
        logger.info(f"📊 Fetching generations for version: {app_version}...")

        traces = []
        observations = []

        for attempt in range(max_retries):
            try:
                # Fetch traces with page-based pagination
                traces = self._fetch_traces_paginated(version=app_version)
                count = len(traces)

                # If no expected count specified, return first successful fetch
                if expected_count is None:
                    logger.info(
                        f"✅ Found {count} generations for app_version {app_version}"
                    )
                    break

                # If we have enough data, return it
                if count >= expected_count:
                    logger.info(
                        f"✅ Found all {count} generations for app_version {app_version}"
                    )
                    break

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
                    break

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
                    logger.error("❌ Max retries reached. Returning empty DataFrame.")
                    return pd.DataFrame()

        trace_to_index = {
            t.id: int(next((tag.replace("request_", "") for tag in t.tags if tag.startswith("request_")), None))
            if next((tag.replace("request_", "") for tag in t.tags if tag.startswith("request_")), None) is not None
            else None
            for t in traces
        }
                    
        # Fetch generations with cursor-based pagination
        generations = self._fetch_generations_paginated(version=app_version)

        logger.info(f"✅ Found {len(generations)} generations")

        # Transform to DataFrame
        df = self.transform_to_dataframe(generations, trace_to_index)
        logger.info(f"📋 DataFrame shape: {df.shape}")

        return df

    def transform_to_dataframe(self, generations: List[Dict[str, Any]], trace_to_index: Dict[str, Optional[int]]) -> pd.DataFrame:
        """Transform Langfuse generations (as dicts) to a pandas DataFrame."""
        if not generations:
            return pd.DataFrame()

        logger.debug(f"✅ generations[0]:\n{generations[0]}")

        data = []

        for gen in generations:
            try:
                request_index = trace_to_index.get(gen.get("traceId", ""))

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
                        "request_index": request_index,
                        "task_name": gen.get("metadata", {}).get("task_name", ""),
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
                        "app_version": gen.get("version", "Unknown"),
                    }
                )
            except Exception as e:
                print(f"⚠️  Error processing generation {gen.get('id', 'unknown')}: {e}")
                continue

        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values("request_index")

        return df
