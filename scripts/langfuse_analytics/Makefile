.PHONY: setup clean test-analytics

VENV = .venv
# On Windows, binaries are in /Scripts/
PYTHON = $(VENV)/Scripts/python
PIP = $(VENV)/Scripts/pip
SENTINEL = $(VENV)/Scripts/activate

setup: $(SENTINEL)
	@echo "Updating dependencies..."
	$(PIP) install -r requirements.txt
	@echo "✅ Setup complete."

$(SENTINEL):
	@echo "Creating virtual environment..."
	py -3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	
MARKER_FILTER ?= -m "not integration"

test-analytics:
	@echo "Running tests..."
	$(PYTHON) -m pytest tests/ $(MARKER_FILTER) $(ARGS) -s

clean:
	@echo "Cleaning environment..."
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +