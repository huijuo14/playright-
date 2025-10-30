FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    tar \
    xz-utils \
    libgtk-3-0 \
    libnss3 \
    libxss1 \
    libasound2 \
    libxtst6 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Download and install Firefox 144.0
RUN wget https://ftp.mozilla.org/pub/firefox/releases/144.0/linux-x86_64/en-US/firefox-144.0.tar.xz \
    && tar -xf firefox-144.0.tar.xz -C /opt \
    && ln -sf /opt/firefox/firefox /usr/local/bin/firefox \
    && rm firefox-144.0.tar.xz

# Verify Firefox installation
RUN firefox --version

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
