# ZStyle Services — Non-Docker Build
# Usage: make <target>

.PHONY: help install install-js install-agents dev dev-frontend dev-agents \
        stop stop-agents status logs-agents logs-frontend clean

AGENTS_DIR := agents
FRONTEND_DIR := frontend
AGENT_PORT := 8123
FRONTEND_PORT := 3000

# PID files
AGENT_PID_FILE := /tmp/zstyle-agent.pid
FRONTEND_PID_FILE := /tmp/zstyle-frontend.pid

##@ Help
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup
install: install-js install-agents ## Install all dependencies

install-js: ## Install JS dependencies (pnpm)
	pnpm install

install-agents: ## Install Python dependencies (uv)
	cd $(AGENTS_DIR) && uv sync

##@ Development
dev: ## Start both frontend and agents concurrently
	@$(MAKE) dev-agents &
	@$(MAKE) dev-frontend

dev-frontend: ## Start Next.js frontend on port $(FRONTEND_PORT)
	cd $(FRONTEND_DIR) && pnpm dev

dev-agents: ## Start LangGraph agent server on port $(AGENT_PORT)
	cd $(AGENTS_DIR) && uv run langgraph dev --port $(AGENT_PORT) --no-browser

##@ Background Services
start: ## Start all services in the background
	@$(MAKE) start-agents
	@sleep 5
	@$(MAKE) start-frontend

start-agents: ## Start agent server in the background
	@echo "Starting LangGraph agent server on port $(AGENT_PORT)..."
	@cd $(AGENTS_DIR) && nohup uv run langgraph dev --port $(AGENT_PORT) --no-browser > /tmp/zstyle-agents.log 2>&1 & echo $$! > $(AGENT_PID_FILE)
	@echo "Agent server started (PID: $$(cat $(AGENT_PID_FILE)))"
	@echo "Logs: tail -f /tmp/zstyle-agents.log"

start-frontend: ## Start frontend in the background
	@echo "Starting Next.js frontend on port $(FRONTEND_PORT)..."
	@cd $(FRONTEND_DIR) && nohup pnpm dev > /tmp/zstyle-frontend.log 2>&1 & echo $$! > $(FRONTEND_PID_FILE)
	@echo "Frontend started (PID: $$(cat $(FRONTEND_PID_FILE)))"
	@echo "Logs: tail -f /tmp/zstyle-frontend.log"

stop: stop-agents stop-frontend ## Stop all background services

stop-agents: ## Stop background agent server
	@if [ -f $(AGENT_PID_FILE) ]; then \
		PID=$$(cat $(AGENT_PID_FILE)); \
		echo "Stopping agent server (PID: $$PID)..."; \
		kill $$PID 2>/dev/null || true; \
		rm -f $(AGENT_PID_FILE); \
		echo "Agent server stopped."; \
	else \
		echo "No agent PID file found. Trying port kill..."; \
		kill $$(lsof -ti:$(AGENT_PORT)) 2>/dev/null || true; \
	fi

stop-frontend: ## Stop background frontend
	@if [ -f $(FRONTEND_PID_FILE) ]; then \
		PID=$$(cat $(FRONTEND_PID_FILE)); \
		echo "Stopping frontend (PID: $$PID)..."; \
		kill $$PID 2>/dev/null || true; \
		rm -f $(FRONTEND_PID_FILE); \
		echo "Frontend stopped."; \
	else \
		echo "No frontend PID file found. Trying port kill..."; \
		kill $$(lsof -ti:$(FRONTEND_PORT)) 2>/dev/null || true; \
	fi

##@ Status & Logs
status: ## Check if services are running
	@echo "=== Service Status ==="
	@if curl -s http://localhost:$(AGENT_PORT)/ok > /dev/null 2>&1; then \
		echo "Agent server ($(AGENT_PORT)):   RUNNING"; \
	else \
		echo "Agent server ($(AGENT_PORT)):   STOPPED"; \
	fi
	@if curl -s http://localhost:$(FRONTEND_PORT) > /dev/null 2>&1; then \
		echo "Frontend ($(FRONTEND_PORT)):       RUNNING"; \
	else \
		echo "Frontend ($(FRONTEND_PORT)):       STOPPED"; \
	fi

logs-agents: ## Tail agent server logs
	tail -f /tmp/zstyle-agents.log

logs-frontend: ## Tail frontend logs
	tail -f /tmp/zstyle-frontend.log

##@ Cleanup
clean: stop ## Stop services and clean build artifacts
	rm -rf $(FRONTEND_DIR)/.next
	rm -rf $(FRONTEND_DIR)/node_modules/.cache
	find . -type d -name __pycache__ -not -path './.venv/*' | xargs rm -rf 2>/dev/null || true
	@echo "Cleaned build artifacts."
