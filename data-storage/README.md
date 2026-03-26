# Data Storage Structure

## Recommended Directory Structure

This structure separates the "Source of Truth" (the CSVs) from the "Public View" (the Plots/Markdown).

```
data-storage/ (data branch)
└── results/
    ├── raw/                          # One CSV per run
    │   └── .gitkeep                  # Placeholder directory
    ├── plots/                        # Visuals generated from ALL files in raw/
    │   ├── amortized_ai_cost.png
    │   ├── amortized_ai_cost_categorize_emails.png
    │   └── amortized_ai_cost_extract_email_templates.png
    └── latest_summary.md             # High-level report (to be created)
```

## Directory Usage

### `raw/`
- **Purpose**: Source of truth for benchmark data
- **Contents**: One CSV file per benchmark run
- **Naming convention**: `benchmark_v{version}_{date}.csv`
- **Example**: `benchmark_v1.0.0_20240308.csv`

### `plots/`
- **Purpose**: Generated visualizations from all raw data
- **Contents**: PNG plots showing amortized AI cost analysis
- **Generation**: Automated by analytics scripts
- **Examples**: 
  - `amortized_ai_cost.png` - Overall amortized AI cost analysis
  - `amortized_ai_cost_categorize_emails.png` - Cost analysis for email categorization
  - `amortized_ai_cost_extract_email_templates.png` - Cost analysis for email template extraction

### `latest_summary.md`
- **Purpose**: High-level executive summary
- **Contents**: Key metrics and insights from all benchmark runs
- **Generation**: Automatically updated when new data is available
- **Audience**: Stakeholders who need quick overview

## Data Flow

1. **Raw Data Collection**: CSV files are generated and stored in `raw/`
2. **Analysis**: Analytics scripts process all files in `raw/`
3. **Visualization**: Plots are generated and saved to `plots/`
4. **Reporting**: Summary is updated in `latest_summary.md`

## Best Practices

- Never manually edit files in `plots/` - they are generated
- Always follow the naming convention for CSV files in `raw/`
- Use version numbers that reflect semantic versioning
- Include dates in YYYYMMDD format for proper chronological ordering
