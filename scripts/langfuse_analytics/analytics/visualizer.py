#!/usr/bin/env python3
"""
Benchmark Visualizer for generating plots and reports from Langfuse data.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd

from .config import get_plots_dir, apply_custom_style


class BenchmarkVisualizer:
    """Visualizer for creating plots and reports from benchmark data."""

    def __init__(self):
        """Initialize visualizer with output directory."""

        self.output_dir = get_plots_dir()
        os.makedirs(self.output_dir, exist_ok=True)

        apply_custom_style()


    def plot_marginal_cost(
        self,
        df_subset: pd.DataFrame,
        output_path: str,
        title: str,
        x_label: str,
        ):
        
        mean_cost = df_subset['marginal_cost'].mean()
        std_dev = df_subset['marginal_cost'].std()

        # 2. Plotting the Bar with Variance
        plt.figure(figsize=(6, 8))
        plt.bar(['Avg Cost per Request'], [mean_cost], yerr=[std_dev], 
                color='#4CAF50',  # Professional green
                capsize=12,       # Adds horizontal lines to the error bar
                edgecolor='black', 
                alpha=0.8)

        # 3. Add Reporting Annotations
        plt.ylabel('Cost (USD)')
        plt.title('Backend AI Cost Stability Analysis')
        plt.grid(axis='y', linestyle='--', alpha=0.5)

        # Optional: Label the actual values on the chart
        plt.text(0, mean_cost / 2, f'Amortized: ${mean_cost:.2f}', ha='center', color='white', weight='bold')
        plt.text(0, mean_cost + std_dev + 0.02, f'Volatility (±${std_dev:.2f})', ha='center', color='darkred')

        plt.tight_layout()
        plt.savefig('backend_cost_report.png') 

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
        plt.xlabel("Number of Requests")
        plt.ylabel(f"{x_label}($ per thousand requests)")
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.ylim(0)
        max_request_index = df_subset["request_index"].max()
        plt.xlim(0, max_request_index)

        # Set x-axis ticks every 5 units
        self._set_smart_ticks(df_subset["request_index"].unique())

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

    def _set_smart_ticks(self, x_data, n_max=10, base=5):
        """
        Sets x-axis ticks to multiples of 'base' ensuring 
        the total number of ticks is less than 'n_max'.
        """
        x_min, x_max = min(x_data), max(x_data)
        x_range = x_max - x_min
        
        step = base
        # Increase step by 'base' until we are under the limit N
        while (x_range / step) >= n_max:
            step += base
            
        # Generate ticks: start at the first multiple of 'step' >= x_min
        start = (x_min // step) * step
        ticks = range(int(start), int(x_max) + step, step)
        
        plt.xticks(ticks)
        return step
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
