# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies if needed (e.g., gcc for some pandas extensions)
# RUN apt-get update && apt-get install -y gcc

COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --- Stage 2: Final Runtime ---
FROM python:3.12-slim
WORKDIR /app

# Prevent Python from buffering and creating .pyc files
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Ensure the virtualenv is used
ENV PATH="/opt/venv/bin:$PATH"

# Copy the virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

# Copy your script logic
COPY . .

# No need to specify the path to python, it's in the VENV path now
CMD ["python", "main.py"]