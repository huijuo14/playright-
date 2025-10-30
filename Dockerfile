FROM mcr.microsoft.com/playwright/python:v1.56.1-jammy

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /root/.mozilla/firefox

# Start the application
CMD ["python", "app.py"]
