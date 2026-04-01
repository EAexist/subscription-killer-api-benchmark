# Langfuse Analytics

Analytics pipeline for processing Langfuse benchmark data with cost convergence analysis and visualization.

## 🚀 Quick Start

### Prerequisites
```bash
# Set Langfuse credentials
export LANGFUSE_SECRET_KEY="your-secret-key"
export LANGFUSE_PUBLIC_KEY="your-public-key"
export LANGFUSE_HOST="https://cloud.langfuse.com"

# Install dependencies
pip install -r requirements.txt
```

### Running Analytics

```bash
# Basic usage
python main.py --app-version "v1.0.0" --run-id "run-123" --analytics-run-id "analytics-456"

# Using Makefile (recommended)
make test-analytics MARKER_FILTER="-m integration"
```

## 📊 Features

### Data Processing
- **Pagination Handling**: Robust page-based (traces) and cursor-based (generations) pagination
- **Retry Logic**: Exponential backoff for API delays
- **CSV Merging**: Combines multiple benchmark runs
- **Missing Data**: Smart filling of incomplete request indices

### Visualizations
- **Cost Convergence**: Professional integrated legends with convergence status
- **Marginal Cost**: Per-request cost analysis with variance
- **Task-Specific**: Separate plots per task type

### Metrics
- **Amortized Cost**: Cumulative moving average per thousand requests
- **Token Usage**: Input/output token analysis
- **Convergence Status**: CV-based convergence detection

## 📁 Directory Structure

```
scripts/langfuse_analytics/
├── analytics/                 # Core analytics modules
│   ├── calculator.py         # Cost and convergence calculations
│   ├── config.py            # Plot styling configuration
│   ├── constants.py         # Column definitions
│   ├── langfuse_client.py   # Langfuse API client with pagination
│   ├── loader.py            # CSV data loading and merging
│   └── visualizer.py        # Plot generation with professional styling
├── tests/                    # Unit and integration tests
├── main.py                   # Main analytics pipeline
├── requirements.txt         # Python dependencies
└── Makefile                 # Build and test commands
```

## 🔧 Configuration

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `LANGFUSE_SECRET_KEY` | ✅ | Langfuse secret key |
| `LANGFUSE_PUBLIC_KEY` | ✅ | Langfuse public key |
| `LANGFUSE_HOST` | ❌ | Langfuse host URL |
| `AI_BENCHMARK_K6_ITERATIONS` | ✅ | Expected request count |

### Command Line Arguments
| Argument | Required | Description |
|----------|----------|-------------|
| `--app-version` | ✅ | App version/tag to fetch |
| `--run-id` | ✅ | Run identifier |
| `--analytics-run-id` | ✅ | Analytics run identifier |

## 📈 Output

### Generated Files
- **Raw Data**: `data-storage/results/raw/benchmark_{app_version}_{timestamp}.csv`
- **Plots**: `data-storage/results/plots/amortized_ai_cost.png`
- **Task Plots**: `data-storage/results/plots/amortized_ai_cost_{task_name}.png`
- **Logs**: `data-storage/logs/{app_version}/analytics_{run_id}_{analytics_run_id}_{timestamp}.log`

### Plot Features
- **Professional Legends**: `{version} | {status} | ${cost}/1k req`
- **Convergence Detection**: CV < 0.05 = "Converged", else "Stabilizing"
- **Smart Ticks**: Automatic axis scaling
- **Clean Styling**: Professional color palette and fonts

## 🧪 Testing

```bash
# Run all tests
make test-analytics

# Run integration tests only
make test-analytics MARKER_FILTER="-m integration"

# Run unit tests only
make test-analytics MARKER_FILTER="-m unit"
```

## 🛠️ Key Components

### LangfuseDataClient
- Handles Langfuse API pagination (traces: page-based, generations: cursor-based)
- Implements exponential backoff retry logic
- Caches model pricing information
- Transforms API responses to DataFrames

### BenchmarkCalculator
- Calculates amortized cost convergence metrics
- Fills missing request indices per app version and task
- Computes marginal cost with price multipliers

### BenchmarkVisualizer
- Generates professional plots with integrated legends
- Handles cost convergence visualization
- Creates task-specific analysis plots

## 📋 Example Usage

```python
from analytics.langfuse_client import LangfuseDataClient
from analytics.calculator import BenchmarkCalculator
from analytics.visualizer import BenchmarkVisualizer

# Initialize components
client = LangfuseDataClient()
calculator = BenchmarkCalculator()
visualizer = BenchmarkVisualizer()

# Fetch data
df = client.fetch_benchmark_generations(
    app_version="v1.0.0",
    expected_count=200
)

# Process data
df_complete = calculator.fill_missing_requests(df, 200)
df_with_cma = calculator.add_convergence_metrics(df_complete, "cost_total")

# Generate plot
visualizer.plot_cost_convergence(
    df_with_cma,
    "output.png",
    "Cost Convergence Analysis",
    "Amortized Cost"
)
```

## 🤝 Architecture

The analytics pipeline follows a clean separation of concerns:

1. **Data Fetching** (`LangfuseDataClient`) → API interaction with retry logic
2. **Data Processing** (`BenchmarkCalculator`) → Metrics and convergence calculations  
3. **Visualization** (`BenchmarkVisualizer`) → Professional plot generation

This modular design enables easy extension and testing of individual components.
