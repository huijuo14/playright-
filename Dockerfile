FROM mcr.microsoft.com/playwright/python:v1.56.1-noble

WORKDIR /app

# Copy and install deps (includes playwright==1.56.1)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure browsers are installed (matches v1.56.1)
RUN playwright install --with-deps firefox

# Copy code
COPY . .

# Clean any old profiles (prevents conflicts)
RUN rm -rf /root/.mozilla/firefox

CMD ["python", "app.py"]
