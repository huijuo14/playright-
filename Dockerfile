FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm
ENV DISPLAY=:99

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcomposite1 \
    libx11-xcb1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    xvfb \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install latest Firefox from Mozilla PPA
RUN wget -q -O- https://packages.mozilla.org/apt/mozilla-archive-keyring.gpg | gpg --dearmor | tee /etc/apt/trusted.gpg.d/mozilla.gpg > /dev/null
RUN echo "deb [signed-by=/etc/apt/trusted.gpg.d/mozilla.gpg] https://packages.mozilla.org/apt mozilla main" | tee /etc/apt/sources.list.d/mozilla.list
RUN echo "Package: *\nPin: origin packages.mozilla.org\nPin-Priority: 1000" | tee /etc/apt/preferences.d/mozilla
RUN apt-get update && apt-get install -y firefox && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Playwright with system Firefox
RUN playwright install firefox

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /root/.mozilla/firefox

# Start the application
CMD ["python3", "app.py"]
