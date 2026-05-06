#!/usr/bin/env python3
"""
Main entry point for Langfuse analytics pipeline.
Fetches data, processes it, and generates visualizations.
"""

import argparse
import logging
import os
from pathlib import Path
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from langfuse_client import LangfuseDataClient
from config import get_data_storage_root
from loader import save_raw_data

def setup_logging(app_version: str, run_id: str):
    """Setup logging to both console and file with UTF-8 support."""
    data_storage_root = get_data_storage_root()
    logs_dir = Path(data_storage_root) / "logs" / app_version / run_id

    # Create all directories in the chain
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"langfuse_loader_{timestamp}.log"
    log_filepath = os.path.join(logs_dir, log_filename)

    logger = logging.getLogger()
    logger.handlers.clear()

    # 1. Explicitly set UTF-8 for the file handler
    file_handler = logging.FileHandler(log_filepath, encoding="utf-8")

    # 2. Use sys.stdout for console and handle potential encoding issues
    stream_handler = logging.StreamHandler(sys.stdout)

    # Set log level based on environment variable
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[file_handler, stream_handler],
        force=True,
    )

    # 3. Test write using UTF-8 to ensure emojis like ✅ work
    with open(log_filepath, "a", encoding="utf-8") as f:
        f.write(f"Log started at {datetime.now()} 🚀\n")

    logger = logging.getLogger(__name__)
    logger.info(f"Logging to file: {log_filepath}")

    return logger


def main():
    """Main analytics pipeline."""
    parser = argparse.ArgumentParser(description="Langfuse Analytics Pipeline")
    parser.add_argument(
        "--app-version", required=True, help="App version/tag to fetch from Langfuse"
    )
    parser.add_argument(
        "--run-id", required=True, help="Run ID to save logs"
    )
    parser.add_argument(
        "--expected-request-count", required=True, help="Expected request count"
    )
    args = parser.parse_args()

    app_version = args.app_version
    run_id = args.run_id    
    expected_request_count = int(args.expected_request_count)
    logger = setup_logging(app_version, run_id)
    logger.info(
        f"🚀 Starting Langfuse Analytics Pipeline for app_version: {app_version}, run_id: {run_id}"
    )

    # Initialize components
    client = LangfuseDataClient()

    try:
        # 1. Fetch data from Langfuse
        logger.info("📊 Fetching data from Langfuse...")
        
        df = client.fetch_benchmark_generations(
            run_id=run_id,
            expected_request_count=expected_request_count,
        )

        logger.info("💾 Saving raw data...")
        save_raw_data(df, app_version)

        logger.info("\n🎉 Langfuse data loaded successfully!")

        # Flush all logging handlers to ensure logs are written
        for handler in logging.getLogger().handlers:
            handler.flush()

    except Exception as e:
        logger.error(f"❌ Error in analytics pipeline: {e}")
        # Flush all logging handlers even on error
        for handler in logging.getLogger().handlers:
            handler.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
