#!/bin/bash
# A simple script to cleanup and dcup with clean builds

echo "starting docker compose take down and rebuild"
docker-compose down
docker-compose build --no-cache

echo "starting docker compose container"
docker-compose up