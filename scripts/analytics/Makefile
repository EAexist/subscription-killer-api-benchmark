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

test:
	@echo "Running tests..."
	@$(PYTHON) -c "import os; [exec(line.strip()) for line in open('.env.test') if line.strip() and not line.startswith('#')]" && $(PYTHON) -m pytest tests/ $(MARKER_FILTER) $(ARGS) -s --log-cli-level=DEBUG

clean:
	@echo "Cleaning environment..."
	rmdir /s /q $(VENV)
	for /d /r . %%d in (__pycache__) do @rmdir /s /q "%%d"