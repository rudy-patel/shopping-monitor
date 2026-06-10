#!/bin/bash

# Enhanced Shopping Monitor Development Server Manager
# Features: Health checks, proper process management, logging, graceful shutdown

set -e  # Exit on any error

# Configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000
BACKEND_URL="http://localhost:$BACKEND_PORT"
FRONTEND_URL="http://localhost:$FRONTEND_PORT"
LOG_DIR="$(pwd)/logs"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create log directory
mkdir -p "$LOG_DIR"

# Global PIDs
BACKEND_PID=""
FRONTEND_PID=""

# Kill existing processes on target ports
kill_existing_processes() {
    echo -e "${BLUE}🛑 Killing existing processes on ports $BACKEND_PORT and $FRONTEND_PORT...${NC}"

    # Kill processes using backend port
    local backend_pids=$(lsof -ti:$BACKEND_PORT 2>/dev/null)
    if [ ! -z "$backend_pids" ]; then
        echo -e "${YELLOW}Killing backend processes: $backend_pids${NC}"
        kill -9 $backend_pids 2>/dev/null || true
    fi

    # Kill processes using frontend port
    local frontend_pids=$(lsof -ti:$FRONTEND_PORT 2>/dev/null)
    if [ ! -z "$frontend_pids" ]; then
        echo -e "${YELLOW}Killing frontend processes: $frontend_pids${NC}"
        kill -9 $frontend_pids 2>/dev/null || true
    fi

    # Kill any orphaned uvicorn processes
    local uvicorn_pids=$(pgrep -f uvicorn 2>/dev/null)
    if [ ! -z "$uvicorn_pids" ]; then
        echo -e "${YELLOW}Killing orphaned uvicorn processes: $uvicorn_pids${NC}"
        kill -9 $uvicorn_pids 2>/dev/null || true
    fi

    # Kill any orphaned vite/node dev processes
    local vite_pids=$(pgrep -f "vite\|npm.*dev" 2>/dev/null)
    if [ ! -z "$vite_pids" ]; then
        echo -e "${YELLOW}Killing orphaned vite/dev processes: $vite_pids${NC}"
        kill -9 $vite_pids 2>/dev/null || true
    fi

    # Brief pause to ensure processes are fully terminated
    sleep 2
    echo -e "${GREEN}✅ Process cleanup complete${NC}"
}

# Open frontend in browser
open_frontend() {
    echo -e "${BLUE}🌐 Opening frontend in browser...${NC}"

    # Try multiple methods to open browser
    if command -v open >/dev/null 2>&1; then
        open "$FRONTEND_URL" 2>/dev/null || true
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$FRONTEND_URL" 2>/dev/null || true
    elif command -v start >/dev/null 2>&1; then
        start "$FRONTEND_URL" 2>/dev/null || true
    else
        echo -e "${YELLOW}⚠️  Could not automatically open browser. Please visit: $FRONTEND_URL${NC}"
        return 1
    fi

    echo -e "${GREEN}✅ Browser opened at: $FRONTEND_URL${NC}"
}

# Cleanup function
cleanup() {
    local exit_after_cleanup=${1:-true}
    echo -e "\n${YELLOW}Shutting down servers...${NC}"

    if [ ! -z "$BACKEND_PID" ] && kill -0 $BACKEND_PID 2>/dev/null; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
    fi

    if [ ! -z "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null || true
        wait $FRONTEND_PID 2>/dev/null || true
    fi

    echo -e "${GREEN}Servers stopped.${NC}"

    if [ "$exit_after_cleanup" = "true" ]; then
        exit 0
    fi
}

# Set trap for cleanup
trap 'cleanup true' SIGINT SIGTERM

# Health check functions
check_backend_health() {
    local max_attempts=30
    local attempt=1

    echo -e "${BLUE}Waiting for backend to be ready...${NC}"

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$BACKEND_URL/health" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Backend is healthy${NC}"
            return 0
        fi

        echo -e "${YELLOW}Backend not ready (attempt $attempt/$max_attempts)...${NC}"
        sleep 2
        ((attempt++))
    done

    echo -e "${RED}❌ Backend failed to start within $(($max_attempts * 2)) seconds${NC}"
    return 1
}

check_frontend_health() {
    local max_attempts=20
    local attempt=1

    echo -e "${BLUE}Waiting for frontend to be ready...${NC}"

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$FRONTEND_URL" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Frontend is healthy${NC}"
            return 0
        fi

        echo -e "${YELLOW}Frontend not ready (attempt $attempt/$max_attempts)...${NC}"
        sleep 2
        ((attempt++))
    done

    echo -e "${RED}❌ Frontend failed to start within $(($max_attempts * 2)) seconds${NC}"
    return 1
}

# Server management functions
start_backend() {
    echo -e "${BLUE}🚀 Starting backend server...${NC}"

    cd backend

    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}📦 Creating virtual environment...${NC}"
        python3 -m venv venv
    fi

    # Activate virtual environment (sandbox-compatible)
    export VIRTUAL_ENV="$(pwd)/venv"
    export PATH="$VIRTUAL_ENV/bin:$PATH"
    # Unset PYTHONHOME if it exists
    unset PYTHONHOME 2>/dev/null || true

    # Install/update dependencies
    echo -e "${BLUE}📦 Installing/updating dependencies...${NC}"
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt

    # Start the server in background (Supabase handles database)
    echo -e "${BLUE}🌐 Starting uvicorn server on port $BACKEND_PORT...${NC}"
    uvicorn main:app --reload --host 0.0.0.0 --port $BACKEND_PORT > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!

    cd ..
    echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID)${NC}"
}

start_frontend() {
    echo -e "${BLUE}🎨 Starting frontend server...${NC}"

    cd frontend

    # Load nvm and activate Node version (virtual environment approach)
    echo -e "${BLUE}🔧 Loading Node.js virtual environment (nvm)...${NC}"
    export NVM_DIR="$HOME/.nvm"
    # Try to load nvm (may fail in sandbox environment)
    if [ -s "$NVM_DIR/nvm.sh" ]; then
        \. "$NVM_DIR/nvm.sh" 2>/dev/null || echo -e "${YELLOW}⚠️  Warning: Could not load nvm.sh (sandbox environment?)${NC}"
        [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" 2>/dev/null || true
    else
        echo -e "${YELLOW}⚠️  Warning: nvm not found at $NVM_DIR${NC}"
    fi

    # Use Node 18 for frontend (optional: .nvmrc at repo root overrides)
    if command -v nvm >/dev/null 2>&1; then
        if [ -f "../.nvmrc" ]; then
            nvm use $(cat ../.nvmrc) 2>/dev/null || nvm install $(cat ../.nvmrc) 2>/dev/null || echo -e "${YELLOW}⚠️  Warning: Could not activate Node version from .nvmrc${NC}"
        else
            nvm use 18 2>/dev/null || nvm install 18 2>/dev/null || echo -e "${YELLOW}⚠️  Warning: Could not activate Node 18${NC}"
        fi

        if command -v node >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Using Node.js $(node --version) via nvm${NC}"
        else
            echo -e "${YELLOW}⚠️  Warning: Node.js not available, proceeding anyway${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Warning: nvm command not available, proceeding with system Node.js${NC}"
        if command -v node >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Using system Node.js $(node --version)${NC}"
        else
            echo -e "${RED}❌ Error: Node.js not found${NC}"
            return 1
        fi
    fi

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}📦 Installing frontend dependencies...${NC}"
        npm install
    fi

    # Start the dev server
    echo -e "${BLUE}🌐 Starting Vite dev server on port $FRONTEND_PORT...${NC}"
    npm run dev > "$FRONTEND_LOG" 2>&1 &
    FRONTEND_PID=$!

    cd ..
    echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID)${NC}"
}

show_status() {
    echo -e "\n${BLUE}📊 Server Status:${NC}"

    # Check backend by testing the health endpoint
    if curl -s -f "$BACKEND_URL/health" >/dev/null 2>&1; then
        # Try to find the actual PID
        local backend_pid=$(pgrep -f "uvicorn.*--port $BACKEND_PORT" 2>/dev/null | head -1)
        if [ ! -z "$backend_pid" ]; then
            echo -e "${GREEN}✅ Backend running (PID: $backend_pid)${NC}"
        else
            echo -e "${GREEN}✅ Backend running${NC}"
        fi
        echo -e "   URL: $BACKEND_URL"
        echo -e "   API Docs: $BACKEND_URL/docs"
        echo -e "   Log: $BACKEND_LOG"
    else
        echo -e "${RED}❌ Backend not running${NC}"
    fi

    # Check frontend by testing the URL
    if curl -s -f "$FRONTEND_URL" >/dev/null 2>&1; then
        # Try to find the actual PID
        local frontend_pid=$(pgrep -f "vite.*--port $FRONTEND_PORT" 2>/dev/null | head -1)
        if [ ! -z "$frontend_pid" ]; then
            echo -e "${GREEN}✅ Frontend running (PID: $frontend_pid)${NC}"
        else
            echo -e "${GREEN}✅ Frontend running${NC}"
        fi
        echo -e "   URL: $FRONTEND_URL"
        echo -e "   Log: $FRONTEND_LOG"
    else
        echo -e "${RED}❌ Frontend not running${NC}"
    fi
}

start_servers() {
    echo -e "${GREEN}🛒 Starting Shopping Monitor Development Servers${NC}"
    echo "========================================"

    # Check if we're in the right directory
    if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
        echo -e "${RED}❌ Error: Please run this script from the project root directory${NC}"
        echo -e "${YELLOW}Usage: ./dev-servers.sh${NC}"
        exit 1
    fi

    # Kill any existing processes first
    kill_existing_processes

    # Start both servers
    start_backend
    start_frontend

    # Health checks
    echo ""
    check_backend_health
    check_frontend_health

    echo ""
    echo -e "${GREEN}🎉 All servers are running and healthy!${NC}"
    show_status

    echo ""
    echo -e "${BLUE}🌐 Frontend available at: $FRONTEND_URL${NC}"
    echo -e "${BLUE}💡 To open in Cursor: Use the browser tool or manually navigate${NC}"

    echo ""
    echo -e "${YELLOW}🛑 Press Ctrl+C to stop all servers${NC}"
    echo -e "${BLUE}💡 Commands:${NC}"
    echo -e "   • ./dev-servers.sh status    - Show server status"
    echo -e "   • ./dev-servers.sh logs [backend|frontend] - Show logs"
    echo -e "   • ./dev-servers.sh stop      - Stop all servers"
}

show_logs() {
    local service=$1
    case $service in
        backend)
            if [ -f "$BACKEND_LOG" ]; then
                echo -e "${BLUE}📄 Backend logs (last 20 lines):${NC}"
                tail -20 "$BACKEND_LOG"
            else
                echo -e "${YELLOW}No backend log file found${NC}"
            fi
            ;;
        frontend)
            if [ -f "$FRONTEND_LOG" ]; then
                echo -e "${BLUE}📄 Frontend logs (last 20 lines):${NC}"
                tail -20 "$FRONTEND_LOG"
            else
                echo -e "${YELLOW}No frontend log file found${NC}"
            fi
            ;;
        *)
            echo -e "${RED}Usage: $0 logs [backend|frontend]${NC}"
            ;;
    esac
}

# Main command handling
case "${1:-start}" in
    start)
        start_servers
        # Wait for processes
        wait
        ;;

    stop)
        echo -e "${YELLOW}🛑 Stopping all servers...${NC}"
        cleanup false
        ;;

    restart)
        echo -e "${YELLOW}🔄 Restarting servers...${NC}"
        echo -e "${YELLOW}🛑 Stopping all servers...${NC}"
        cleanup false
        sleep 2
        start_servers
        ;;

    status)
        show_status
        ;;

    logs)
        show_logs "$2"
        ;;

    health)
        echo -e "${BLUE}🏥 Health Check:${NC}"

        if curl -s -f "$BACKEND_URL/health" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Backend: Healthy${NC}"
        else
            echo -e "${RED}❌ Backend: Unhealthy${NC}"
        fi

        if curl -s -f "$FRONTEND_URL" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Frontend: Healthy${NC}"
        else
            echo -e "${RED}❌ Frontend: Unhealthy${NC}"
        fi
        ;;

    help|--help|-h)
        echo -e "${BLUE}Usage: $0 [command]${NC}"
        echo ""
        echo -e "${BLUE}Commands:${NC}"
        echo "  start     - Start both backend and frontend servers with health checks (default)"
        echo "             - Automatically kills leftover processes and opens browser"
        echo "  stop      - Stop all running servers"
        echo "  restart   - Restart all servers (with process cleanup)"
        echo "  status    - Show current server status"
        echo "  logs [backend|frontend] - Show server logs"
        echo "  health    - Check server health"
        echo ""
        echo -e "${YELLOW}Examples:${NC}"
        echo "  ./dev-servers.sh              # Start servers"
        echo "  ./dev-servers.sh logs backend # Show backend logs"
        echo "  ./dev-servers.sh health       # Check health"
        ;;

    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo ""
        echo -e "${BLUE}Usage: $0 [command]${NC}"
        echo ""
        echo -e "${BLUE}Commands:${NC}"
        echo "  start     - Start both backend and frontend servers with health checks (default)"
        echo "             - Automatically kills leftover processes and opens browser"
        echo "  stop      - Stop all running servers"
        echo "  restart   - Restart all servers (with process cleanup)"
        echo "  status    - Show current server status"
        echo "  logs [backend|frontend] - Show server logs"
        echo "  health    - Check server health"
        echo ""
        echo -e "${YELLOW}Examples:${NC}"
        echo "  ./dev-servers.sh              # Start servers"
        echo "  ./dev-servers.sh logs backend # Show backend logs"
        echo "  ./dev-servers.sh health       # Check health"
        exit 1
        ;;
esac
