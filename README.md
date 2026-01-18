# Strava Insight Portal

A production-ready web application that lets users log in with Strava and ask natural-language questions about their activity data using Google Gemini.

## Architecture

- **Backend**: Python FastAPI
- **Frontend**: React (Vite)
- **Database**: PostgreSQL
- **AI Integration**: Google Gemini API
- **Data Source**: Strava API via local MCP Server

## Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL
- Docker (optional, for DB)

## Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd strava-mcp
   ```

2. **Environment Variables**
   Create `backend/.env` with:
   ```bash
   DATABASE_URL=postgresql://user:pass@localhost:5432/strava_insight
   STRAVA_CLIENT_ID=your_id
   STRAVA_CLIENT_SECRET=your_secret
   STRAVA_REFRESH_TOKEN=dummy_or_real
   GEMINI_API_KEY=your_gemini_key
   FRONTEND_URL=http://localhost:5173
   REDIRECT_URI=http://localhost:5000/api/auth/strava/callback
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

5. **Database**
   Run via Docker:
   ```bash
   docker-compose up -d
   ```
   Or install PostgreSQL locally and creating `strava_insight` database.

## Running Locally

1. **Start Backend**
   ```bash
   source venv/bin/activate
   uvicorn backend.main:app --port 5000 --reload
   ```

2. **Start MCP Server**
   ```bash
   source venv/bin/activate
   python mcp-server/src/strava_http_server.py
   ```

3. **Start Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

4. **Access App**
   Open http://localhost:5173

## Deployment

Refer to `deployment/` directory for Nginx config and Systemd service files.

1. Copy service files to `/etc/systemd/system/`.
2. Reload daemon: `sudo systemctl daemon-reload`.
3. Enable and start services.
4. Configure Nginx with `nginx.conf`.
