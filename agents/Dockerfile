# Use official Python image
FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 4312
EXPOSE 4312

# Run FastAPI using uvicorn
CMD ["python3", "./multimodal_api.py"]
