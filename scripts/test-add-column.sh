#!/bin/bash

# CORRECTED test script for adding column to existing README benchmark report
# Tests the actual README.md path as used in GitHub workflow

set -e

echo "📊 Adding new benchmark column to existing README.md report (CORRECTED)..."

# Configuration - modify these values to test different scenarios
APP_GIT_COMMIT="0eeeddf"  # Change this to test different commits
GEMINI_3_FLASH_PREVIEW_INPUT_TOKEN_PRICE_PER_MILLION="0.50"
GEMINI_3_FLASH_PREVIEW_OUTPUT_TOKEN_PRICE_PER_MILLION="3.00"

echo "📝 Adding column to existing benchmark table..."

# Find the benchmark data directory for current commit (use latest timestamped directory)
LATEST_DIR=$(ls -t results/ai-benchmark/${APP_GIT_COMMIT} | head -n 1)
BENCHMARK_DIR="results/ai-benchmark/${APP_GIT_COMMIT}/${LATEST_DIR}"

if [ -z "$BENCHMARK_DIR" ] || [ ! -d "$BENCHMARK_DIR" ]; then
    echo "❌ Error: Benchmark directory not found for commit ${APP_GIT_COMMIT}"
    echo "📁 Available benchmark directories:"
    ls -la results/ai-benchmark/ 2>/dev/null || echo "No benchmark directories found"
    exit 1
fi

echo "📁 Using benchmark directory: $BENCHMARK_DIR"

# Call the Python script with README.md path (CORRECT)
echo "🔄 Adding column for commit ${APP_GIT_COMMIT} to README.md..."

GEMINI_3_FLASH_PREVIEW_INPUT_TOKEN_PRICE_PER_MILLION="0.50" \
GEMINI_3_FLASH_PREVIEW_OUTPUT_TOKEN_PRICE_PER_MILLION="3.00" \
python scripts/trace_ai_benchmark_comparison.py \
  --existing-report "README.md" \
  --commit "$APP_GIT_COMMIT" \
  --dir "$BENCHMARK_DIR"

if [ $? -eq 0 ]; then
    echo "✅ Successfully added column for ${APP_GIT_COMMIT} to README.md"
else
    echo "❌ Failed to add column for ${APP_GIT_COMMIT}"
    exit 1
fi

echo ""
echo "📋 Test Summary:"
echo "   ✅ Using correct README.md path"
echo "   ✅ Testing actual column addition logic"
echo "   ✅ Commit: $APP_GIT_COMMIT"
echo "   ✅ Benchmark Dir: $BENCHMARK_DIR"
echo "   - AI Cost Input Price: ${GEMINI_3_FLASH_PREVIEW_INPUT_TOKEN_PRICE_PER_MILLION}/million"
echo "   - AI Cost Output Price: ${GEMINI_3_FLASH_PREVIEW_OUTPUT_TOKEN_PRICE_PER_MILLION}/million"
echo ""
echo "🔍 Check README.md to see the updated benchmark table!"
