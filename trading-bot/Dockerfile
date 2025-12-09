# Trading Bot Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd --create-home --shell /bin/bash trader && \
    chown -R trader:trader /app
USER trader

# Copy source code
COPY --chown=trader:trader . .

# Create directories for logs and data
RUN mkdir -p logs data

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import os; exit(0 if os.path.exists('/tmp/bot_health') else 1)" || exit 1

# Default command - can be overridden
CMD ["python", "start.py"]