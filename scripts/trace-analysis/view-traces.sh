#!/bin/bash
# === Zipkin Trace Viewer Script ===
# Usage: ./view-traces.sh <trace-file> [port]

set -e

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <trace-file> [port]"
    echo "Example: $0 results/benchmark/5d8f13c/2026-02-08_04-33-25/data/raw-zipkin-traces.json"
    echo "Example: $0 results/benchmark/5d8f13c/2026-02-08_04-33-25/data/raw-zipkin-traces.json 9412"
    exit 1
fi

TRACE_FILE="$1"
PORT="${2:-9411}"

echo "=== Zipkin Trace Viewer ==="
echo "Trace file: $TRACE_FILE"
echo "Zipkin UI port: $PORT"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not running or not installed. Please start Docker."
    exit 1
fi

# Check if trace file exists
if [ ! -f "$TRACE_FILE" ]; then
    echo "Error: Trace file not found: $TRACE_FILE"
    exit 1
fi

# Check if jq is available for JSON parsing
if ! command -v jq &> /dev/null; then
    echo "Warning: jq not found. Using Python for JSON parsing."
    JSON_PARSER="python"
else
    JSON_PARSER="jq"
fi

# Extract raw data from JSON wrapper
echo "Extracting trace data..."
if [ "$JSON_PARSER" = "jq" ]; then
    RAW_TRACES=$(jq -r '.rawData' "$TRACE_FILE" | jq -r '. | flatten | .')
else
    RAW_TRACES=$(python -c "
import json
import sys
try:
    with open('$TRACE_FILE', 'r') as f:
        data = json.load(f)
    raw_data = data.get('rawData', '')
    # Parse the escaped JSON string
    if raw_data:
        parsed_data = json.loads(raw_data)
        # Flatten the list of traces into a single list of spans
        flat_spans = []
        for trace in parsed_data:
            if isinstance(trace, list):
                flat_spans.extend(trace)
            else:
                flat_spans.append(trace)
        # Convert back to JSON string for import
        print(json.dumps(flat_spans))
    else:
        print('')
except Exception as e:
    print(f'Error parsing file: {e}', file=sys.stderr)
    sys.exit(1)
")
fi

if [ -z "$RAW_TRACES" ] || [ "$RAW_TRACES" = "null" ]; then
    echo "Error: No trace data found in file"
    exit 1
fi

echo "Trace data extracted successfully"
echo "Data length: $(echo "$RAW_TRACES" | wc -c) characters"
echo "Number of spans: $(echo "$RAW_TRACES" | jq '. | length' 2>/dev/null || echo "jq not available")"

# Check if Zipkin container is already running on the port
EXISTING_CONTAINER=$(docker ps --filter "publish=$PORT" --filter "ancestor=openzipkin/zipkin" --format "{{.ID}}" | head -n 1)

if [ -n "$EXISTING_CONTAINER" ]; then
    echo "Zipkin container already running on port $PORT"
    CONTAINER_NAME="$EXISTING_CONTAINER"
else
    # Start new Zipkin container
    echo "Starting Zipkin container..."
    CONTAINER_NAME="benchmark-zipkin-viewer-$PORT"
    
    # Stop and remove existing container with same name if it exists
    OLD_CONTAINER=$(docker ps -a --filter "name=$CONTAINER_NAME" --format "{{.ID}}" | head -n 1)
    if [ -n "$OLD_CONTAINER" ]; then
        echo "Removing existing container: $OLD_CONTAINER"
        docker stop "$OLD_CONTAINER" >/dev/null 2>&1 || true
        docker rm "$OLD_CONTAINER" >/dev/null 2>&1 || true
    fi
    
    # Start new container
    docker run -d --name "$CONTAINER_NAME" -p "$PORT:9411" openzipkin/zipkin:latest
    
    echo "Zipkin container started: $CONTAINER_NAME"
    
    # Wait for Zipkin to be ready
    echo "Waiting for Zipkin to be ready..."
    READY=false
    ATTEMPTS=0
    MAX_ATTEMPTS=30
    
    while [ "$READY" = false ] && [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
        if curl -f "http://localhost:$PORT/health" >/dev/null 2>&1; then
            READY=true
        else
            ATTEMPTS=$((ATTEMPTS + 1))
            sleep 2
            echo -n "."
        fi
    done
    
    echo ""
    
    if [ "$READY" = false ]; then
        echo "Error: Zipkin failed to start within expected time"
        docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
        docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
        exit 1
    fi
    
    echo "Zipkin is ready!"
fi

# Import traces to Zipkin
echo "Importing traces to Zipkin..."
IMPORT_URL="http://localhost:$PORT/api/v2/spans"

# Debug: Show first 500 characters of data
echo "Sample of data being imported:"
echo "$RAW_TRACES" | head -c 500
echo "..."
echo ""

# Create temp file for debugging
TEMP_FILE=$(mktemp)
echo "$RAW_TRACES" > "$TEMP_FILE"

if curl -X POST -H "Content-Type: application/json" -d @"$TEMP_FILE" "$IMPORT_URL" >/dev/null 2>&1; then
    echo "Traces imported successfully!"
else
    echo "Warning: Failed to import traces. Checking response..."
    # Try to get more detailed error
    RESPONSE=$(curl -X POST -H "Content-Type: application/json" -d @"$TEMP_FILE" "$IMPORT_URL" 2>&1)
    echo "Response: $RESPONSE"
    echo "You can still view the Zipkin UI, but traces may not be available."
fi

# Clean up temp file
rm -f "$TEMP_FILE"

# Open browser
ZIPKIN_URL="http://localhost:$PORT"
echo "Opening Zipkin UI in browser: $ZIPKIN_URL"

# Try different commands to open browser
if command -v xdg-open &> /dev/null; then
    xdg-open "$ZIPKIN_URL" 2>/dev/null || true
elif command -v open &> /dev/null; then
    open "$ZIPKIN_URL" 2>/dev/null || true
elif command -v start &> /dev/null; then
    start "$ZIPKIN_URL" 2>/dev/null || true
else
    echo "Could not open browser automatically. Please manually navigate to: $ZIPKIN_URL"
fi

echo ""
echo "=== Zipkin Trace Viewer Running ==="
echo "UI URL: $ZIPKIN_URL"
echo "Container: $CONTAINER_NAME"
echo ""
echo "To stop Zipkin when done:"
echo "docker stop $CONTAINER_NAME"
echo "docker rm $CONTAINER_NAME"
echo ""
echo "Press Ctrl+C to stop this script (Zipkin will continue running)"

# Keep script running or allow user to exit
trap 'echo -e "\nStopping script (Zipkin continues running)"; exit 0' INT

while true; do
    sleep 10
    # Check if container is still running
    if ! docker ps --filter "id=$CONTAINER_NAME" --format "{{.ID}}" | grep -q "$CONTAINER_NAME"; then
        echo "Zipkin container stopped unexpectedly"
        break
    fi
done
