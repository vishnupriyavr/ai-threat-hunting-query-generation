# Use a Python base image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project context into the container
COPY . .

# Set environment variables for Python buffering
ENV PYTHONUNBUFFERED=1

# Expose ports for Streamlit (8501) and potentially MCP servers (5001, 5002)
# These will be explicitly mapped in docker-compose.yml
EXPOSE 8501