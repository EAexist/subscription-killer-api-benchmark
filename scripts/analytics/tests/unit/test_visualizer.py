import os
import shutil
import tempfile
import unittest

import pandas as pd
from analytics.calculator import BenchmarkCalculator
from analytics.visualizer import BenchmarkVisualizer


class TestBenchmarkVisualizer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_visualizer_init(self):
        """Test that BenchmarkVisualizer initializes with default output directory."""
        visualizer = BenchmarkVisualizer()
        self.assertIsNotNone(visualizer.output_dir)
        self.assertTrue(os.path.exists(visualizer.output_dir))

    def test_plot_cost_convergence(self):
        """Test that cost convergence plot is generated and saved."""
        # Create test data with multiple versions and trace_ids
        data = {
            "request_index": [1, 2, 3, 4],
            "total_cost": [0.1, 0.08, 0.06, 0.05],
            "app_version": ["v1", "v1", "v2", "v2"],
        }
        df = pd.DataFrame(data)

        # Calculate convergence metrics
        df_with_cma = BenchmarkCalculator.add_convergence_metrics(df, "total_cost")

        print("\n=== Test Data ===")
        print(df_with_cma)

        visualizer = BenchmarkVisualizer()
        output_path = os.path.join(self.temp_dir, "test_convergence.png")
        visualizer.plot_cost_convergence(df_with_cma, output_path, "Test Plot Title", "Test X Label", show_plot=True)

        print(f"\n✅ Convergence plot saved to: {output_path}")
        print("Please check the generated plot to verify it looks correct.")

        # Verify the calculated CMA values
        expected_cma_v1 = [0.1, 0.09]  # (0.1)/1, (0.1+0.08)/2
        expected_cma_v2 = [0.06, 0.055]  # (0.06)/1, (0.06+0.05)/2

        v1_data = df_with_cma[df_with_cma["app_version"] == "v1"]
        v2_data = df_with_cma[df_with_cma["app_version"] == "v2"]

        print("\n=== CMA Calculations ===")
        print("v1 CMA values:", list(v1_data["amortized_cost"]))
        print("v1 expected:", expected_cma_v1)
        print("v2 CMA values:", list(v2_data["amortized_cost"]))
        print("v2 expected:", expected_cma_v2)

        self.assertEqual(list(v1_data["amortized_cost"]), expected_cma_v1)
        self.assertEqual(list(v2_data["amortized_cost"]), expected_cma_v2)

        # Verify the file was actually created
        self.assertTrue(os.path.exists(output_path))

    # def test_generate_markdown_table(self):
    #     """Test that a markdown file is created."""
    #     data = {
    #         "timestamp": [pd.Timestamp("2023-01-01")],
    #         "name": ["test"],
    #         "model": ["test_model"],
    #         "input_tokens": [1],
    #         "output_tokens": [1],
    #         "total_tokens": [2],
    #         "cost": [0.1],
    #         "latency_seconds": [0.5],
    #     }
    #     df = pd.DataFrame(data)
    #     output_file = os.path.join(self.temp_dir, "test.md")

    #     visualizer = BenchmarkVisualizer()
    #     with patch("builtins.open", mock_open()) as mock_file:
    #         result = visualizer.generate_markdown_table(df, output_file)
    #         mock_file.assert_called_with(output_file, "w", encoding="utf-8")
    #         self.assertIn("Langfuse Benchmark Results", result)

    # def test_generate_markdown_table_empty_df(self):
    #     """Test that empty DataFrame returns empty string."""
    #     df = pd.DataFrame()
    #     visualizer = BenchmarkVisualizer()

    #     with patch("builtins.print") as mock_print:
    #         result = visualizer.generate_markdown_table(df)
    #         self.assertEqual(result, "")
    #         mock_print.assert_called_with("⚠️  No data to generate markdown table")


if __name__ == "__main__":
    unittest.main()
