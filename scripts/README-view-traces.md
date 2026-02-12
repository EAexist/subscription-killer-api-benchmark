# Zipkin Trace Viewer

This script allows you to view your benchmark trace data in the Zipkin browser UI.

## Files Created

- `scripts/view-traces.sh` - Linux/macOS bash script
- `scripts/view-traces.ps1` - Windows PowerShell script  
- `scripts/view-traces.bat` - Windows batch script (alternative)

## Usage

### Linux/macOS (Bash)
```bash
./scripts/view-traces.sh results/benchmark/5d8f13c/2026-02-08_04-33-25/data/raw-zipkin-traces.json
```

### Windows (PowerShell)
```powershell
.\scripts\view-traces.ps1 -TraceFile "results\benchmark\5d8f13c\2026-02-08_04-33-25\data\raw-zipkin-traces.json"
```

### Windows (Batch)
```cmd
scripts\view-traces.bat "results\benchmark\5d8f13c\2026-02-08_04-33-25\data\raw-zipkin-traces.json"
```

## Optional Parameters

### Custom Port
```bash
./scripts/view-traces.sh results/benchmark/5d8f13c/2026-02-08_04-33-25/data/raw-zipkin-traces.json 9412
```

```powershell
.\scripts\view-traces.ps1 -TraceFile "results\benchmark\5d8f13c\2026-02-08_04-33-25\data\raw-zipkin-traces.json" -Port 9412
```

## What the Script Does

1. **Checks Docker** - Ensures Docker is running
2. **Validates File** - Confirms the trace file exists and contains data
3. **Starts Zipkin** - Launches a Zipkin container (or uses existing one)
4. **Imports Traces** - Loads your trace data into Zipkin
5. **Opens Browser** - Automatically opens the Zipkin UI
6. **Keeps Running** - Script stays active so you can use the UI

## Features

- ✅ **Automatic container management** - Starts Zipkin if needed
- ✅ **Port conflict detection** - Handles existing containers
- ✅ **JSON parsing** - Extracts trace data from your benchmark files
- ✅ **Error handling** - Graceful handling of common issues
- ✅ **Cross-platform** - Works on Linux, macOS, and Windows

## Stopping Zipkin

When you're done viewing traces, stop the container:

```bash
docker stop benchmark-zipkin-viewer-9411
docker rm benchmark-zipkin-viewer-9411
```

## Troubleshooting

### Docker Not Running
Start Docker Desktop or your Docker daemon.

### Port Already in Use
Use a different port:
```bash
./scripts/view-traces.sh your-trace-file.json 9412
```

### Trace File Not Found
Ensure the path is correct and the file exists:
```bash
ls -la results/benchmark/*/2026-*/data/raw-zipkin-traces.json
```

### Browser Doesn't Open
Manually navigate to: http://localhost:9411

## Example Output

```
=== Zipkin Trace Viewer ===
Trace file: results/benchmark/5d8f13c/2026-02-08_04-33-25/data/raw-zipkin-traces.json
Zipkin UI port: 9411
Extracting trace data...
Trace data extracted successfully
Starting Zipkin container...
Zipkin container started: benchmark-zipkin-viewer-9411
Waiting for Zipkin to be ready...
.....
Zipkin is ready!
Importing traces to Zipkin...
Traces imported successfully!
Opening Zipkin UI in browser: http://localhost:9411

=== Zipkin Trace Viewer Running ===
UI URL: http://localhost:9411
Container: benchmark-zipkin-viewer-9411

To stop Zipkin when done:
docker stop benchmark-zipkin-viewer-9411
docker rm benchmark-zipkin-viewer-9411
```

## Manual Alternative

If the scripts don't work, you can manually run Zipkin:

```bash
# Start Zipkin
docker run -d -p 9411:9411 --name zipkin-viewer openzipkin/zipkin:latest

# Wait for it to start (10-20 seconds)
sleep 20

# Import traces (extract JSON first)
jq -r '.rawData' results/benchmark/5d8f13c/2026-02-08_04-33-25/data/raw-zipkin-traces.json | \
curl -X POST -H "Content-Type: application/json" -d @- http://localhost:9411/api/v2/spans

# Open browser
open http://localhost:9411
```
