# Use a suitable Python base image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy your requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

EXPOSE 8080

# Command to run your application with Uvicorn
# Replace 'main:app' with the actual module and ASGI app instance path
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$PORT"]
