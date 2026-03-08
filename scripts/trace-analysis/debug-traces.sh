#!/bin/bash
# Debug script to test trace data format

TRACE_FILE="$1"

echo "=== Debug Trace Data ==="
echo "File: $TRACE_FILE"

# Extract and show the raw data structure
echo ""
echo "1. Raw file structure:"
jq -r '.rawData | type' "$TRACE_FILE" 2>/dev/null || echo "jq not available"

# Extract the actual traces
echo ""
echo "2. Extracting traces..."
python -c "
import json
import sys
try:
    with open('$TRACE_FILE', 'r') as f:
        data = json.load(f)
    raw_data = data.get('rawData', '')
    if raw_data:
        parsed_data = json.loads(raw_data)
        print(f'Type: {type(parsed_data)}')
        print(f'Length: {len(parsed_data)}')
        if parsed_data:
            print(f'First item type: {type(parsed_data[0])}')
            if isinstance(parsed_data[0], list):
                print(f'First trace length: {len(parsed_data[0])}')
                if parsed_data[0]:
                    print(f'First span: {parsed_data[0][0].get(\"name\", \"no name\")}')
        # Save to temp file for inspection
        with open('/tmp/debug_traces.json', 'w') as f:
            json.dump(parsed_data, f, indent=2)
        print('Saved to /tmp/debug_traces.json')
    else:
        print('No raw data found')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
"

echo ""
echo "3. Checking if Zipkin API accepts this format..."
echo "Testing with a single span..."

# Extract just one span for testing
python -c "
import json
import sys
import subprocess

try:
    with open('$TRACE_FILE', 'r') as f:
        data = json.load(f)
    raw_data = data.get('rawData', '')
    if raw_data:
        parsed_data = json.loads(raw_data)
        if parsed_data and parsed_data[0]:
            # Get first span
            first_span = parsed_data[0][0] if parsed_data[0] else None
            if first_span:
                print('Testing single span import...')
                result = subprocess.run([
                    'curl', '-X', 'POST', 
                    '-H', 'Content-Type: application/json',
                    '-d', json.dumps([first_span]),
                    'http://localhost:9411/api/v2/spans'
                ], capture_output=True, text=True)
                print(f'Response code: {result.returncode}')
                print(f'Response: {result.stdout}')
                if result.stderr:
                    print(f'Error: {result.stderr}')
except Exception as e:
    print(f'Error: {e}')
"
