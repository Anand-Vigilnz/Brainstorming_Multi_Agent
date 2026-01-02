# Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (including curl for health checks)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management (optional but recommended)
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install Python dependencies using uv
RUN uv pip install --system -e .

# Alternative: If not using uv, uncomment below and comment above
# COPY pyproject.toml ./
# RUN pip install --no-cache-dir -e .

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose ports (will be overridden in docker-compose)
EXPOSE 9991 9992 9993 9999 8501

# Default command (will be overridden in docker-compose)
CMD ["python", "--version"]