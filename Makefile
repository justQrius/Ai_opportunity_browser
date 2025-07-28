.PHONY: help setup dev-up dev-down test lint format clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Set up development environment
	@echo "Setting up development environment..."
	@python -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  source venv/bin/activate  (Linux/Mac)"
	@echo "  venv\\Scripts\\activate     (Windows)"
	@echo "Then run: pip install -r requirements.txt"

dev-up: ## Start development environment with Docker
	@echo "Starting development environment..."
	@docker-compose up -d postgres redis
	@echo "Databases started. Run 'make dev-api' to start the API server."

dev-api: ## Start API server using Docker (requires databases to be running)
	@echo "Starting API server with Docker..."
	@docker-compose up api

dev-api-local: ## Start API server using local venv (requires databases to be running)
	@echo "Starting API server with local Python..."
	@if [ ! -d "venv" ]; then echo "Virtual environment not found. Run 'make setup' first."; exit 1; fi
	@echo "Activating virtual environment and starting server..."
	@bash -c "source venv/bin/activate && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"

dev-frontend: ## Start frontend development server
	@echo "Starting frontend development server..."
	@if [ ! -d "ui/node_modules" ]; then echo "Frontend dependencies not installed. Run 'cd ui && npm install' first."; exit 1; fi
	@cd ui && npm run dev

dev-down: ## Stop development environment
	@echo "Stopping development environment..."
	@docker-compose down

dev-logs: ## Show logs from all services
	@docker-compose logs -f

test: ## Run tests
	@echo "Running tests..."
	@pytest

test-event-bus: ## Test event bus system (Redis only)
	@echo "Testing event bus system..."
	@python scripts/test_event_bus_system.py

dev-kafka: ## Start development environment with Kafka
	@echo "Starting development environment with Kafka..."
	@docker-compose --profile kafka up -d

test-event-bus-kafka: ## Test event bus system with Kafka
	@echo "Testing event bus system with Kafka..."
	@EVENT_BUS_TYPE=kafka KAFKA_BOOTSTRAP_SERVERS=localhost:9092 python scripts/test_event_bus_system.py

lint: ## Run linting
	@echo "Running linting..."
	@flake8 .
	@mypy .

format: ## Format code
	@echo "Formatting code..."
	@black .

clean: ## Clean up development environment
	@echo "Cleaning up..."
	@docker-compose down -v
	@docker system prune -f