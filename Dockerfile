# Base image with Python 3.11
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=10000 \
    GUNICORN_CMD_ARGS="--bind=0.0.0.0:10000 --workers=2 --threads=4 --timeout=120"

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose port
EXPOSE 10000

# Start command
CMD ["gunicorn", "app:app"]
