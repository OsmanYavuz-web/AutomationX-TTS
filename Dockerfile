# Base image
FROM python:3.10-slim

# Install system dependencies
# ffmpeg is required for audio processing (torchaudio, pydub etc)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir to keep image small
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 7777

# Environment variables (defaults)
ENV PORT=7777
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "app.py"]
