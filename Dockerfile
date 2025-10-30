# Use Ubuntu Noble (24.04) as base for stability
FROM ubuntu:24.04

# Set non-interactive mode for apt
ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.12 + pip + essentials
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3-pip \
    wget \
    curl \
    unzip \
    xvfb \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.12 as default
RUN ln -s /usr/bin/python3.12 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip

# Download and extract Playwright v1.56.1 from GitHub tarball
WORKDIR /tmp
RUN wget https://github.com/microsoft/playwright/archive/refs/tags/v1.56.1.tar.gz && \
    tar -xzf v1.56.1.tar.gz && \
    cd playwright-1.56.1 && \
    pip install . --no-cache-dir

# Install Playwright browsers (this pulls Firefox 142.0.1, Chromium 141, WebKit 26)
RUN playwright install --with-deps firefox chromium webkit

# Create app directory
WORKDIR /app

# Copy your script (and any other files)
COPY . .

# Install any additional Python deps (if you have requirements.txt)
# RUN pip install requests beautifulsoup4 pytz urllib3

# Expose port if needed (e.g., for Telegram bot)
EXPOSE 8080

# Run your monitor script
CMD ["python", "monitor.py"]
