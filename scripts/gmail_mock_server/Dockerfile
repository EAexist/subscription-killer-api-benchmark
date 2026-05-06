# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

WORKDIR /build

# Install git only in the builder
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# 1. STOP THE "PACKFILE" ERROR: Disable partial clones globally in this stage
# This prevents pip from adding --filter=blob:none to the git command
RUN git config --global core.partialclonefilter ""

# 2. SKIP THE DATASET: Ensure LFS doesn't download the heavy blobs
ENV GIT_LFS_SKIP_SMUDGE=1
RUN git clone --depth 1 https://huggingface.co/datasets/hyeon-expression/subscription-killer-synthetic-emails /shared_repo

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --user -r requirements.txt
RUN pip install --user /shared_repo

# --- Stage 2: Final Runtime ---
FROM python:3.12-slim
WORKDIR /app

# Prevent Python from buffering
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:${PATH}"
ENV PYTHONPATH="/root/.local/lib/python3.12/site-packages"

# Copy only the installed packages from the builder
COPY --from=builder /root/.local /root/.local
COPY . .

CMD ["python", "mock_server.py"]