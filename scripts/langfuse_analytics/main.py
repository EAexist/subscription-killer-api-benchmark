#!/usr/bin/env python3
"""
Main entry point for Langfuse analytics pipeline.
Fetches data, processes it, and generates visualizations.
"""

import os
import sys

from analytics.calculator import BenchmarkCalculator
from analytics.data_client import LangfuseDataClient
from analytics.loader import load_and_merge_csv_files, save_raw_data
from analytics.visualizer import BenchmarkVisualizer


def main():
    """Main analytics pipeline."""
    print("🚀 Starting Langfuse Analytics Pipeline")

    # Initialize components
    client = LangfuseDataClient()
    visualizer = BenchmarkVisualizer()

    try:
        # 1. Fetch data from Langfuse
        print("📊 Fetching data from Langfuse...")
        # Fetch without expected count for now (can be added later if needed)
        generations = client.fetch_benchmark_generations("benchmark")

        if not generations:
            print("❌ No data found in Langfuse")
            return

        print(f"✅ Found {len(generations)} generations")

        # Transform to DataFrame
        df = client.transform_to_dataframe(generations)
        print(f"📋 DataFrame shape: {df.shape}")

        # 2. Save raw data as CSV
        print("💾 Saving raw data...")
        csv_path = save_raw_data(df, "benchmark")

        # 3. Load and merge all CSV files from data directory
        print("📂 Loading and merging all CSV files...")
        merged_df = load_and_merge_csv_files()

        if merged_df.empty:
            print("❌ No CSV files found to merge")
            return

        print(f"📋 Merged DataFrame shape: {merged_df.shape}")

        # 4. Generate convergence plot
        print("📈 Generating convergence plot...")

        # Add convergence metrics - use 'cost_total' column as that's what's available
        df_with_cma = BenchmarkCalculator.add_convergence_metrics(
            merged_df, "cost_total"
        )

        # Generate plot with descriptive name
        plot_path = os.path.join(visualizer.output_dir, "cost_convergence_results.png")
        visualizer.plot_cost_convergence(df_with_cma, plot_path)
        print(f"✅ Convergence plot saved to: {plot_path}")

        # Generate task-specific plots if task_name column exists
        if "task_name" in merged_df.columns:
            for task_name in merged_df["task_name"].unique():
                task_df = merged_df[merged_df["task_name"] == task_name]
                if not task_df.empty:
                    task_cma = BenchmarkCalculator.add_convergence_metrics(
                        task_df, "cost_total"
                    )
                    task_plot_path = os.path.join(
                        visualizer.output_dir, f"cost_convergence_{task_name}.png"
                    )
                    visualizer.plot_cost_convergence(task_cma, task_plot_path)
                    print(f"✅ Task-specific plot saved to: {task_plot_path}")

        # Generate summary
        print("\n📊 Summary:")
        print(f"- Raw data: {csv_path}")
        print(f"- Total records: {len(merged_df)}")

        if "task_name" in merged_df.columns:
            print(f"- Task names: {merged_df['task_name'].unique()}")

        if "cost_total" in merged_df.columns:
            print(f"- Total cost: ${merged_df['cost_total'].sum():.6f}")
            print(f"- Average cost per request: ${merged_df['cost_total'].mean():.6f}")

        print("\n🎉 Analytics pipeline completed successfully!")

    except Exception as e:
        print(f"❌ Error in analytics pipeline: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
