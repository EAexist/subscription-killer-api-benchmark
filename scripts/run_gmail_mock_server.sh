#!/bin/bash

export PYTHONUTF8=1

# --- 1. CONFIGURATION ---
MOCK_SERVER_DIR="$(pwd)/scripts/gmail_mock_server"
# Add tests to PYTHONPATH so pytest can resolve siblings
export PYTHONPATH="$MOCK_SERVER_DIR:$MOCK_SERVER_DIR/dataset/src:$MOCK_SERVER_DIR/dataset/tests"
export DATASET_PATH="$MOCK_SERVER_DIR/dataset"

# --- 2. SERVER CLEANUP & START ---
cleanup_port() {
    echo "🔍 Checking for processes on port 8081..."
    powershell.exe -Command "Get-NetTCPConnection -LocalPort 8081 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id \$_ -Force }"
    sleep 1
}

cleanup_port

VENV_PYTHON="$MOCK_SERVER_DIR/.venv/Scripts/python.exe"

echo "🚀 Starting server on 127.0.0.1:8081..."
"$VENV_PYTHON" -m uvicorn mock_server:app --app-dir "$MOCK_SERVER_DIR" --host 127.0.0.1 --port 8081 &
SERVER_PID=$!

# Wait for server to be ready
sleep 3

echo "✅ Gmail mock server is running on http://127.0.0.1:8081"
echo "📋 Server PID: $SERVER_PID"
echo "🛑 To stop the server, run: kill $SERVER_PID"
echo "🌐 Health check: curl http://127.0.0.1:8081/health"

# Keep the script running and wait for user interrupt
trap 'echo -e "\n🛑 Stopping server..."; kill $SERVER_PID 2>/dev/null; cleanup_port; echo "✅ Server stopped."; exit 0' INT TERM

echo "⏳ Server is running. Press Ctrl+C to stop..."
wait $SERVER_PID
