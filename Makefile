.PHONY: help setup start stop restart logs clean test lint

help:
	@echo "ORIGIN Learning Platform - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Initial project setup"
	@echo "  make install        - Install all dependencies"
	@echo ""
	@echo "Docker:"
	@echo "  make start          - Start all services"
	@echo "  make stop           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View service logs"
	@echo "  make clean          - Remove containers and volumes"
	@echo ""
	@echo "Database:"
	@echo "  make migrate        - Run database migrations"
	@echo "  make migration      - Create new migration"
	@echo "  make db-shell       - Open PostgreSQL shell"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-backend   - Run backend tests"
	@echo "  make test-mobile    - Run mobile tests"
	@echo "  make coverage       - Generate coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint           - Run linters"
	@echo "  make format         - Format code"
	@echo "  make type-check     - Run type checkers"

setup:
	@echo "Setting up ORIGIN Learning Platform..."
	cp backend/.env.example backend/.env
	cp mobile/.env.example mobile/.env
	@echo "Please edit backend/.env and mobile/.env with your configuration"

install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing mobile dependencies..."
	cd mobile && npm install

start:
	docker-compose up -d
	@echo "Services started. API available at http://localhost:8000"

stop:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	rm -rf backend/__pycache__ backend/.pytest_cache backend/htmlcov
	rm -rf mobile/node_modules mobile/coverage

migrate:
	docker-compose exec backend alembic upgrade head

migration:
	@read -p "Enter migration message: " msg; \
	docker-compose exec backend alembic revision --autogenerate -m "$$msg"

db-shell:
	docker-compose exec postgres psql -U origin -d origin_db

test:
	@echo "Running backend tests..."
	cd backend && pytest
	@echo "Running mobile tests..."
	cd mobile && npm test

test-backend:
	cd backend && pytest

test-mobile:
	cd mobile && npm test

coverage:
	cd backend && pytest --cov=app --cov-report=html
	@echo "Coverage report generated in backend/htmlcov/index.html"

lint:
	@echo "Linting backend..."
	cd backend && flake8 app/
	@echo "Linting mobile..."
	cd mobile && npm run lint

format:
	@echo "Formatting backend..."
	cd backend && black app/
	@echo "Formatting mobile..."
	cd mobile && npm run lint -- --fix

type-check:
	@echo "Type checking backend..."
	cd backend && mypy app/
	@echo "Type checking mobile..."
	cd mobile && npm run type-check
