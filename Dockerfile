FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

# Install system dependencies
ENV PYTHONUNBUFFERED=1 \
    PORT=8080

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure Playwright Chromium browser is installed
RUN playwright install chromium

# Copy application files
COPY . .

# Expose port (Cloud Run sets PORT env var)
EXPOSE 8080

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
