.PHONY: test build docker-build docker-run compose-up compose-down

# ==============================================================================
# General Commands
# ==============================================================================

test:
	@echo "Running tests..."
	@PYTHONPATH=. pytest

# ==============================================================================
# Docker Commands
# ==============================================================================

build:
	@echo "Building Docker image..."
	@docker build -t fib-api .

run:
	@echo "Running Docker container..."
	@docker run -p 8000:8000 fib-api

compose-up:
	@echo "Starting services with Docker Compose..."
	@docker-compose up -d

compose-build:
	@echo "Building and starting services with Docker Compose..."
	@docker-compose up -d --build

compose-down:
	@echo "Stopping services..."
	@docker-compose down 