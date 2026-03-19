#!/usr/bin/env python3
"""
Benchmark Visualizer for generating plots and reports from Langfuse data.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd

from .config import PLOTS_DIR, apply_custom_style


class BenchmarkVisualizer:
    """Visualizer for creating plots and reports from benchmark data."""

    def __init__(self):
        """Initialize visualizer with output directory."""

        self.output_dir = PLOTS_DIR
        os.makedirs(self.output_dir, exist_ok=True)

        apply_custom_style()

    def plot_cost_convergence(
        self,
        df_subset: pd.DataFrame,
        output_path: str,
        title: str,
        x_label: str,
        show_plot: bool = False,
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
            )

        plt.title(title)
        plt.xlabel("Request")
        plt.ylabel(f"{x_label}($ per thousand requests)")
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.ylim(0)
        max_request_index = df_subset["request_index"].max()
        plt.xlim(0, max_request_index)

        # Set x-axis ticks every 5 units
        tick_positions = range(0, int(max_request_index) + 1, 5)
        plt.xticks(tick_positions)


        # 2. Add 10% padding to the upper limit
        max_cost = df_subset["amortized_cost"].max() * 1_000

        if max_cost > 0:
            plt.ylim(0, max_cost * 1.1)
        else:
            plt.ylim(0, 1) # Fallback for empty/zero data

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
