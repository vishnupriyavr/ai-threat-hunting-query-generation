# Use a Python base image
FROM python:3.12-slim-bookworm

# Set the working directory in the container
WORKDIR /app

ENV PYTHONPATH="/app"

# Create the virtual environment
RUN python -m venv /opt/venv

# 2. Set the PATH so that 'python' and 'pip' refer to the venv versions
ENV PATH="/opt/venv/bin:$PATH"

# Install system dependencies (for building duckdb/pandas if needed)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into the venv
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the entire project context into the container
COPY . .

# Set environment variables for Python buffering
ENV PYTHONUNBUFFERED=1
