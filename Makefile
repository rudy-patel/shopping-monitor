# Shopping Monitor — Development Makefile
# Run `make help` to see available commands

.PHONY: help start stop restart status logs health test test-backend test-frontend test-integration test-e2e test-all clean install-deps setup benchmark-retailers update-drift-snapshots check-retailer-drift

help:
	@echo "🛒 Shopping Monitor — development commands"
	@echo "=========================================="
	@echo ""
	@echo "Server Management:"
	@echo "  make start     - Start both backend and frontend servers"
	@echo "  make stop      - Stop all running servers"
	@echo "  make restart   - Restart all servers"
	@echo "  make status    - Show current server status"
	@echo "  make logs      - Show logs for both servers"
	@echo "  make health    - Check server health"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run unit tests (backend + frontend)"
	@echo "  make test-backend   - Run backend unit tests only"
	@echo "  make test-frontend  - Run frontend tests"
	@echo "  make setup-integration-env - Write backend/.env from Supabase secrets"
	@echo "  make test-integration - Run integration tests (requires Supabase)"
	@echo "  make test-e2e       - Run Playwright e2e tests (auto-starts servers)"
	@echo "  make test-all       - Run all tests including integration"
	@echo "  make benchmark-retailers - Regenerate fixture benchmark report (T5.1)"
	@echo "  make update-drift-snapshots - Regenerate drift baselines from fixtures (T5.5)"
	@echo "  make check-retailer-drift - Live drift check (SCRAPER_MODE=live; hits retailers)"
	@echo ""
	@echo "Development:"
	@echo "  make clean     - Clean up logs and cache files"
	@echo "  make install   - Install all dependencies"
	@echo "  make setup     - Full development environment setup"
	@echo ""
	@echo "Shortcuts:"
	@echo "  make dev       - Alias for make start"
	@echo "  make s         - Alias for make status"

start: dev
dev:
	@echo "🚀 Starting development servers..."
	./dev-servers.sh start

stop:
	@echo "🛑 Stopping development servers..."
	./dev-servers.sh stop

restart:
	@echo "🔄 Restarting development servers..."
	./dev-servers.sh restart

status: s
s:
	@echo "📊 Server status:"
	./dev-servers.sh status

logs:
	@echo "📄 Backend logs (last 20 lines):"
	@./dev-servers.sh logs backend
	@echo ""
	@echo "📄 Frontend logs (last 20 lines):"
	@./dev-servers.sh logs frontend

health:
	@echo "🏥 Health check:"
	./dev-servers.sh health

test: test-backend test-frontend

test-backend:
	@echo "🔧 Running backend unit tests..."
	@if [ -d "backend/venv" ]; then \
		cd backend && . venv/bin/activate && python -m pytest test/ -v --tb=short -m "not integration"; \
	else \
		cd backend && python3 -m pytest test/ -v --tb=short -m "not integration"; \
	fi

test-frontend:
	@echo "🎨 Running frontend tests..."
	@cd frontend && npm run test:run

setup-integration-env:
	@echo "🔐 Syncing backend/.env for integration tests..."
	@python scripts/setup_integration_env.py

test-integration: setup-integration-env
	@echo "🔗 Running integration tests (requires Supabase)..."
	@if [ -d "backend/venv" ]; then \
		cd backend && . venv/bin/activate && REQUIRE_INTEGRATION_ENV=1 python -m pytest test/ -v -m "integration"; \
	else \
		cd backend && REQUIRE_INTEGRATION_ENV=1 python3 -m pytest test/ -v -m "integration"; \
	fi

test-e2e:
	@echo "🎭 Running Playwright e2e tests (auto-starts backend :8000 and frontend :3000)..."
	@cd frontend && PLAYWRIGHT_API_URL=http://localhost:8000 npx playwright test

test-all: test test-integration
	@echo "✅ All tests completed!"

benchmark-retailers:
	@echo "📊 Running fixture-mode retailer benchmark..."
	@cd backend && . venv/bin/activate && SCRAPER_MODE=fixtures python ../scripts/run_scraper_benchmark.py \
		--out ../docs/benchmarks/fixtures-$$(date +%Y-%m-%d).json

update-drift-snapshots:
	@echo "🧭 Regenerating drift baselines from fixtures..."
	@cd backend && . venv/bin/activate && SCRAPER_MODE=fixtures python ../scripts/update_drift_snapshots.py

check-retailer-drift:
	@echo "🔍 Running live retailer drift check (outbound requests; not for CI)..."
	@cd backend && . venv/bin/activate && SCRAPER_MODE=live python ../scripts/check_retailer_drift.py --no-issues

install: install-deps

install-deps:
	@echo "📦 Installing backend dependencies..."
	@if [ ! -d "backend/venv" ]; then \
		echo "Creating virtual environment..."; \
		cd backend && python3 -m venv venv; \
	fi
	@cd backend && . venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
	@echo "📦 Installing frontend dependencies..."
	@cd frontend && npm install

setup: install
	@echo "✅ Development environment setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy backend/.env.example → backend/.env and frontend/.env.example → frontend/.env"
	@echo "  2. make start    - Start the development servers"
	@echo "  3. Visit http://localhost:3000"

clean:
	@echo "🧹 Cleaning up..."
	@rm -rf logs/
	@rm -rf backend/__pycache__/
	@rm -rf frontend/node_modules/.cache/
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

check-env:
	@echo "🔍 Checking development environment..."
	@if [ ! -d "backend" ] || [ ! -d "frontend" ]; then \
		echo "❌ Error: Please run from project root directory"; \
		exit 1; \
	fi
	@if ! command -v python3 &> /dev/null; then \
		echo "❌ Python3 not found"; \
		exit 1; \
	fi
	@if ! command -v node &> /dev/null; then \
		echo "❌ Node.js not found"; \
		exit 1; \
	fi
	@if ! command -v npm &> /dev/null; then \
		echo "❌ npm not found"; \
		exit 1; \
	fi
	@echo "✅ Environment looks good!"

quick-start: check-env start
