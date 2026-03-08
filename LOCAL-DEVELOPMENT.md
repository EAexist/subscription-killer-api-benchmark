# Local Development Guide

This guide explains how to run the benchmark locally without pushing to GitHub.

## Prerequisites

1. **Docker Desktop** running
2. **Java 21** installed
3. **Maven** installed
4. **Target repository** with Gradle build available locally

## Quick Start

### 1. Build Your Docker Image

In your target repository directory:
```bash
./gradlew bootBuildImage --imageName=subscription-killer:local-dev
```

### 2. Configure Environment

Edit your `.env` file (already exists) with:
```bash
# Required
IMAGE_NAME=subscription-killer:local-dev
APP_GIT_COMMIT=your-actual-commit-hash
APP_GIT_TAG=your-tag-or-commit-hash

# Benchmark configuration
AI_BENCHMARK_ENABLE_VERBOSE_DOCKER_LOGS=false
AI_BENCHMARK_ENDPOINT=api/benchmark/analyze
AI_BENCHMARK_K6_ITERATIONS=5
AI_BENCHMARK_K6_WARMUP_ITERATIONS=2
AI_BENCHMARK_REQUEST_TIMEOUT=5m

# Pricing
GEMINI_3_FLASH_PREVIEW_INPUT_TOKEN_PRICE_PER_MILLION=0.075
GEMINI_3_FLASH_PREVIEW_OUTPUT_TOKEN_PRICE_PER_MILLION=0.3
```

### 3. Run the Benchmark

**On Windows (PowerShell):**
```powershell
.\run-local-benchmark.ps1
```

**On Linux/Mac/WSL:**
```bash
./run-local-benchmark.sh
```

## What the Script Does

The local script replicates the GitHub workflow:

1. **Loads environment** from `.env` file
2. **Validates** required variables
3. **Extracts metadata** from Docker image (commit, tag)
4. **Sets up Spring environment** (uses existing `.env.spring.benchmark` or creates minimal)
5. **Runs the benchmark** using `./run-ai-benchmark.sh`
6. **Shows results location**

## Docker Image Options

### Option A: Local Build (Recommended for Development)
```bash
# In target repo
./gradlew bootBuildImage --imageName=subscription-killer:local-dev

# In .env
IMAGE_NAME=subscription-killer:local-dev
```

### Option B: GitHub Container Registry
```bash
# Pull existing image
docker pull ghcr.io/your-org/your-repo:commit-hash

# In .env
IMAGE_NAME=ghcr.io/your-org/your-repo:commit-hash
```

### Option C: Local Registry
```bash
# Build and push to local registry
./gradlew bootBuildImage --imageName=localhost:5000/subscription-killer:latest
docker push localhost:5000/subscription-killer:latest

# In .env
IMAGE_NAME=localhost:5000/subscription-killer:latest
```

## Environment Variables

### Required Variables
- `IMAGE_NAME`: Docker image name (e.g., `subscription-killer:local-dev`)
- `APP_GIT_COMMIT`: Git commit hash from target repo
- `APP_GIT_TAG`: Git tag or commit hash for results organization

### Optional Variables
- `AI_BENCHMARK_K6_ITERATIONS`: Number of test iterations (default: 1)
- `AI_BENCHMARK_K6_WARMUP_ITERATIONS`: Warmup iterations (default: 1)
- `AI_BENCHMARK_ENDPOINT`: API endpoint to test (default: `api/benchmark/analyze`)
- `AI_BENCHMARK_REQUEST_TIMEOUT`: Request timeout (default: `5m`)
- `AI_BENCHMARK_ENABLE_VERBOSE_DOCKER_LOGS`: Enable verbose logs (default: `false`)
- `SPRING_ENV_FILE`: Spring environment file path (default: `.env.spring.benchmark`)

### Pricing Variables
- `GEMINI_3_FLASH_PREVIEW_INPUT_TOKEN_PRICE_PER_MILLION`: Input token cost
- `GEMINI_3_FLASH_PREVIEW_OUTPUT_TOKEN_PRICE_PER_MILLION`: Output token cost

## Results

Results are saved to:
```
results/ai-benchmark/{APP_GIT_TAG}/{timestamp}/
├── data/
│   ├── spring-boot-logs.txt
│   └── spring-boot-logs.json
├── reports/
├── logs/
└── artifacts/
```

## Troubleshooting

### Docker Image Not Found
```
❌ Error: Docker image 'subscription-killer:local-dev' not found locally!
```
**Solution**: Build the image first in your target repo:
```bash
./gradlew bootBuildImage --imageName=subscription-killer:local-dev
```

### Missing Environment Variables
```
❌ Error: APP_GIT_COMMIT is required but not set!
```
**Solution**: Add the missing variable to your `.env` file.

### Docker Not Running
```
❌ Error: Docker is not running!
```
**Solution**: Start Docker Desktop.

### Spring Environment Issues
The script will create a minimal Spring configuration if `.env.spring.benchmark` is missing, or you can specify a custom file:
```bash
SPRING_ENV_FILE=.env.spring.benchmark.dev
```

## Differences from GitHub Workflow

| GitHub Workflow | Local Development |
|----------------|------------------|
| Triggered by repository dispatch | Manual execution |
| Uses GitHub secrets/variables | Uses `.env` file |
| Pulls from ghcr.io | Uses local or any registry |
| Uploads artifacts | Saves to local `results/` |
| Automated metadata extraction | Same extraction process |
| Parallel job processing | Single-threaded execution |

## Best Practices

1. **Use meaningful image names**: `subscription-killer:feature-branch-name`
2. **Commit before building**: Ensure your Docker image has proper metadata labels
3. **Clean up old images**: `docker image prune -f`
4. **Monitor Docker resources**: Large benchmarks can consume significant memory
5. **Use version control**: Track your `.env.example` but ignore `.env`

## Advanced Usage

### Custom Spring Configuration
Create a custom Spring environment file:
```bash
# .env.spring.benchmark.dev
SPRING_PROFILES_ACTIVE=benchmark,dev
SPRING_DATASOURCE_URL=jdbc:postgresql://localhost:5432/test_db
# ... other Spring properties
```

Then set in your `.env`:
```bash
SPRING_ENV_FILE=.env.spring.benchmark.dev
```

### Debug Mode
Enable verbose logging:
```bash
AI_BENCHMARK_ENABLE_VERBOSE_DOCKER_LOGS=true
```

### Keep Containers Running
For debugging, keep containers running after the test:
```bash
AI_BENCHMARK_KEEP_CONTAINERS=true
AI_BENCHMARK_WAIT_TIME_MS=300000  # 5 minutes
```
