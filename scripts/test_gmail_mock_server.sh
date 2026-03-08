#!/bin/bash

export PYTHONUTF8=1

# --- 1. CONFIGURATION ---
MOCK_SERVER_DIR="$(pwd)/scripts/gmail_mock_server"
# Add tests to PYTHONPATH so pytest can resolve siblings
export PYTHONPATH="$MOCK_SERVER_DIR:$MOCK_SERVER_DIR/dataset/src:$MOCK_SERVER_DIR/dataset/tests"
export DATASET_PATH="$MOCK_SERVER_DIR/dataset"

# --- 2. PRE-FLIGHT TESTS (Pytest) ---
echo "🧪 Running internal unit tests..."
# Run pytest specifically on the mock server directory
# -c points to your config, --rootdir ensures correct path context
python -m pytest "$MOCK_SERVER_DIR" -c "$MOCK_SERVER_DIR/pyproject.toml"

if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Aborting server start."
    exit 1
fi
echo "✅ Internal tests passed!"

# --- 3. SERVER CLEANUP & START ---
cleanup_port() {
    echo "🔍 Checking for processes on port 8080..."
    powershell.exe -Command "Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id \$_ -Force }"
    sleep 1
}

cleanup_port

echo "🚀 Starting server on 127.0.0.1:8080..."
# Use python -m uvicorn so it uses the same environment as pytest
cd "$MOCK_SERVER_DIR" && python -m uvicorn mock_server:app --host 127.0.0.1 --port 8080 &
SERVER_PID=$!

# Wait for server to be ready
sleep 3

# --- 4. INTEGRATION SMOKE TEST (CURL) ---
echo -e "\n--- Sending Test Request ---"
# ... your existing curl commands ...

# --- 5. FINISH ---
echo -e "\n--- Cleaning up ---"
kill $SERVER_PID 2>/dev/null
cleanup_port
echo "✅ All systems green."