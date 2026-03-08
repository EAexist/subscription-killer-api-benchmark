#!/usr/bin/env python3
"""
Integration tests for main.py with real Langfuse client.
"""

import os
import sys
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
            # Mock sys.argv to include the required --app-version argument
            original_argv = sys.argv
            sys.argv = ["main.py", "--app-version", "benchmark-dev-2"]

            # Call main() directly - it will use its own logic
            main()

            # Restore original sys.argv
            sys.argv = original_argv

            # Verify that the pipeline completed successfully
            # (main() will print success message or exit with error)
            print(" Main integration test completed successfully")

        except SystemExit as e:
            # Restore original sys.argv even if SystemExit occurs
            sys.argv = original_argv
            if e.code != 0:
                self.fail(f"Main() exited with error code: {e.code}")
        except Exception as e:
            # Restore original sys.argv for any other exception
            sys.argv = original_argv
            self.fail(f"Main() integration test failed: {e}")


if __name__ == "__main__":
    unittest.main()
