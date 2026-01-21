# ZStyle Services - Development Commands
# Usage: make <command>

.PHONY: help dev test test-unit test-integration lint format clean docker-up docker-down docker-logs docker-rebuild install setup ngrok-start ngrok-stop ngrok-status ngrok-url ngrok-restart-app

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
	docker-compose up -d --build

docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

docker-logs:
	@echo "Viewing Docker logs..."
	docker-compose logs -f

docker-rebuild:
	@echo "Rebuilding Docker services..."
	docker-compose down
	docker-compose up -d --build

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

# Ngrok commands
ngrok-start:
	@echo "Starting ngrok tunnel..."
	@./scripts/start-ngrok.sh 8000

ngrok-stop:
	@pkill ngrok || echo "No ngrok process found"

ngrok-status:
	@curl -s http://localhost:4040/api/tunnels 2>/dev/null | python3 -m json.tool || echo "Ngrok not running"

ngrok-url:
	@curl -s http://localhost:4040/api/tunnels 2>/dev/null | \
		python3 -c "import sys, json; \
		data = json.load(sys.stdin); \
		tunnels = data.get('tunnels', []); \
		https_tunnel = next((t for t in tunnels if t.get('proto') == 'https'), None); \
		print(https_tunnel['public_url'] if https_tunnel else 'Ngrok not running')" || \
		echo "Ngrok not running"

# Restart app after ngrok URL changes
ngrok-restart-app:
	@echo "Restarting application to load new OAUTH_BASE_URL..."
	@docker-compose restart app
	@echo "✅ Application restarted"
