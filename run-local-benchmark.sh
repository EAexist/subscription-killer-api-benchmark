#!/bin/bash

# Local Benchmark Runner Script
# Replicates the GitHub workflow process locally using .env and .env.spring.benchmark files

set -e  # Exit on any error

# Default: load .env.dev overrides
USE_DEV_ENV=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --prod)
            USE_DEV_ENV=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--prod]"
            echo "  --prod          Use production config (skip .env.dev overrides)"
            echo "  -h, --help      Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Load environment variables from .env file
if [ -f ".env" ]; then
    echo "📝 Loading environment variables from .env..."
    set -a
    source .env
    set +a
else
    echo "❌ Error: .env file not found!"
    exit 1
fi

# Load .env.dev overrides if enabled and file exists
if [ "$USE_DEV_ENV" = true ]; then
    if [ -f ".env.dev" ]; then
        echo "📝 Loading environment variable overrides from .env.dev..."
        set -a
        source .env.dev
        set +a
    else
        echo "⚠️  .env.dev file not found, skipping overrides"
    fi
else
    echo "📝 Skipping .env.dev overrides (production mode enabled by --prod)"
fi

# Set default IMAGE_NAME if not already set
IMAGE_NAME="${IMAGE_NAME:-subscription-killer-api}"

# Function to extract metadata from Docker image
extract_image_metadata() {
    local image_name="$1"
    
    echo "📋 Extracting metadata from image: $image_name"
    
    # Check if image exists locally
    if ! docker image inspect "$image_name" > /dev/null 2>&1; then
        echo "❌ Error: Docker image '$image_name' not found locally!"
        exit 1
    fi
    
    # Extract labels from image
    RAW_COMMIT=$(docker inspect --format='{{index .Config.Labels "org.opencontainers.image.revision"}}' "$image_name" 2>/dev/null || echo "")
    RAW_TAG=$(docker inspect --format='{{index .Config.Labels "org.opencontainers.image.ref.name"}}' "$image_name" 2>/dev/null || echo "")
    
    echo "✅ Extracted metadata:"
    echo "   Commit: $RAW_COMMIT"
    echo "   Tag: $RAW_TAG"
    
    # Export for use by the benchmark script
    export EXTRACTED_COMMIT="$RAW_COMMIT"
    export EXTRACTED_TAG="$RAW_TAG"
}

# Function to setup Spring environment file
setup_spring_environment() {
    echo "🌱 Setting up Spring environment..."
    
    local spring_env_file=".env.spring.benchmark"
    
    if [ -f "$spring_env_file" ]; then
        echo "✅ Using Spring environment file: $spring_env_file"
        export SPRING_ENV_FILE="$spring_env_file"
    else
        echo "❌ Error: Spring environment file not found: $spring_env_file"
        exit 1
    fi
}

# Function to run the benchmark
run_benchmark() {
    # Set environment variables for the benchmark script
    export APP_GIT_COMMIT="$EXTRACTED_COMMIT"
    export APP_GIT_TAG="$EXTRACTED_TAG"
    export IMAGE_NAME="$IMAGE_NAME"
    
    # Make sure the benchmark script is executable
    chmod +x run-ai-benchmark.sh
    
    # Run the benchmark
    ./run-ai-benchmark.sh
}

# Function to show results location
show_results() {
    echo ""
    echo "📊 Benchmark completed!"
    echo "📁 Results location: results/ai-benchmark/${EXTRACTED_TAG}/"
}

# Main execution flow
main() {
echo "🚀 Starting Local Benchmark Process..."
    echo ""
    
    # Step 1: Extract metadata from Docker image
    extract_image_metadata "$IMAGE_NAME"
    echo ""
    
    # Step 2: Setup Spring environment
    setup_spring_environment
    echo ""
    
    # Step 3: Run the benchmark
    run_benchmark
    echo ""
    
    # Step 4: Show results
    show_results
}

# Handle script interruption gracefully
trap 'echo ""; echo "❌ Benchmark interrupted by user"; exit 1' INT

# Run main function
main "$@"
