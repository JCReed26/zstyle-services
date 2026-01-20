# ZStyle Services - Development Commands
# Usage: make <command>

.PHONY: help dev test test-unit test-integration lint format clean docker-up docker-down docker-logs docker-rebuild install setup

# Default target
help:
	@echo "ZStyle Services - Development Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start development server with hot reload"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up    - Start all services (docker-compose up)"
	@echo "  make docker-down  - Stop all services"
	@echo "  make docker-logs   - View logs (follow mode)"
	@echo "  make docker-rebuild - Rebuild and restart"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean        - Clean Python cache files"
	@echo "  make install      - Install dependencies"
	@echo "  make setup        - Initial setup (copy .env.example)"

# Development
dev:
	@echo "Starting development server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Docker
docker-up:
	@echo "Starting Docker services..."
	docker-compose up --build

docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

docker-logs:
	@echo "Viewing Docker logs..."
	docker-compose logs -f

docker-rebuild:
	@echo "Rebuilding Docker services..."
	docker-compose down
	docker-compose up --build

# Utilities
clean:
	@echo "Cleaning cache files..."
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

setup:
	@echo "...Setting up project..."
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "Created .env file - please configure it"; \
	else \
		echo ".env file already exists"; \
	fi
