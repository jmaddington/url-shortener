# Use Python 3.10 slim image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production

# Create and set working directory
WORKDIR /app

# Install system dependencies required for python3-saml
RUN apt-get update && apt-get install -y \
    git \
    libxml2-dev \
    libxmlsec1-dev \
    libxmlsec1-openssl \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create uploads directory with proper permissions
RUN mkdir -p uploads && \
    chmod 755 uploads

# Create directory for SQLite database
RUN mkdir -p data && \
    chmod 755 data

# Create directory for SAML settings
RUN mkdir -p saml && \
    chmod 755 saml

# Create directory for session files
RUN mkdir -p flask_session && \
    chmod 755 flask_session

# Create a non-root user
RUN useradd -m appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--timeout", "120", "app:app"]