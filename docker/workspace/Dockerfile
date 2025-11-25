# Workspace container for Claude Code execution
FROM python:3.11-slim

# Install common development tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    vim \
    nano \
    build-essential \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install common Python packages
RUN pip install --no-cache-dir \
    requests \
    httpx \
    aiohttp \
    pydantic \
    pytest \
    black \
    ruff \
    mypy

# Create workspace directory
WORKDIR /workspace

# Set environment variables
ENV WORKSPACE_PATH=/workspace
ENV PYTHONUNBUFFERED=1

# Keep container running
CMD ["tail", "-f", "/dev/null"]

