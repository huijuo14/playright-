FROM mcr.microsoft.com/playwright/python:v1.40.0-noble

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt || echo "No requirements.txt"

CMD ["python", "app.py"]
