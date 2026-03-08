#!/usr/bin/env python3
"""
Integration tests for main.py with real Langfuse client.
"""

import os
import unittest

import pytest

from main import main


@pytest.mark.integration
class TestAnalytics(unittest.TestCase):
    """Integration tests for main analytics pipeline."""

    @pytest.mark.skipif(
        not (os.getenv("LANGFUSE_SECRET_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY")),
        reason="Langfuse credentials not available",
    )
    @pytest.mark.capture_output
    def test_analytics(self):
        """Test main() method with real Langfuse data."""
        try:
            # Call main() directly - it will use its own logic
            main()

            # Verify that the pipeline completed successfully
            # (main() will print success message or exit with error)
            print(" Main integration test completed successfully")

        except SystemExit as e:
            if e.code != 0:
                self.fail(f"Main() exited with error code: {e.code}")
        except Exception as e:
            self.fail(f"Main() integration test failed: {e}")


if __name__ == "__main__":
    unittest.main()
