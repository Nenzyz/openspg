# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency files
COPY pyproject.toml ./

# Configure Poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root --no-dev

# Copy application code
COPY graphspg/ ./graphspg/
COPY examples/ ./examples/

# Expose API port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "graphspg.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
