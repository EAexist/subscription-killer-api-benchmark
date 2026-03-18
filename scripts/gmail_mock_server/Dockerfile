FROM python:3.11-slim

WORKDIR /app

# 1. Install dependencies
COPY scripts/gmail_mock_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy the dataset
# COPY scripts/gmail_mock_server/dataset ./dataset

# 3. Copy EVERYTHING from the project folder
# This picks up models.py, config.py, state.py, mock_server.py, etc.
COPY scripts/gmail_mock_server/*.py ./
COPY scripts/gmail_mock_server/services ./services
COPY scripts/gmail_mock_server/utils ./utils

# 4. Set PYTHONPATH
ENV DATASET_PATH="/app/dataset"
ENV PYTHONPATH="/app:/app/dataset/src"

EXPOSE 8080

CMD ["python", "mock_server.py"]