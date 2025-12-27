#!/bin/bash
set -e

# Ensure data directory exists and is writable
mkdir -p /app/data
chmod 777 /app/data

# Execute the main command
exec "$@"

