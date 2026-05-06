#!/usr/bin/env python3
"""
Docker-based test for the Gmail API Mock Server.
Builds and tests the Docker container without running the full Java benchmark.
"""

import asyncio
import subprocess
import sys
import time

from test_mock_server import MockServerTests


def run_command(cmd, description, cwd=None, capture_output=True):
    """Run a command and handle errors."""
    print(f"🔧 {description}...")
    print(f"   Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=capture_output, text=True, check=True
        )
        if capture_output and result.stdout.strip():
            print(f"   Output: {result.stdout.strip()}")
        print("✅ Success!")
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Failed!")
        if capture_output:
            print(f"   Error: {e.stderr}")
        return False


def build_docker_image():
    """Build the Docker image."""
    return run_command(
        ["docker", "build", "-t", "gmail-mock-server:latest", "."],
        "Building Docker image",
        cwd="scripts/gmail_mock_server",
    )


def run_docker_container():
    """Run the Docker container."""
    # Stop any existing container
    run_command(
        ["docker", "stop", "gmail-mock-server-test"],
        "Stopping existing container (if any)",
        capture_output=False,
    )
    run_command(
        ["docker", "rm", "gmail-mock-server-test"],
        "Removing existing container (if any)",
        capture_output=False,
    )

    # Run new container
    success = run_command(
        [
            "docker",
            "run",
            "-d",
            "--name",
            "gmail-mock-server-test",
            "-p",
            "8080:8080",
            "--mount",
            "type=bind,source=../datasets,target=/app/datasets,readonly",
            "gmail-mock-server:latest",
        ],
        "Starting Docker container",
    )

    if not success:
        return False

    # Wait for container to be ready
    print("⏳ Waiting for server to start...")
    for i in range(30):  # Wait up to 30 seconds
        try:
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "gmail-mock-server-test",
                    "curl",
                    "-f",
                    "http://localhost:8080/health",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                print("✅ Server is ready!")
                return True
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass

        time.sleep(1)
        print(f"   Waiting... ({i + 1}/30)")

    print("❌ Server failed to start within 30 seconds")
    return False


def cleanup_container():
    """Clean up the Docker container."""
    print("🧹 Cleaning up...")
    run_command(
        ["docker", "stop", "gmail-mock-server-test"],
        "Stopping container",
        capture_output=False,
    )
    run_command(
        ["docker", "rm", "gmail-mock-server-test"],
        "Removing container",
        capture_output=False,
    )


async def main():
    """Main test runner."""
    print("🐳 Docker-based Mock Server Test Suite")
    print("=" * 50)

    # Build Docker image
    if not build_docker_image():
        print("❌ Docker build failed!")
        return False

    # Run container
    if not run_docker_container():
        cleanup_container()
        print("❌ Container failed to start!")
        return False

    try:
        # Run tests
        tests = MockServerTests()
        success = await tests.run_all_tests()
        return success
    finally:
        # Always cleanup
        cleanup_container()


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        cleanup_container()
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite error: {e}")
        cleanup_container()
        sys.exit(1)
