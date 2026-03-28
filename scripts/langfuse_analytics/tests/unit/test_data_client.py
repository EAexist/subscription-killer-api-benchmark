import os
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from analytics.langfuse_client import LangfuseDataClient
from analytics import config


class TestLangfuseDataClient(unittest.TestCase):
    @patch.dict(
        os.environ,
        {"LANGFUSE_SECRET_KEY": "test_secret", "LANGFUSE_PUBLIC_KEY": "test_public"},
    )
    def test_client_init_success(self):
        """Test that LangfuseDataClient is created when env vars are set."""
        client = LangfuseDataClient()
        self.assertIsNotNone(client.client)
        self.assertEqual(client.secret_key, "test_secret")
        self.assertEqual(client.public_key, "test_public")

    @patch.dict(os.environ, {}, clear=True)
    def test_client_init_failure(self):
        """Test that the script exits if env vars are missing."""
        with self.assertRaises(SystemExit) as cm:
            LangfuseDataClient()
        self.assertEqual(cm.exception.code, 1)

    @patch("analytics.langfuse_client.Langfuse")
    def test_fetch_benchmark_generations_success(self, mock_langfuse):
        """Test fetching generations with a mock Langfuse client."""
        mock_client = MagicMock()
        
        # Mock traces with proper pagination metadata
        mock_trace = MagicMock()
        mock_trace.id = "trace-1"
        mock_trace.tags = ["request_1"]
        
        # Create mock response for traces with proper pagination
        mock_trace_response = MagicMock()
        mock_trace_response.data = [mock_trace]
        mock_trace_response.meta.page = 1
        mock_trace_response.meta.total_pages = 1
        mock_client.api.trace.list.return_value = mock_trace_response
        
        # Mock generations with proper pagination metadata
        mock_generation_response = MagicMock()
        mock_generation = MagicMock()
        mock_generation.__getitem__ = lambda self, key: {
            "id": "gen-1",
            "traceId": "trace-1",
            "usageDetails": {"input": 100, "output": 50, "total": 150},
            "costDetails": {"input": 0.001, "output": 0.0005, "total": 0.0015},
            "metadata": {"task_name": "test_task"},
            "version": "test-version"
        }[key]
        mock_generation.get = lambda key, default=None: {
            "id": "gen-1",
            "traceId": "trace-1", 
            "usageDetails": {"input": 100, "output": 50, "total": 150},
            "costDetails": {"input": 0.001, "output": 0.0005, "total": 0.0015},
            "metadata": {"task_name": "test_task"},
            "version": "test-version"
        }.get(key, default)
        
        mock_generation_response.data = [mock_generation]
        mock_generation_response.meta.cursor = None  # No cursor for single page
        mock_client.api.observations_v_2.get_many.return_value = mock_generation_response

        client = LangfuseDataClient()
        client.client = mock_client  # Override the client with our mock

        df = client.fetch_benchmark_generations("test-run")
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 1)
        mock_client.api.trace.list.assert_called_once()
        mock_client.api.observations_v_2.get_many.assert_called_once()

    # @patch("analytics.langfuse_client.Langfuse")
    # def test_fetch_benchmark_generations_empty(self, mock_langfuse):
    #     """Test fetching when no generations are found."""
    #     mock_client = MagicMock()
        
    #     # Mock empty traces
    #     mock_client.api.trace.list.return_value.data = []
        
    #     # Mock empty generations
    #     mock_response = MagicMock()
    #     mock_response.data = []
    #     mock_client.api.observations_v_2.get_many.return_value = mock_response

    #     client = LangfuseDataClient()
    #     client.client = mock_client  # Override the client with our mock

    #     df = client.fetch_benchmark_generations("test-run")
    #     self.assertIsInstance(df, pd.DataFrame)
    #     self.assertEqual(len(df), 0)

    def test_transform_to_dataframe_empty(self):
        """Test that an empty list of generations results in an empty DataFrame."""
        client = LangfuseDataClient()
        df = client.transform_to_dataframe([], {})
        self.assertTrue(df.empty)

    def test_transform_to_dataframe_with_data(self):
        """Test transformation of a list of mock generation objects."""
        mock_generation = {
            "id": "gen-1",
            "traceId": "trace-1",
            "startTime": "2023-01-01T12:00:00.000Z",
            "name": "test-generation",
            "usageDetails": {
                "input": 100,
                "instruction_tokens": 80,
                "output": 50,
                "input_tokens_per_item": 10,
                "output_tokens_per_item": 5,
                "total": 150,
            },
            "costDetails": {"input": 0.0001, "output": 0.00005, "total": 0.00015},
            "version": "test-version",
            "metadata": {"task_name": "test_task"},
        }
        
        trace_to_index = {"trace-1": 1, "trace-2": None}

        client = LangfuseDataClient()
        df = client.transform_to_dataframe([mock_generation], trace_to_index)

        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["id"], "gen-1")
        self.assertEqual(df.iloc[0]["request_index"], 1)
        self.assertEqual(df.iloc[0]["input_tokens"], 100)
        self.assertEqual(df.iloc[0]["instruction_tokens"], 80)
        self.assertEqual(df.iloc[0]["output_tokens"], 50)
        self.assertEqual(df.iloc[0]["input_tokens_per_item"], 10)
        self.assertEqual(df.iloc[0]["output_tokens_per_item"], 5)
        self.assertEqual(df.iloc[0]["total_tokens"], 150)
        self.assertEqual(df.iloc[0]["cost_input"], 0.0001)
        self.assertEqual(df.iloc[0]["cost_output"], 0.00005)
        self.assertEqual(df.iloc[0]["cost_total"], 0.00015)
        self.assertEqual(df.iloc[0]["app_version"], "test-version")
        self.assertEqual(df.iloc[0]["task_name"], "test_task")

    # @pytest.mark.skipif(
    #     not (os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY")),
    #     reason="Langfuse credentials not available",
    # )
    # @pytest.mark.capture_output  # This will capture output but make it available
    # def test_data_client_integration(self):
    #     """Integration test connecting to real Langfuse cloud with TEST_RUN tag."""
    #     try:
    #         test_version = os.environ.get("TEST_RUN_ID") or "benchmark-dev-2"
    #         client = LangfuseDataClient()

    #         generations = client.fetch_benchmark_generations(test_version)

    #         if not generations:
    #             print(
    #                 f"ℹ️  TEST_RUN tag {test_version} not found in Langfuse - skipping test"
    #             )
    #             self.skipTest("TEST_RUN observations not found")

    #         # Log raw data for manual verification
    #         print(f"\n🔍 Raw observations count: {len(generations)}")

    #         if generations:
    #             print("📄 Observations:")
    #             for g in generations:
    #                 print(f"{g}")
    #                 print(f"Full Metadata: {g.get('metadata')}")

    #         # If we found observations, verify we can transform them
    #         df = client.transform_to_dataframe(generations)
    #         self.assertGreater(len(df), 0)
    #         print(
    #             f"✅ Successfully connected and fetched {len(generations)} observations"
    #         )
    #         print("\n📊 DataFrame preview:")
    #         print(df.head())
    #         print(f"\n📋 DataFrame columns: {list(df.columns)}")
    #         print(f"📏 DataFrame shape: {df.shape}")

    #     except Exception as e:
    #         self.fail(f"Integration test failed: {e}")


if __name__ == "__main__":
    unittest.main()
