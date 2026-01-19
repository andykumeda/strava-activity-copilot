# Project Status & Roadmap

**Last Updated:** January 18, 2026

## 📋 Executive Summary
The Strava Insight Portal is a functional MVP allowing users to query their Strava data using LLMs. It features a React frontend, FastAPI backend, and a custom MCP-like server for Strava integration. Recent updates have optimized context management, integrated OpenRouter for cost-effective LLM access, and improved basic security/configuration.

**Current Focus:** Critical security hardening (Authentication & Encryption) and stability improvements.

---

## 🚀 Recent Accomplishments
- **LLM Integration:** Successfully migrated to OpenRouter/DeepSeek for 70%+ cost reduction.
- **Context Optimization:** Implemented smart filtering (`ContextOptimizer`) to handle large datasets and prevent token limits.
- **Configuration:** Moved critical configs (CORS, URLs, Logging) to environment variables.
- **Performance:** Parallelized API calls and implemented connection pooling.
- **Security:** Added basic input validation and prompt injection delimiters.

---

## ⚠️ Critical Tasks (Immediate Priority)

### 1. Secure Authentication (High Risk)
**Issue:** User identification currently relies on an unsigned `auth_uid` cookie, allowing trivial impersonation.
**Action Plan:**
- Implement JWT-based authentication using `python-jose`.
- Replace plain-text cookies with HTTP-only, secure, signed cookies.
- Update `backend/auth.py` and `backend/deps.py` to issue and validate tokens.

### 2. Data Encryption
**Issue:** Strava Access/Refresh tokens are stored in plain text in the database.
**Action Plan:**
- Implement encryption at rest for the `tokens` table using `cryptography` (Fernet).
- Add decryption logic for token retrieval.

### 3. Prompt Injection Hardening
**Issue:** Current delimiters are insufficient against sophisticated injection attacks.
**Action Plan:**
- Separate user input from system instructions more robustly.
- Validate input for malicious patterns.

---

## 🛠️ Maintenance & Refactoring (Medium Priority)

### 1. Architecture Cleanup
**Issue:** `strava_http_server.py` uses blocking `time.sleep` in an async context.
**Action Plan:**
- Refactor `make_strava_request` to be async.
- Use `httpx` instead of `requests`.
- Replace `time.sleep` with `asyncio.sleep`.

### 2. Caching Strategy
**Issue:** In-memory caching (`ACTIVITY_CACHE`) is not persistent or distributed.
**Action Plan:**
- Implement Redis or file-based caching (`diskcache`) for robustness.

### 3. Database Management
**Issue:** No migration system.
**Action Plan:**
- Initialize Alembic for database migrations.

### 4. Code Quality
- Add comprehensive type hints to `mcp-server`.
- Add unit and integration tests (pytest/React Testing Library).
- Implement explicit frontend error boundaries.

---

## 🔮 Future Enhancements (Low Priority)
- **API Rate Limiting:** Implement `slowapi` to protect endpoints.
- **Request Queuing:** Better management of Strava API limits.
- **Bundle Optimization:** Code splitting for the frontend.
- **Monitoring:** Add structured logging and metrics (Prometheus/Grafana).

---

## 📚 Reference Information

### Recommended Models
- **Primary:** `deepseek/deepseek-chat` (via OpenRouter) - Best cost/performance.
- **Complex Tasks:** `deepseek/deepseek-reasoner` - Better for analysis.
- **Backup:** `google/gemini-2.5-flash` - Reliable fallback.

### Environment Setup
Ensure your `.env` includes:
```bash
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key
LLM_MODEL=deepseek/deepseek-chat
ALLOWED_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
```
