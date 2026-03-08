#!/bin/bash

# Build the Gmail API Mock Server Docker image
echo "🔨 Building Gmail API Mock Server Docker image..."

docker build --no-cache -t gmail-mock-server:latest -f scripts/gmail_mock_server/Dockerfile .

if [ $? -eq 0 ]; then
    echo "✅ Gmail Mock Server Docker image built successfully"
else
    echo "❌ Failed to build Gmail Mock Server Docker image"
    exit 1
fi
