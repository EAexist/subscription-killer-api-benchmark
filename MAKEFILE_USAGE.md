# Makefile Usage

## Setup
```bash
make setup                 # Setup project environment
make setup-analytics       # Setup langfuse analytics environment
```

## Testing
```bash
make test-analytics               # Run unit tests (default)
make test-analytics MARKER_FILTER="-m integration"    # Run only integration tests
make test-analytics MARKER_FILTER=""                  # Run all tests
make test-analytics ARGS="-k test_name"               # Run specific test
```

## Cleanup
```bash
make clean                 # Clean project environment
```

## Examples
```bash
# Run only integration tests
make test-analytics MARKER_FILTER="-m integration"

# Run specific test with verbose output
make test-analytics ARGS="-k test_plot_cost_convergence -v -s"

# Run all tests
make test-analytics MARKER_FILTER=""
```
