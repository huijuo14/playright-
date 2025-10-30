FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# Install Firefox 144.0 manually (latest stable)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    libgtk-3-0 \
    libnss3 \
    libxss1 \
    libasound2 \
    libdbus-glib-1-2 \
    && rm -rf /var/lib/apt/lists/*

# Download and install Firefox 144.0
RUN wget -O /tmp/firefox.tar.bz2 "https://download-installer.cdn.mozilla.net/pub/firefox/releases/144.0/linux-x86_64/en-US/firefox-144.0.tar.bz2" \
    && tar -xjf /tmp/firefox.tar.bz2 -C /opt \
    && ln -sf /opt/firefox/firefox /usr/local/bin/firefox \
    && rm /tmp/firefox.tar.bz2

# Verify Firefox installation
RUN firefox --version

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /root/.mozilla/firefox

# Start the application
CMD ["python", "app.py"]
