# Langfuse Post-Processing for Benchmark Results

This directory contains scripts for post-processing benchmark results using the Langfuse Python SDK to generate tables and plots.

## 🚀 Quick Start

### Prerequisites

1. **Set up Langfuse credentials** as environment variables:
   ```bash
   export LANGFUSE_SECRET_KEY="your-secret-key"
   export LANGFUSE_PUBLIC_KEY="your-public-key"
   export LANGFUSE_HOST="https://cloud.langfuse.com"  # optional
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Post-Processor

#### Option 1: Using the convenience scripts (recommended)

**Linux/macOS:**
```bash
# Run with default settings (fetches all generations)
./scripts/run_langfuse_postprocessor.sh

# Run with specific tag
./scripts/run_langfuse_postprocessor.sh --run-tag "run-2026-02-21"

# Custom output directory
./scripts/run_langfuse_postprocessor.sh --output-dir "my-results" --run-tag "run-2026-02-21"
```

**Windows (PowerShell):**
```powershell
# Run with default settings
.\scripts\run_langfuse_postprocessor.ps1

# Run with specific tag
.\scripts\run_langfuse_postprocessor.ps1 -RunTag "run-2026-02-21"

# Custom output directory
.\scripts\run_langfuse_postprocessor.ps1 -OutputDir "my-results" -RunTag "run-2026-02-21"
```

#### Option 2: Direct Python execution

```bash
python scripts/langfuse_postprocessor.py --run-tag "run-2026-02-21" --output-dir "results/langfuse"
```

## 📊 Generated Outputs

The post-processor generates the following files in the output directory:

### 📄 `langfuse_benchmark_results.md`
A comprehensive markdown report containing:
- Summary statistics (total tokens, costs, latency)
- Detailed results table with formatted data
- Timestamps and model information

### 📊 `plots/` directory
Contains visualizations:
- `cost_trend.png` - Cost over time
- `token_usage.png` - Input/output/total token trends
- `latency_trend.png` - Latency over time
- `cost_vs_tokens.png` - Scatter plot of cost vs token usage

### 📈 `raw_benchmark_data.csv`
Raw CSV data for further analysis or custom reporting

## 🔧 Configuration

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--run-tag` | Specific run tag to filter results | None (all generations) |
| `--output-dir` | Output directory for results | `results/langfuse` |
| `--markdown-file` | Output markdown file name | `langfuse_benchmark_results.md` |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LANGFUSE_SECRET_KEY` | ✅ | Your Langfuse secret key |
| `LANGFUSE_PUBLIC_KEY` | ✅ | Your Langfuse public key |
| `LANGFUSE_HOST` | ❌ | Langfuse host (defaults to cloud) |

## 🔄 Integration with CI/CD

The post-processor is automatically integrated into the GitHub Actions workflow (`.github/workflows/benchmark-release.yml`). 

To enable it:

1. **Add secrets to your GitHub repository:**
   - `LANGFUSE_SECRET_KEY`
   - `LANGFUSE_PUBLIC_KEY`

2. **Add repository variables (optional):**
   - `LANGFUSE_HOST` (if using self-hosted Langfuse)

The workflow will:
- Automatically run after benchmark completion
- Generate Langfuse analysis for each run tag
- Include results in GitHub releases
- Skip gracefully if credentials aren't configured

## 📋 Example Usage Scenarios

### Scenario 1: Analyze Latest Benchmark Run
```bash
# Assuming your latest run used tag "run-2026-02-21"
./scripts/run_langfuse_postprocessor.sh --run-tag "run-2026-02-21"
```

### Scenario 2: Compare Multiple Runs
```bash
# Run for different tags and compare the generated markdown files
./scripts/run_langfuse_postprocessor.sh --run-tag "run-2026-02-20" --output-dir "results/run-2026-02-20"
./scripts/run_langfuse_postprocessor.sh --run-tag "run-2026-02-21" --output-dir "results/run-2026-02-21"
```

### Scenario 3: Custom Analysis
```bash
# Generate raw data and use it for custom analysis
python scripts/langfuse_postprocessor.py --output-dir "custom-analysis"
# Then work with custom-analysis/raw_benchmark_data.csv in your preferred tool
```

## 🛠️ Troubleshooting

### Common Issues

1. **"Missing required environment variables"**
   - Ensure `LANGFUSE_SECRET_KEY` and `LANGFUSE_PUBLIC_KEY` are set
   - Check for typos in variable names

2. **"No generations found for tag"**
   - Verify the run tag exists in Langfuse
   - Try running without `--run-tag` to see all available generations

3. **"ModuleNotFoundError: No module named 'langfuse'"**
   - Run `pip install -r requirements.txt`
   - Ensure you're using the correct Python environment

4. **Permission errors (Windows)**
   - Run PowerShell as Administrator
   - Or use: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Debug Mode

For debugging, you can run the Python script directly with verbose output:
```bash
python -v scripts/langfuse_postprocessor.py --run-tag "your-tag"
```

## 📚 Dependencies

- **langfuse** >= 2.0.0 - Official Langfuse Python SDK
- **pandas** >= 1.5.0 - Data manipulation and analysis
- **matplotlib** >= 3.6.0 - Plotting and visualization

## 🤝 Contributing

To extend the post-processor:

1. **Add new plots**: Modify the `generate_plots()` function in `langfuse_postprocessor.py`
2. **Add new metrics**: Update the `transform_to_dataframe()` function
3. **Customize output format**: Modify the `generate_markdown_table()` function

## 📄 License

This script follows the same license as the main project.
