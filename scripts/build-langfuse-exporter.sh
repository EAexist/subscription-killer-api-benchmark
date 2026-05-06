#!/bin/bash

# Build the Langfuse Exporter Docker image
echo "🔨 Building Langfuse Exporter Docker image..."

# Change to langfuse_loader directory to use its .dockerignore
cd scripts/langfuse_loader
docker build --no-cache -t langfuse-exporter:latest -f Dockerfile .
cd ../..

if [ $? -eq 0 ]; then
    echo " Langfuse Exporter Docker image built successfully"
    
    # Run and test the exporter using the same approach as Makefile test-run
    echo " Running and testing the Langfuse Exporter..."
    
    # Create test output file
    touch test_output.log
    
    # Run the exporter container with test configuration in background
    docker run --rm \
        --name langfuse-exporter-test \
        -e LANGFUSE_HOST="http://localhost:3000" \
        -e LANGFUSE_PUBLIC_KEY="pk-lf-12345" \
        -e LANGFUSE_SECRET_KEY="sk-lf-12345" \
        -e AI_BENCHMARK_K6_ITERATIONS="10" \
        -e DATA_STORAGE_ROOT="/app/data-storage" \
        -e PYTHONIOENCODING="utf-8" \
        langfuse-exporter:latest \
        python main.py --app-version "test-version" --run-id "test-run-$(date +%s)" > test_output.log 2>&1 &
    
    PID=$!
    
    # Set up cleanup trap
    trap "docker kill langfuse-exporter-test 2>/dev/null; wait $PID 2>/dev/null; rm -f test_output.log" EXIT
    
    # Monitor output and detect expected error pattern
    tail -f test_output.log | while IFS= read -r line; do
        echo "$line"
        if echo "$line" | grep -q "status_code: 500.*body: Internal Server Error\|Connection refused\|Errno 111"; then
            echo "----------------------------------------------------------"
            echo " SUCCESS: Expected connectivity error caught."
            echo "Langfuse server not available - test completed successfully."
            echo "----------------------------------------------------------"
            exit 0
        fi
    done
    
else
    echo " Failed to build Langfuse Exporter Docker image"
    exit 1
fi
