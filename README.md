# Strava Insight Portal

A production-ready web application that lets users log in with Strava and ask natural-language questions about their activity data using LLMs (DeepSeek via OpenRouter, or Google Gemini).

## Features

- **Natural Language Queries**: Ask questions like "How many miles did I run in 2025?"
- **Full History Access**: Fetches and caches your entire Strava activity history (thousands of activities).
- **Smart Context Filtering**: Dynamically filters data sent to the LLM to avoid context limits while ensuring accuracy.
- **Robust Rate Handling**: Automatically handles Strava API rate limits (429 errors) with retries and backoff.
- **Caching**: In-memory caching ensures fast responses (~1s) for subsequent queries.
- **Rich Formatting**: AI responses formatted with Markdown bullet points and bold text.
- **Cost Effective**: Integrated with OpenRouter to use DeepSeek-V3 for significantly lower costs (~70% savings) compared to standard models, with automatic fallbacks.

## Architecture

- **Backend**: Python FastAPI (Port 8000)
- **Frontend**: React + Vite + TypeScript + TailwindCSS (Port 5173)
- **Data Server (MCP)**: Python FastAPI (Port 8001) - Handles Strava data fetching, caching, and summarization.
- **Database**: SQLite (default) or PostgreSQL.
- **AI Integration**: OpenRouter (DeepSeek) or Google Gemini.

## Prerequisites

- Python 3.12+
- Node.js 18+
- Strava API Application (Client ID & Secret)
- OpenRouter API Key (recommended) or Gemini API Key

## Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd strava-insight-portal
   ```

2. **Environment Variables**
   Create `backend/.env` with:
   ```bash
   # Database
   DATABASE_URL=sqlite:///./sql_app.db

   # Strava API (Get from strava.com/settings/api)
   STRAVA_CLIENT_ID=your_id
   STRAVA_CLIENT_SECRET=your_secret
   REDIRECT_URI=http://localhost:8000/api/auth/strava/callback

   # AI Provider (OpenRouter Recommended)
   LLM_PROVIDER=openrouter
   OPENROUTER_API_KEY=your_openrouter_key
   LLM_MODEL=deepseek/deepseek-chat
   
   # Or for Gemini:
   # LLM_PROVIDER=gemini
   # GEMINI_API_KEY=your_gemini_key
   # LLM_MODEL=gemini-2.5-flash

   # App Config
   FRONTEND_URL=http://localhost:5173
   MCP_SERVER_URL=http://localhost:8001
   ALLOWED_ORIGINS=http://localhost:5173
   LOG_LEVEL=INFO
   ```

3. **Backend Setup**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r backend/requirements.txt
   ```

4. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

## Running Locally

1. **Start Backend**
   ```bash
   source venv/bin/activate
   uvicorn backend.main:app --port 8000 --reload
   ```

2. **Start Data Server**
   ```bash
   source venv/bin/activate
   python mcp-server/src/strava_http_server.py
   ```
   (Runs on port 8001)

3. **Start Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

4. **Access App**
   Open http://localhost:5173

## Project Status

See [PROJECT_STATUS.md](./PROJECT_STATUS.md) for the current roadmap, critical tasks, and known issues.

## Deployment

Refer to `deployment/` directory for Nginx config and Systemd service files.

1. Copy service files to `/etc/systemd/system/`.
2. Reload daemon: `sudo systemctl daemon-reload`.
3. Enable and start services.
4. Configure Nginx with `nginx.conf`.