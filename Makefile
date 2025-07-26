# Makefile for Social Media Publisher with Intelligent Cropping
# Usage: make [target]

.PHONY: help build start stop restart status logs test clean sam

# Default target
.DEFAULT_GOAL := help

# Variables
COMPOSE_FILE := docker-compose.yaml
PROJECT_NAME := social-media-publisher

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
RED := \033[0;31m
NC := \033[0m # No Color

## Help target
help: ## Show this help message
	@echo "$(BLUE)Social Media Publisher with Intelligent Cropping$(NC)"
	@echo "$(BLUE)=====================================================$(NC)"
	@echo ""
	@echo "Available targets:"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make start          # Start all services"
	@echo "  make logs-api       # Show API logs"
	@echo "  make test-crop      # Test intelligent cropping"
	@echo "  make sam-download   # Download SAM models"

## Build and deployment targets
build: ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose -f $(COMPOSE_FILE) build

start: ## Start all services
	@echo "$(BLUE)Starting all services...$(NC)"
	./deploy.sh start

stop: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down

restart: ## Restart all services
	@echo "$(BLUE)Restarting all services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) restart

## Status and monitoring targets
status: ## Show service status
	@echo "$(BLUE)Service Status:$(NC)"
	docker-compose -f $(COMPOSE_FILE) ps

health: ## Check health of all services
	@echo "$(BLUE)Health Check:$(NC)"
	@curl -sf http://localhost:8090/health || echo "$(RED)API not responding$(NC)"
	@curl -sf http://localhost:8090/crop/status || echo "$(RED)Crop system not responding$(NC)"
	@curl -sf http://admin:admin@localhost:5555 || echo "$(RED)Flower not responding$(NC)"

## Logging targets
logs: ## Show logs for all services
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-api: ## Show API logs
	docker-compose -f $(COMPOSE_FILE) logs -f social-media-api

logs-image: ## Show image processing worker logs
	docker-compose -f $(COMPOSE_FILE) logs -f social-media-worker-image

logs-content: ## Show content worker logs
	docker-compose -f $(COMPOSE_FILE) logs -f social-media-worker-content

logs-publishing: ## Show publishing worker logs
	docker-compose -f $(COMPOSE_FILE) logs -f social-media-worker-publishing

logs-redis: ## Show Redis logs
	docker-compose -f $(COMPOSE_FILE) logs -f social-media-redis

## Testing targets
test: ## Test the deployment
	@echo "$(BLUE)Testing deployment...$(NC)"
	./deploy.sh test

test-crop: ## Test intelligent cropping system
	@echo "$(BLUE)Testing intelligent cropping...$(NC)"
	docker-compose -f $(COMPOSE_FILE) exec social-media-api python test_crop_system.py

test-api: ## Test API endpoints
	@echo "$(BLUE)Testing API endpoints...$(NC)"
	@curl -sf http://localhost:8090/health && echo "$(GREEN)✅ Health OK$(NC)" || echo "$(RED)❌ Health failed$(NC)"
	@curl -sf http://localhost:8090/crop/status && echo "$(GREEN)✅ Crop status OK$(NC)" || echo "$(RED)❌ Crop status failed$(NC)"
	@curl -sf http://localhost:8090/crop/recommendations && echo "$(GREEN)✅ Recommendations OK$(NC)" || echo "$(RED)❌ Recommendations failed$(NC)"

## SAM (Intelligent Cropping) targets
sam-download: ## Download SAM checkpoints manually
	@echo "$(BLUE)Downloading SAM checkpoints...$(NC)"
	./deploy.sh sam

sam-status: ## Check SAM configuration
	@echo "$(BLUE)SAM Configuration:$(NC)"
	@curl -sf http://localhost:8090/crop/status | jq '.crop_service_status.unified_cropper' || echo "$(RED)Could not get SAM status$(NC)"

sam-test: ## Test SAM with sample image
	@echo "$(BLUE)Testing SAM with sample image...$(NC)"
	@curl -X POST "http://localhost:8090/images/analyze-smart" \
		-F "s3_url=s3://your-bucket/test-image.jpg" || echo "$(RED)SAM test failed - check S3 URL$(NC)"

## Development targets
shell: ## Open shell in API container
	docker-compose -f $(COMPOSE_FILE) exec social-media-api bash

shell-worker: ## Open shell in image worker container
	docker-compose -f $(COMPOSE_FILE) exec social-media-worker-image bash

redis-cli: ## Connect to Redis CLI
	docker-compose -f $(COMPOSE_FILE) exec social-media-redis redis-cli

db-shell: ## Connect to PostgreSQL
	docker-compose -f $(COMPOSE_FILE) exec social-media-db psql -U social_media_user -d social_media_publisher

## Scaling targets
scale-image: ## Scale image processing workers (usage: make scale-image N=3)
	@echo "$(BLUE)Scaling image workers to $(N)...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d --scale social-media-worker-image=$(N)

scale-content: ## Scale content workers (usage: make scale-content N=2)
	@echo "$(BLUE)Scaling content workers to $(N)...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d --scale social-media-worker-content=$(N)

scale-publishing: ## Scale publishing workers (usage: make scale-publishing N=2)
	@echo "$(BLUE)Scaling publishing workers to $(N)...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d --scale social-media-worker-publishing=$(N)

## Monitoring targets
flower: ## Open Flower monitoring
	@echo "$(BLUE)Opening Flower monitoring...$(NC)"
	@echo "URL: http://localhost:5555"
	@echo "Login: admin:admin"

docs: ## Open API documentation
	@echo "$(BLUE)Opening API documentation...$(NC)"
	@echo "URL: http://localhost:8090/docs"

monitor: ## Show real-time container stats
	docker stats $(shell docker-compose -f $(COMPOSE_FILE) ps -q)

## Cleanup targets
clean: ## Clean up containers and volumes
	@echo "$(YELLOW)Cleaning up containers and volumes...$(NC)"
	./deploy.sh clean

clean-images: ## Remove unused Docker images
	@echo "$(YELLOW)Removing unused Docker images...$(NC)"
	docker image prune -f

clean-volumes: ## Remove unused Docker volumes
	@echo "$(YELLOW)Removing unused Docker volumes...$(NC)"
	docker volume prune -f

clean-all: ## Complete cleanup (containers, images, volumes)
	@echo "$(RED)Complete cleanup - This will remove everything!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo ""; \
		docker-compose -f $(COMPOSE_FILE) down -v; \
		docker system prune -af; \
		echo "$(GREEN)Complete cleanup done$(NC)"; \
	else \
		echo ""; \
		echo "$(BLUE)Cleanup cancelled$(NC)"; \
	fi

## Configuration targets
env-setup: ## Setup .env file from example
	@if [ ! -f .env ]; then \
		echo "$(BLUE)Creating .env from .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(YELLOW)Please edit .env with your credentials$(NC)"; \
	else \
		echo "$(GREEN).env file already exists$(NC)"; \
	fi

env-check: ## Check required environment variables
	@echo "$(BLUE)Checking environment variables...$(NC)"
	@if [ -f .env ]; then \
		echo "$(GREEN)✅ .env file exists$(NC)"; \
		grep -q "ANTHROPIC_API_KEY=" .env && echo "$(GREEN)✅ Claude API key configured$(NC)" || echo "$(RED)❌ Claude API key missing$(NC)"; \
		grep -q "AWS_ACCESS_KEY_ID=" .env && echo "$(GREEN)✅ AWS credentials configured$(NC)" || echo "$(RED)❌ AWS credentials missing$(NC)"; \
		grep -q "SAM_ENABLED=" .env && echo "$(GREEN)✅ SAM configuration found$(NC)" || echo "$(RED)❌ SAM configuration missing$(NC)"; \
	else \
		echo "$(RED)❌ .env file not found$(NC)"; \
	fi

## Quick start targets
quick-start: env-setup build start test ## Complete setup from scratch
	@echo "$(GREEN)🎉 Quick start completed!$(NC)"
	@echo "$(BLUE)Available endpoints:$(NC)"
	@echo "  API: http://localhost:8090"
	@echo "  Docs: http://localhost:8090/docs"
	@echo "  Flower: http://localhost:5555"

demo: ## Start services and run crop demo
	@echo "$(BLUE)Starting demo...$(NC)"
	make start
	sleep 30
	make test-crop
	@echo "$(GREEN)Demo completed! Check logs for results.$(NC)"

## Info targets
info: ## Show system information
	@echo "$(BLUE)System Information:$(NC)"
	@echo "Docker version: $$(docker --version)"
	@echo "Docker Compose version: $$(docker-compose --version 2>/dev/null || docker compose version)"
	@echo "Available disk space: $$(df -h . | tail -1 | awk '{print $$4}')"
	@echo "Available memory: $$(free -h | grep Mem | awk '{print $$7}')"

endpoints: ## Show all available endpoints
	@echo "$(BLUE)Available Endpoints:$(NC)"
	@echo "$(GREEN)Main Services:$(NC)"
	@echo "  🌐 API: http://localhost:8090"
	@echo "  📚 Docs: http://localhost:8090/docs"
	@echo "  🌸 Flower: http://localhost:5555 (admin:admin)"
	@echo ""
	@echo "$(GREEN)Health & Status:$(NC)"
	@echo "  ❤️ Health: http://localhost:8090/health"
	@echo "  🎯 Crop Status: http://localhost:8090/crop/status"
	@echo "  📊 Recommendations: http://localhost:8090/crop/recommendations"
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@echo "  🧪 Crop Test: POST /images/unified-crop"
	@echo "  🔍 Image Analysis: POST /images/analyze-smart"
	@echo "  📝 Examples: GET /examples"

# Example usage with parameters
N := 1