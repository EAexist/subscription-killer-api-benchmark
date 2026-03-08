#!/usr/bin/env python3
"""
Quick test suite for the Gmail API Mock Server.
Run this to validate the server works before running the full Java benchmark.
"""

import asyncio
import json
import sys
from typing import Any, Dict

import aiohttp


class MockServerTester:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get(self, endpoint: str) -> Dict[str, Any]:
        """Make GET request and return response."""
        try:
            if self.session is None:
                return {"status": 0, "text": "Session not initialized", "headers": {}}
            async with self.session.get(f"{self.base_url}{endpoint}") as response:
                return {
                    "status": response.status,
                    "text": await response.text(),
                    "headers": dict(response.headers),
                }
        except Exception as e:
            return {"status": 0, "text": f"Connection error: {str(e)}", "headers": {}}

    async def post(self, endpoint: str, data: Any) -> Dict[str, Any]:
        """Make POST request and return response."""
        try:
            if self.session is None:
                return {"status": 0, "text": "Session not initialized", "headers": {}}
            async with self.session.post(
                f"{self.base_url}{endpoint}",
                json=data,
                headers={"Content-Type": "application/json"},
            ) as response:
                return {
                    "status": response.status,
                    "text": await response.text(),
                    "headers": dict(response.headers),
                }
        except Exception as e:
            return {"status": 0, "text": f"Connection error: {str(e)}", "headers": {}}


class MockServerTests:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def log(self, message: str, status: str = "INFO"):
        """Log message with status."""
        colors = {
            "PASS": "\033[92m",  # Green
            "FAIL": "\033[91m",  # Red
            "INFO": "\033[94m",  # Blue
            "WARN": "\033[93m",  # Yellow
        }
        reset = "\033[0m"
        color = colors.get(status, "")
        print(f"{color}[{status}]{reset} {message}")

    def assert_success(self, response: Dict[str, Any], test_name: str):
        """Assert response was successful."""
        if response["status"] == 200:
            self.passed += 1
            self.log(f"✅ {test_name}", "PASS")
            return True
        else:
            self.failed += 1
            self.log(
                f"❌ {test_name} - Status: {response['status']}, Response: {response['text']}",
                "FAIL",
            )
            return False

    def assert_contains(self, response: Dict[str, Any], expected: str, test_name: str):
        """Assert response contains expected text."""
        if expected in response["text"]:
            self.passed += 1
            self.log(f"✅ {test_name}", "PASS")
            return True
        else:
            self.failed += 1
            self.log(
                f"❌ {test_name} - Expected '{expected}' in response: {response['text']}",
                "FAIL",
            )
            return False

    async def test_health_check(self, tester: MockServerTester):
        """Test the /health endpoint."""
        self.log("Testing /health endpoint...", "INFO")
        response = await tester.get("/health")

        if not self.assert_success(response, "Health check status"):
            return False

        # Check if response contains expected fields
        try:
            data = json.loads(response["text"])
            if "status" in data and data["status"] == "healthy":
                self.passed += 1
                self.log("✅ Health check response format", "PASS")
                return True
            else:
                self.failed += 1
                self.log(f"❌ Health check response format: {data}", "FAIL")
                return False
        except json.JSONDecodeError:
            self.failed += 1
            self.log(f"❌ Health check JSON parsing failed: {response['text']}", "FAIL")
            return False

    async def test_list_messages(self, tester: MockServerTester):
        """Test the /messages endpoint."""
        self.log("Testing /messages endpoint...", "INFO")
        response = await tester.get("/messages")

        if not self.assert_success(response, "List messages status"):
            return False

        # Check if response contains comma-separated message IDs
        message_ids = response["text"].strip()
        if message_ids and "," in message_ids:
            self.passed += 1
            self.log(
                f"✅ List messages format: {len(message_ids.split(','))} IDs returned",
                "PASS",
            )
            return True
        else:
            self.failed += 1
            self.log(f"❌ List messages format: {message_ids}", "FAIL")
            return False

    async def test_batch_get(self, tester: MockServerTester):
        """Test the /messages/batch-get endpoint."""
        self.log("Testing /messages/batch-get endpoint...", "INFO")

        # First get some message IDs
        list_response = await tester.get("/messages")
        if list_response["status"] != 200:
            self.failed += 1
            self.log("❌ Cannot test batch-get - failed to get message IDs", "FAIL")
            return False

        message_ids = list_response["text"].strip().split(",")[:3]  # Take first 3 IDs

        # Test batch-get
        response = await tester.post("/messages/batch-get", message_ids)

        if not self.assert_success(response, "Batch get status"):
            return False

        # Check if response contains expected message data
        try:
            data = json.loads(response["text"])
            if "messages" in data and len(data["messages"]) > 0:
                self.passed += 1
                self.log(
                    f"✅ Batch get response: {len(data['messages'])} messages returned",
                    "PASS",
                )
                return True
            else:
                self.failed += 1
                self.log(f"❌ Batch get response format: {data}", "FAIL")
                return False
        except json.JSONDecodeError:
            self.failed += 1
            self.log(f"❌ Batch get JSON parsing failed: {response['text']}", "FAIL")
            return False

    async def test_first_message(self, tester: MockServerTester):
        """Test the /messages/first endpoint."""
        self.log("Testing /messages/first endpoint...", "INFO")

        # Test with some sample email addresses
        test_addresses = ["test@example.com", "user@example.com"]
        response = await tester.post("/messages/first", test_addresses)

        if not self.assert_success(response, "First message status"):
            return False

        # Response should be a message ID or empty string
        message_id = response["text"].strip()
        if message_id == "" or len(message_id) > 0:
            self.passed += 1
            self.log(f"✅ First message response: '{message_id}'", "PASS")
            return True
        else:
            self.failed += 1
            self.log(f"❌ First message response format: {message_id}", "FAIL")
            return False

    async def run_all_tests(self):
        """Run all tests."""
        self.log("🚀 Starting Mock Server Tests", "INFO")
        self.log("=" * 50, "INFO")

        async with MockServerTester() as tester:
            # Wait a moment for server to be ready
            await asyncio.sleep(1)

            # Run tests
            await self.test_health_check(tester)
            await self.test_list_messages(tester)
            await self.test_batch_get(tester)
            await self.test_first_message(tester)

        # Print summary
        self.log("=" * 50, "INFO")
        total = self.passed + self.failed
        self.log(f"📊 Test Results: {self.passed}/{total} passed", "INFO")

        if self.failed == 0:
            self.log("🎉 All tests passed! Server is ready for Java benchmark.", "PASS")
            return True
        else:
            self.log(
                f"💥 {self.failed} tests failed. Fix issues before running Java benchmark.",
                "FAIL",
            )
            return False


async def main():
    """Main test runner."""
    # Check if server is running
    tester = MockServerTester()
    try:
        async with tester:
            health_response = await tester.get("/health")
            if health_response["status"] != 200:
                print("❌ Server is not running or not healthy!")
                print("📝 Start the server first:")
                print("   cd scripts/gmail_mock_server")
                print("   python mock_server.py")
                print("   OR")
                print("   docker build -t gmail-mock-server:latest .")
                print("   docker run -p 8080:8080 gmail-mock-server:latest")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("📝 Make sure the server is running on http://localhost:8080")
        return False

    # Run tests
    tests = MockServerTests()
    success = await tests.run_all_tests()

    return success


if __name__ == "__main__":
    print("🧪 Gmail API Mock Server Test Suite")
    print("=" * 50)

    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite error: {e}")
        sys.exit(1)
