# Use a suitable Python base image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy your requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

EXPOSE 8000

# Command to run your application with Gunicorn (single worker for WebSocket support)
# Use single worker with Gunicorn for WebSocket compatibility
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "120", "main:app", "--bind", "0.0.0.0:8000"]
