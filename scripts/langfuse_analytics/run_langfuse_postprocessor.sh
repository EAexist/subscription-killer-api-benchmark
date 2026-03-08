#!/bin/bash
# Langfuse Post-Processing Runner
# This script runs the Langfuse post-processor with sensible defaults

set -e

# Default values
version=""
OUTPUT_DIR="results/langfuse"
MARKDOWN_FILE="langfuse_benchmark_results.md"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --run-tag)
            version="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --markdown-file)
            MARKDOWN_FILE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --run-tag TAG        Specific run tag to filter results (e.g., run-2026-02-21)"
            echo "  --output-dir DIR     Output directory for results (default: results/langfuse)"
            echo "  --markdown-file FILE  Output markdown file name (default: langfuse_benchmark_results.md)"
            echo "  -h, --help           Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  LANGFUSE_SECRET_KEY  Your Langfuse secret key"
            echo "  LANGFUSE_PUBLIC_KEY  Your Langfuse public key"
            echo "  LANGFUSE_HOST        Langfuse host (default: https://cloud.langfuse.com)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if required environment variables are set
if [[ -z "$LANGFUSE_SECRET_KEY" || -z "$LANGFUSE_PUBLIC_KEY" ]]; then
    echo "❌ Error: LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY environment variables must be set"
    echo ""
    echo "Please set these environment variables before running the script:"
    echo "export LANGFUSE_SECRET_KEY='your-secret-key'"
    echo "export LANGFUSE_PUBLIC_KEY='your-public-key'"
    echo "export LANGFUSE_HOST='https://cloud.langfuse.com'  # optional"
    exit 1
fi

# Check if Python dependencies are installed
if ! python -c "import langfuse, pandas, matplotlib" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    pip install -r ../../requirements.txt
fi

# Build the command
CMD="python langfuse_postprocessor.py"

if [[ -n "$version" ]]; then
    CMD="$CMD --run-tag \"$version\""
fi

CMD="$CMD --output-dir \"$OUTPUT_DIR\""
CMD="$CMD --markdown-file \"$MARKDOWN_FILE\""

echo "🚀 Running Langfuse post-processing..."
echo "📁 Output directory: $OUTPUT_DIR"
if [[ -n "$version" ]]; then
    echo "🏷️  Run tag: $version"
fi
echo ""

# Execute the command
eval $CMD

echo ""
echo "✅ Langfuse post-processing completed!"
echo "📂 Results saved in: $OUTPUT_DIR"
echo ""
echo "Generated files:"
if [[ -f "$OUTPUT_DIR/$MARKDOWN_FILE" ]]; then
    echo "  📄 $OUTPUT_DIR/$MARKDOWN_FILE"
fi
if [[ -d "$OUTPUT_DIR/plots" ]]; then
    echo "  📊 $OUTPUT_DIR/plots/ (plots)"
fi
if [[ -f "$OUTPUT_DIR/raw_benchmark_data.csv" ]]; then
    echo "  📈 $OUTPUT_DIR/raw_benchmark_data.csv"
fi
