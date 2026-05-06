  #!/bin/bash

# Load specific tooling env
if [ -f .env.tooling ]; then
    export $(grep -v '^#' .env.tooling | xargs)
else
    echo "Error: .env.tooling file not found"
    exit 1
fi

curl -X POST \
    -H "Authorization: token $SECRETS_PAT" \
    -H "Accept: application/vnd.github.v3+json" \
    https://api.github.com/repos/EAexist/subscription-killer-api-benchmark/dispatches \
    -d '{"event_type": "new_ai_benchmark_build", "client_payload": {"image_name": "ghcr.io/eaexist/subscription-killer-api:9aa1b6698762d378893a4d40ff4bb5c8f587cfd3"}}'