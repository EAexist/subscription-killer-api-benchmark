#!/usr/bin/env python3
"""
Benchmark Visualizer for generating plots and reports from Langfuse data.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd

from .config import PLOTS_DIR


class BenchmarkVisualizer:
    """Visualizer for creating plots and reports from benchmark data."""

    def __init__(self, output_dir: str = None):
        """Initialize visualizer with output directory."""
        if output_dir is None:
            # Use the centralized config for plots directory
            output_dir = PLOTS_DIR

        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Set up matplotlib for better plots
        plt.style.use("default")
        plt.rcParams["figure.figsize"] = (12, 8)

    def plot_cost_convergence(
        self, df_subset: pd.DataFrame, output_path: str, show_plot: bool = False
    ) -> None:
        """
        Plot cost convergence data.

        Expects a DataFrame with: ['request_index', 'amortized_cost', 'version']

        Args:
            df_subset: DataFrame with trace data
            output_path: Path to save the plot
            show_plot: If True, display the plot interactively
        """
        plt.figure(figsize=(12, 8))

        # Simple Plotting Logic
        for impl in df_subset["app_version"].unique():
            data = df_subset[df_subset["app_version"] == impl]
            # Convert cost to $ per thousand requests
            cost_per_thousand = data["amortized_cost"] * 1_000
            plt.plot(
                data["request_index"],
                cost_per_thousand,
                label=impl,
                linewidth=2.5,
                marker="o",
                markersize=3,
                alpha=0.8,
            )

        plt.title(
            "Amortized AI Operational Cost per Request", fontsize=16, fontweight="bold"
        )
        plt.xlabel("Request", fontsize=12)
        plt.ylabel(
            "Amortized AI Cost per Request ($ per thousand requests)", fontsize=12
        )
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)

        # Set x-axis range to start from zero and ticks every 5 units
        max_request_index = df_subset["request_index"].max()
        plt.xlim(0, max_request_index)
        tick_positions = range(0, int(max_request_index) + 1, 5)
        plt.xticks(tick_positions)

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")

        if show_plot:
            plt.show()
        else:
            plt.close()


#     def generate_markdown_table(
#         self, df: pd.DataFrame, output_file: Optional[str] = None
#     ) -> str:
#         """Generate and save a markdown table from DataFrame."""
#         if df.empty:
#             print("⚠️  No data to generate markdown table")
#             return ""

#         if output_file is None:
#             output_file = os.path.join(self.output_dir, "benchmark_results.md")

#         try:
#             # Select relevant columns for display
#             display_columns = [
#                 "timestamp",
#                 "traceIdname",
#                 "model",
#                 "input_tokens",
#                 "output_tokens",
#                 "total_tokens",
#                 "latency_seconds",
#                 "inputPrice",
#                 "outputPrice",
#                 "totalPrice",
#                 "input_tokens_per_item",
#             ]

#             # Format data for better readability
#             display_df = df[display_columns].copy()
#             display_df["timestamp"] = pd.to_datetime(
#                 display_df["timestamp"]
#             ).dt.strftime("%Y-%m-%d %H:%M:%S")
#             display_df["cost"] = display_df["cost"].apply(
#                 lambda x: f"${x:.6f}" if pd.notna(x) else "N/A"
#             )
#             display_df["latency_seconds"] = display_df["latency_seconds"].apply(
#                 lambda x: f"{x:.2f}s" if pd.notna(x) else "N/A"
#             )

#             # Generate markdown content
#             markdown_content = f"""# 📊 Langfuse Benchmark Results

# *Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*

# ## Summary Statistics
# - **Total Generations:** {len(df)}
# - **Total Input Tokens:** {df["input_tokens"].sum():,}
# - **Total Output Tokens:** {df["output_tokens"].sum():,}
# - **Total Tokens:** {df["total_tokens"].sum():,}
# - **Total Cost:** ${df["cost"].sum():.6f if df['cost'].notna().any() else 'N/A'}
# - **Average Latency:** {df["latency_seconds"].mean():.2f if df['latency_seconds'].notna().any() else 'N/A'}s

# ## Detailed Results

# {display_df.to_markdown(index=False)}

# ---

# *This report was generated using Langfuse analytics script.*
# """

#             with open(output_file, "w", encoding="utf-8") as f:
#                 f.write(markdown_content)

#             print(f"✅ Markdown table saved to: {output_file}")
#             return markdown_content

#         except Exception as e:
#             print(f"❌ Error generating markdown table: {e}")
#             return ""
