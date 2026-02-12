#!/bin/bash

# AI Cost Benchmark Runner Script
# This script loads environment variables from .env and runs the Testcontainers AI benchmark

set -e  # Exit on any error

echo "🚀 Starting AI Cost Benchmark..."

# Load environment variables from .env file (if it exists)
if [ -f ".env" ]; then
    echo "📝 Loading environment variables from .env..."
    set -a
    source .env
    set +a
else
    echo "⚠️  .env file not found, using environment variables only"
fi

# Override with workflow environment variables if set
if [ -n "$APP_GIT_COMMIT" ]; then
    echo "🔧 Using workflow-provided APP_GIT_COMMIT: $APP_GIT_COMMIT"
fi
if [ -n "$APP_GIT_TAG" ]; then
    echo "🔧 Using workflow-provided APP_GIT_TAG: $APP_GIT_TAG"
fi

# Display current configuration
echo "🔧 Configuration:"
echo "   Git Commit: ${APP_GIT_COMMIT:-not-set}"
echo "   Git Tag: ${APP_GIT_TAG:-not-set}"
echo "   K6 Iterations: ${AI_BENCHMARK_K6_ITERATIONS:-not-set}"
echo "   WARMUP Iterations: ${AI_BENCHMARK_K6_WARMUP_ITERATIONS:-not-set}"
echo "   Endpoint: ${AI_BENCHMARK_ENDPOINT:-not-set}"
echo "   Request Timeout: ${AI_BENCHMARK_REQUEST_TIMEOUT:-not-set}"
echo "   Verbose Docker Logs: ${AI_BENCHMARK_ENABLE_VERBOSE_DOCKER_LOGS:-not-set}"

# Validate required variables
if [ -z "$APP_GIT_COMMIT" ]; then
    echo "❌ Error: APP_GIT_COMMIT is required but not set!"
    echo "   Set it in .env file or as environment variable"
    exit 1
fi

if [ -z "$AI_BENCHMARK_K6_ITERATIONS" ]; then
    echo "⚠️  Warning: AI_BENCHMARK_K6_ITERATIONS not set, using default: 1"
    export AI_BENCHMARK_K6_ITERATIONS=1
fi
# Build the full Docker image name
if [ -n "$IMAGE_NAME" ]; then
    DOCKER_IMAGE="$IMAGE_NAME"
    echo "   Using workflow-provided image: $DOCKER_IMAGE"
else
    DOCKER_IMAGE="$IMAGE_NAME"
    echo "   Using pre-built image: $DOCKER_IMAGE"
fi
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "Please start Docker and try again"
    exit 1
fi

# Check if the Docker image exists locally, pull if not found
if ! docker image inspect "$DOCKER_IMAGE" > /dev/null 2>&1; then
    echo "⚠️  Docker image '$DOCKER_IMAGE' not found locally"
    echo "   Attempting to pull from registry..."
    if ! docker pull "$DOCKER_IMAGE" > /dev/null 2>&1; then
        echo "❌ Error: Failed to pull Docker image '$DOCKER_IMAGE'"
        echo "   Make sure the image exists in the registry or build it locally:"
        echo "   ./gradlew bootBuildImage --imageName=\"$DOCKER_IMAGE\""
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "✅ Successfully pulled image from registry"
    fi
fi

# Run the Maven test
echo "🧪 Running AI Cost Benchmark Test..."
echo "   Command: mvn test -Dtest=PerformanceBenchmarkTest"
echo ""

# Run the specific test class
mvn test -Dtest=PerformanceBenchmarkTest -Dorg.slf4j.simpleLogger.log.com.github.dockerjava=WARN -Dorg.slf4j.simpleLogger.log.org.testcontainers=INFO

# Check if test passed
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ AI Cost Benchmark completed successfully!"
else
    echo ""
    echo "❌ AI Cost Benchmark failed!"
    echo "   Check the test output above for details"
    exit 1
fi
