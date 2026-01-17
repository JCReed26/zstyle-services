# ZStyle Services - Development Commands
# Usage: make <command>

.PHONY: help dev test test-unit test-integration lint format clean docker-up docker-down docker-logs docker-rebuild install setup

# Default target
help:
	@echo "ZStyle Services - Development Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start development server with hot reload"
	@echo "  make test         - Run all tests"
	@echo "  make test-unit    - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make lint         - Run linters (ruff, mypy)"
	@echo "  make format       - Format code (ruff format)"
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
	@echo "🚀 Starting development server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Testing
test:
	@echo "🧪 Running all tests..."
	pytest tests/ -v

test-unit:
	@echo "🧪 Running unit tests..."
	pytest tests/unit/ -v

test-integration:
	@echo "🧪 Running integration tests..."
	pytest tests/integration/ -v

# Code Quality
lint:
	@echo "🔍 Running linters..."
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check .; \
	else \
		echo "⚠️  ruff not installed, skipping..."; \
	fi
	@if command -v mypy >/dev/null 2>&1; then \
		mypy . --ignore-missing-imports || true; \
	else \
		echo "⚠️  mypy not installed, skipping..."; \
	fi

format:
	@echo "✨ Formatting code..."
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format .; \
		ruff check --fix .; \
	else \
		echo "⚠️  ruff not installed, install with: pip install ruff"; \
	fi

# Docker
docker-up:
	@echo "🐳 Starting Docker services..."
	docker-compose up --build

docker-down:
	@echo "🐳 Stopping Docker services..."
	docker-compose down

docker-logs:
	@echo "📋 Viewing Docker logs..."
	docker-compose logs -f

docker-rebuild:
	@echo "🔨 Rebuilding Docker services..."
	docker-compose down
	docker-compose up --build

# Utilities
clean:
	@echo "🧹 Cleaning cache files..."
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true

install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

setup:
	@echo "⚙️  Setting up project..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env file - please configure it"; \
	else \
		echo "ℹ️  .env file already exists"; \
	fi
