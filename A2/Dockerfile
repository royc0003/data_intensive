FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables with local defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DB_HOST=host.docker.internal \
    DB_USER=root \
    DB_PASSWORD=password \
    DB_NAME=Bookstore

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libmariadb3 \
        libmariadb-dev \
        build-essential \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy and make the entrypoint script executable
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Expose port 80
EXPOSE 80

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Use the entrypoint script
ENTRYPOINT ["./docker-entrypoint.sh"] 