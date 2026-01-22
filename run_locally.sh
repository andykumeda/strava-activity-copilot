#!/bin/bash

# Kill child processes on exit
trap 'kill $(jobs -p)' EXIT

echo "🚀 Starting Strava Activity Copilot Locally..."

# Check only venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run 'python3 -m venv venv' and install requirements."
    exit 1
fi

# 1. Start MCP Server (Port 8001)
echo "🔌 Starting MCP Server on :8001..."
source venv/bin/activate
python mcp-server/src/strava_http_server.py > mcp.log 2>&1 &
MCP_PID=$!

# 2. Start Backend API (Port 8000)
echo "🔙 Starting Backend API on :8000..."
uvicorn backend.main:app --port 8000 --reload --env-file backend/.env > backend.log 2>&1 &
BACKEND_PID=$!

# 3. Start Frontend (Port 5173)
echo "🎨 Starting Frontend on :5173..."
cd frontend
npm run dev

# Wait for frontend to close
wait
