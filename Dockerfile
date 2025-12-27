FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# libpq-dev is required for psycopg2/asyncpg building if wheels aren't available
# gcc is often needed for compiling python extensions
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


RUN mkdir -p /app/data && chmod 777 /app/data
# Patch openmemory-py package bug: BaseMessage not defined in except ImportError block
COPY fix_openmemory.sh .
RUN chmod +x fix_openmemory.sh && python3 fix_openmemory.sh

# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

