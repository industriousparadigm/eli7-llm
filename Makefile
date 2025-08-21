.PHONY: help build up down logs test clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

build: ## Build all Docker images
	docker compose build

up: ## Start all services
	docker compose up

up-d: ## Start all services in detached mode
	docker compose up -d

down: ## Stop all services
	docker compose down

logs: ## Show logs from all services
	docker compose logs -f

logs-api: ## Show API logs
	docker compose logs -f api

logs-ui: ## Show UI logs
	docker compose logs -f ui

logs-ollama: ## Show Ollama logs
	docker compose logs -f ollama

test-smoke: ## Run smoke tests
	./tests/smoke_test.sh

test-e2e: ## Run E2E tests
	cd ui && npm install && npm run test

test: test-smoke ## Run all tests

shell-api: ## Open shell in API container
	docker compose exec api /bin/bash

shell-ui: ## Open shell in UI container
	docker compose exec ui /bin/sh

pull-model: ## Manually pull Ollama model
	docker compose exec ollama ollama pull phi3:mini

clean: ## Clean up containers and volumes
	docker compose down -v

restart: down up ## Restart all services

dev: ## Start development environment
	@echo "Starting development environment..."
	@cp -n .env.example .env || true
	docker compose up