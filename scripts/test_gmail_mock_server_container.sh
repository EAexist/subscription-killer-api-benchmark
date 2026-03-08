#!/bin/bash
ROOT_DIR=$(pwd)

echo "Building image..."
docker build -t gmail-mock-server:latest -f scripts/gmail_mock_server/Dockerfile .

echo "Starting container..."

# Use MSYS_NO_PATHCONV=1 to stop Git Bash from mangling paths
# OR use //app to escape the path conversion
MSYS_NO_PATHCONV=1 docker run --rm -it \
  -p 8080:8080 \
  -v "$ROOT_DIR/scripts/gmail_mock_server:/app" \
  gmail-mock-server:latest