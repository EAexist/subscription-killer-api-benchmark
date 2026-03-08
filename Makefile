.PHONY: setup clean

VENV = .venv
PIP = $(VENV)/Scripts/pip
SENTINEL = $(VENV)/Scripts/activate

setup: $(SENTINEL)
	@echo "Updating dependencies from requirements.txt..."
	$(PIP) install -r requirements.txt
	@echo "✅ Environment is up to date."

$(SENTINEL):
	@echo "Creating virtual environment..."
	py -m venv $(VENV)
	$(PIP) install --upgrade pip

clean:
	rm -rf $(VENV)

# Langufes Analytics
setup-analytics:
	$(MAKE) -C scripts/langfuse_analytics setup

test-analytics:
	$(MAKE) -C scripts/langfuse_analytics test-analytics