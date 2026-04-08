.PHONY: setup clean test-analytics test-run test-run-real-tracing

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
	$(PYTHON) -m pip install --upgrade pip
	
MARKER_FILTER ?= -m "not integration"

test:
	@echo "🔍 Running tests..."
	@$(PYTHON) -c "import os; [exec(line.strip()) for line in open('.env.test') if line.strip() and not line.startswith('#')]" && $(PYTHON) -m pytest tests/ $(MARKER_FILTER) $(ARGS) -s --log-cli-level=DEBUG

test-run: $(SENTINEL)
	@echo "🚀 Running Langfuse exporter locally..."
	@echo "📋 Using default arguments with monitoring..."
	@bash -c 'export LANGFUSE_HOST=http://localhost:3000 \
		LANGFUSE_PUBLIC_KEY=pk-lf-12345 \
		LANGFUSE_SECRET_KEY=sk-lf-12345 \
		AI_BENCHMARK_K6_ITERATIONS=10 \
		DATA_STORAGE_ROOT=../../data-storage \
		PYTHONIOENCODING=utf-8; \
		touch test_output.log; \
		$(PYTHON) -m main --app-version "test-version" --run-id "test-run-$$(date +%s)" > test_output.log 2>&1 & \
		PID=$$!; \
		trap "kill $$PID 2>/dev/null; wait $$PID 2>/dev/null; rm -f test_output.log" EXIT; \
		tail -f test_output.log | while IFS= read -r line; do \
			echo "$$line"; \
			if echo "$$line" | grep -q "status_code: 500.*body: Internal Server Error"; then \
				echo "----------------------------------------------------------"; \
				echo "✅ SUCCESS: Expected connectivity error caught."; \
				echo "Langfuse server not available - test completed successfully."; \
				echo "----------------------------------------------------------"; \
				exit 0; \
			fi; \
		done'

test-run-real-tracing: $(SENTINEL)
	@echo "🚀 Running Langfuse exporter with real tracing..."
	@echo "📋 Using provided arguments: run-id=$(run-id), app-version=$(app-version)"
	@bash -c 'export DATA_STORAGE_ROOT=../../data-storage \
		PYTHONIOENCODING=utf-8 \
		LOG_LEVEL=DEBUG; \
		$(PYTHON) -m main --app-version "$(app-version)" --run-id "$(run-id)"'

clean:
	@echo "Cleaning environment..."
	rmdir /s /q $(VENV)
	for /d /r . %%d in (__pycache__) do @rmdir /s /q "%%d"