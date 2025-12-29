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

# Install Cloud SQL Proxy for local development/testing
# (Not needed for Cloud Run, but useful for local Cloud SQL connections)
RUN apt-get update && apt-get install -y wget && \
    wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O /usr/local/bin/cloud_sql_proxy && \
    chmod +x /usr/local/bin/cloud_sql_proxy && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/data && chmod 777 /app/data
# Patch openmemory-py package bug: BaseMessage not defined in except ImportError block
COPY fix_openmemory.sh .
RUN chmod +x fix_openmemory.sh && python3 fix_openmemory.sh

# Copy the rest of the application
COPY . .

# Copy entrypoint script and make it executable
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 8000

# Set entrypoint to ensure data directory permissions
ENTRYPOINT ["/entrypoint.sh"]

# Run the application
# Use PORT env var (Cloud Run sets this)
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]

