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

from analytics.calculator import BenchmarkCalculator
from analytics.langfuse_client import LangfuseDataClient
from analytics.config import (
    CSV_NAMING_PATTERN,
    get_data_storage_root,
)
from analytics.loader import load_and_merge_csv_files, save_raw_data
from analytics.visualizer import BenchmarkVisualizer


def setup_logging(app_version: str, run_id: str, analytics_run_id: str):
    """Setup logging to both console and file with UTF-8 support."""
    data_storage_root = get_data_storage_root()
    logs_dir = Path(data_storage_root) / "logs"/ app_version

    # Create all directories in the chain
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"analytics_{run_id}_{analytics_run_id}_{timestamp}.log"
    log_filepath = os.path.join(logs_dir, log_filename)

    logger = logging.getLogger()
    logger.handlers.clear()

    # 1. Explicitly set UTF-8 for the file handler
    file_handler = logging.FileHandler(log_filepath, encoding="utf-8")

    # 2. Use sys.stdout for console and handle potential encoding issues
    stream_handler = logging.StreamHandler(sys.stdout)

    logging.basicConfig(
        level=logging.INFO,
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
        "--analytics-run-id", required=True, help="Analytics run ID to save logs"
    )
    args = parser.parse_args()

    app_version = args.app_version
    run_id = args.run_id  
    analytics_run_id = args.analytics_run_id  
    logger = setup_logging(app_version, run_id, analytics_run_id)
    logger.info(
        f"🚀 Starting Langfuse Analytics Pipeline for app_version: {app_version}, run_id: {run_id}, analytics_run_id: {analytics_run_id}"
    )

    # Initialize components
    client = LangfuseDataClient()
    visualizer = BenchmarkVisualizer()

    try:
        # 1. Fetch data from Langfuse
        logger.info("📊 Fetching data from Langfuse...")
        
        # Fetch with expected count - AI_BENCHMARK_K6_ITERATIONS is required
        expected_count = os.getenv("AI_BENCHMARK_K6_ITERATIONS")
        if not expected_count:
            logger.error("❌ AI_BENCHMARK_K6_ITERATIONS environment variable is required")
            logger.error("Please set AI_BENCHMARK_K6_ITERATIONS in your .env.test file")
            return
        
        df = client.fetch_benchmark_generations(
            app_version=app_version,
            expected_count=int(expected_count),
        )

        # 2. Save raw data as CSV
        logger.info("💾 Saving raw data...")
        csv_path = save_raw_data(df, app_version)

        # 3. Load and merge all CSV files from data directory
        logger.info("📂 Loading and merging all CSV files...")
        merged_df = load_and_merge_csv_files()

        if merged_df.empty:
            logger.error("❌ No CSV files found to merge")
            return

        logger.info(f"📋 Merged DataFrame shape: {merged_df.shape}")

        # 4. Generate convergence plot
        logger.info("📈 Generating convergence plot...")

        # Fill missing requests up to expected count first
        df_complete = BenchmarkCalculator.fill_missing_requests(
            merged_df, int(expected_count)
        )
        
        # Generate total cost plot with complete data
        df_with_cma = BenchmarkCalculator.add_convergence_metrics(
            df_complete, "cost_total"
        )

        plot_path = os.path.join(visualizer.output_dir, "amortized_ai_cost.png")
        visualizer.plot_cost_convergence(
            df_with_cma,
            plot_path,
            "Amortized AI Operational Cost per Request",
            "Amortized Cost",
        )
        logger.info(f"✅ Amortized cost plot saved to: {plot_path}")

        # Generate task-specific plots if task_name column exists
        if "task_name" in df_complete.columns:
            for task_name in df_complete["task_name"].unique():
                task_df = df_complete[df_complete["task_name"] == task_name]
                if not task_df.empty:
                    # Total Cost
                    task_cma = BenchmarkCalculator.add_convergence_metrics(
                        task_df, "cost_total"
                    )
                    task_plot_path = os.path.join(
                        visualizer.output_dir,
                        f"amortized_ai_cost_{task_name}.png",
                    )
                    visualizer.plot_cost_convergence(
                        task_cma,
                        task_plot_path,
                        f"AI Cost per Request\n({task_name})",
                        "Amortized Cost",
                    )
                    logger.info(f"✅ Task-specific plot saved to: {task_plot_path}")

        # Generate summary
        logger.info("\n📊 Summary:")
        logger.info(f"- Raw data: {csv_path}")
        logger.info(f"- Total records: {len(merged_df)}")

        if "task_name" in merged_df.columns:
            logger.info(f"- Task names: {merged_df['task_name'].unique()}")

        if "cost_total" in merged_df.columns:
            logger.info(f"- Total cost: ${merged_df['cost_total'].sum():.6f}")
            logger.info(
                f"- Average cost per request: ${merged_df['cost_total'].mean():.6f}"
            )

        logger.info("\n🎉 Analytics pipeline completed successfully!")

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
