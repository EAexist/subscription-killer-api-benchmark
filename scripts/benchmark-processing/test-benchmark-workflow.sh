#!/bin/bash

# Test script that replicates the GitHub workflow functionality locally
# Usage: ./scripts/test-benchmark-workflow.sh <commit_hash>

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${BLUE}📊 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Check arguments
if [ $# -ne 1 ]; then
    echo "Usage: $0 <commit_hash>"
    echo "Example: $0 abc123def"
    echo ""
    echo "The script will automatically find the benchmark directory for the given commit."
    exit 1
fi

COMMIT_HASH="$1"

# Auto-find benchmark directory (same logic as GitHub workflow)
COMMIT_BASE_DIR="results/ai-benchmark/${COMMIT_HASH}"

if [ ! -d "$COMMIT_BASE_DIR" ]; then
    print_error "Commit directory does not exist: $COMMIT_BASE_DIR"
    print_info "Available commits in results/ai-benchmark/:"
    ls -1 results/ai-benchmark/ 2>/dev/null || print_info "No benchmark results found"
    exit 1
fi

# Find the timestamp directory (same as GitHub workflow)
TIMESTAMP_DIR=$(ls "$COMMIT_BASE_DIR" | head -1)
BENCHMARK_DIR="${COMMIT_BASE_DIR}/${TIMESTAMP_DIR}"

if [ ! -d "$BENCHMARK_DIR" ]; then
    print_error "Benchmark directory not found: $BENCHMARK_DIR"
    print_info "Available timestamp directories in $COMMIT_BASE_DIR:"
    ls -1 "$COMMIT_BASE_DIR" 2>/dev/null || print_info "No timestamp directories found"
    exit 1
fi

if [ ! -f "$BENCHMARK_DIR/data/raw-zipkin-traces.json" ]; then
    print_error "Trace data not found in: $BENCHMARK_DIR/data/raw-zipkin-traces.json"
    exit 1
fi

print_step "Starting benchmark workflow test for commit: $COMMIT_HASH"
print_info "Auto-detected benchmark directory: $BENCHMARK_DIR"

# Set up environment variables (you can adjust these as needed)
export GEMINI_3_FLASH_PREVIEW_INPUT_TOKEN_PRICE_PER_MILLION="${GEMINI_3_FLASH_PREVIEW_INPUT_TOKEN_PRICE_PER_MILLION:-0.50}"
export GEMINI_3_FLASH_PREVIEW_OUTPUT_TOKEN_PRICE_PER_MILLION="${GEMINI_3_FLASH_PREVIEW_OUTPUT_TOKEN_PRICE_PER_MILLION:-3.00}"

print_info "AI Token Prices: Input=$GEMINI_3_FLASH_PREVIEW_INPUT_TOKEN_PRICE_PER_MILLION$/M, Output=$GEMINI_3_FLASH_PREVIEW_OUTPUT_TOKEN_PRICE_PER_MILLION$/M"

# Step 0: Download Latest Benchmark Data (if needed)
print_step "Step 0: Checking for existing benchmark data..."

# Check if files exist, if not, download from releases
if [ ! -f "results/reports/ai-metrics.csv" ] || [ ! -f "results/reports/supplementary-metrics.csv" ] || [ ! -f "results/reports/latest-benchmark-results.md" ]; then
    print_info "Missing benchmark data files, downloading from GitHub releases..."
    
    # Ensure reports directory exists
    mkdir -p "results/reports"
    
    # Download latest benchmark data
    python scripts/download_benchmark_data.py \
        --repo-owner "EAexist" \
        --repo-name "subscription-killer-api-benchmark" \
        --output-dir "results/reports"
    
    if [ $? -eq 0 ]; then
        print_success "Benchmark data downloaded successfully"
    else
        print_error "Failed to download benchmark data"
        exit 1
    fi
else
    print_success "Benchmark data files already exist"
fi

# Step 1: Add Column to Existing CSV Reports
print_step "Step 1: Adding column to existing CSV reports..."

# Update CSV files directly
python scripts/benchmarkUtils.py \
    --existing-report "results/ai-benchmark" \
    --commit "$COMMIT_HASH" \
    --dir "$BENCHMARK_DIR"

if [ $? -eq 0 ]; then
    print_success "CSV reports updated successfully"
else
    print_error "Failed to update CSV reports"
    exit 1
fi

# Step 2: Convert CSV to Markdown and Update README
print_step "Step 2: Converting CSV to markdown and updating README..."

# Generate markdown from CSV files
python scripts/markdownUtils.py \
    --ai-csv "results/reports/ai-metrics.csv" \
    --supplementary-csv "results/reports/supplementary-metrics.csv" \
    --existing-report "results/ai-benchmark" \
    --commits "$COMMIT_HASH" \
    --dirs "$BENCHMARK_DIR"

if [ $? -eq 0 ]; then
    print_success "Markdown generated successfully"
else
    print_error "Failed to generate markdown"
    exit 1
fi

# Display markdown content
if [ -f "results/reports/latest-benchmark-results.md" ]; then
    print_step "Generated Markdown Content:"
    echo "----------------------------------------"
    cat "results/reports/latest-benchmark-results.md"
    echo "----------------------------------------"
else
    print_error "Generated markdown file not found"
    exit 1
fi

# Update README.md
print_step "Step 3: Updating README.md..."

if [ ! -f "README.md" ]; then
    print_error "README.md not found"
    exit 1
fi

# Create backup of README.md
cp README.md README.md.backup

# Update README.md using awk (same as GitHub workflow)
# Create a temporary script to properly replace benchmark results
cat > replace_benchmark.awk << 'EOF'
BEGIN {
  in_benchmark_section = 0
  skip_content = 0
}

/<!-- BENCHMARK_RESULTS_START -->/ {
  in_benchmark_section = 1
  skip_content = 1
  print
  # Print the new benchmark content
  while ((getline line < "results/reports/latest-benchmark-results.md") > 0) {
    print line
  }
  close("results/reports/latest-benchmark-results.md")
  next
}

/<!-- BENCHMARK_RESULTS_END -->/ {
  if (in_benchmark_section && skip_content) {
    in_benchmark_section = 0
    skip_content = 0
  }
  print
  next
}

{
  if (!skip_content) {
    print
  }
}
EOF

awk -f replace_benchmark.awk README.md > README.tmp && mv README.tmp README.md

if [ $? -eq 0 ]; then
    print_success "README.md updated successfully"
else
    print_error "Failed to update README.md"
    # Restore backup
    mv README.md.backup README.md
    exit 1
fi

# Clean up backup and temporary files
rm -f README.md.backup replace_benchmark.awk

# Step 4: Display Benchmark Results (CSV format)
print_step "Step 4: Displaying benchmark results (CSV format)..."

echo ""
echo "=== 🤖 AI Metrics CSV ==="
if [ -f "results/reports/ai-metrics.csv" ]; then
    cat "results/reports/ai-metrics.csv"
else
    print_error "AI metrics CSV not found"
fi

echo ""
echo "=== 📈 Supplementary Performance Indicators CSV ==="
if [ -f "results/reports/supplementary-metrics.csv" ]; then
    cat "results/reports/supplementary-metrics.csv"
else
    print_error "Supplementary metrics CSV not found"
fi

# Step 5: Show git status (for manual commit)
print_step "Step 5: Git status (for manual commit)"
echo ""
git status --porcelain
echo ""

if git diff --quiet && git diff --cached --quiet; then
    print_info "No changes to commit"
else
    print_info "Changes are ready to commit. You can manually run:"
    echo "  git add results/reports/ README.md"
    echo "  git commit -m \"docs: auto-update benchmark results [skip ci]\""
    echo "  git push"
fi

print_success "Benchmark workflow test completed successfully!"

# Summary of files created/updated
echo ""
echo "📁 Files created/updated:"
echo "  • results/reports/ai-metrics.csv"
echo "  • results/reports/supplementary-metrics.csv"
echo "  • results/reports/latest-benchmark-results.md"
echo "  • README.md (updated benchmark section)"
