#!/bin/bash
ROOT_DIR=$(pwd)

echo "Building image"
docker build --progress=plain \
    -t gmail-mock-server:latest \
    -f scripts/gmail_mock_server/Dockerfile \
    scripts/gmail_mock_server

if [ $? -ne 0 ]; then
    echo "❌ Failed to build Gmail Mock Server Docker image"
    exit 1
fi

echo "✅ Gmail Mock Server Docker image built successfully"
echo ""
echo "Starting container"

# Use MSYS_NO_PATHCONV=1 to stop Git Bash from mangling paths
# OR use //app to escape the path conversion
MSYS_NO_PATHCONV=1 docker run --rm -d \
    -p 8080:8080 \
    -e N_REQUESTS=200 \
    -e N_EMAILS_PER_REQUEST=40 \
    -e N_COMPANIES_PER_CHUNK=5 \
    --name gmail-mock-test \
    gmail-mock-server:latest

echo "⏳ Waiting for server to start with retry mechanism"

# Initial wait time before first health check
INITIAL_DELAY=10
echo "🕐 Initial ${INITIAL_DELAY}s wait for container startup"
sleep $INITIAL_DELAY

# Retry mechanism for server startup
MAX_RETRIES=4
RETRY_DELAY=5
RETRY_COUNT=0
HEALTH_STATUS="000"

while [ $RETRY_COUNT -lt $MAX_RETRIES ] && [ "$HEALTH_STATUS" != "200" ]; do
    if [ $RETRY_COUNT -gt 0 ]; then
        echo "🔄 Retry $RETRY_COUNT/$MAX_RETRIES - waiting ${RETRY_DELAY}s"
        sleep $RETRY_DELAY
    fi
    
    echo "🔍 Testing health check endpoint (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)"
    HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health)
    echo "   HTTP status: $HEALTH_STATUS"
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

if [ "$HEALTH_STATUS" = "200" ]; then
    echo "✅ Health check endpoint: PASSED (HTTP $HEALTH_STATUS) after $RETRY_COUNT attempts"
    curl -s http://localhost:8080/health | jq .
else
    echo "❌ Health check endpoint: FAILED after $MAX_RETRIES attempts (HTTP $HEALTH_STATUS)"
    echo "📋 Checking container logs for troubleshooting"
    docker logs gmail-mock-test
fi

echo ""
# Test messages endpoint
echo "🔍 Testing messages endpoint"
MESSAGES_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/messages)
if [ "$MESSAGES_STATUS" = "200" ]; then
    echo "✅ Messages endpoint: PASSED (HTTP $MESSAGES_STATUS)"
    curl -s http://localhost:8080/messages | head -c 200
    echo ""
else
    echo "❌ Messages endpoint: FAILED (HTTP $MESSAGES_STATUS)"
fi

echo ""
# Overall test result
if [ "$HEALTH_STATUS" = "200" ] && [ "$MESSAGES_STATUS" = "200" ]; then
    echo "🎉 All tests PASSED! Gmail mock server is working correctly."
    echo "🎉 Build and test completed successfully!"
else
    echo "💥 Some tests FAILED! Check the server logs for issues."
    echo "❌ Build or test failed"
    exit 1
fi

echo ""
echo "Stopping container"
docker stop gmail-mock-test
