# CityMind AI

A runnable smart-city intelligence starter focused on verified imported observations, transparent scenario assumptions, and operational alert workflows. The application deliberately displays empty states rather than inventing live feeds. This is a development MVP, not yet a production-certified control-room system.
![CityMind AI Ahmedabad Smart City Command Center](./Ahmedabad%20Smart%20City%20Command%20Centre.png)
## Architecture

```text
React + Vite UI ── REST /api/v1 ── FastAPI ── SQLite (local)
                                       ├── user registration / roles
                                       ├── observation CSV import
                                       ├── alerts + audit trail
                                       └── transparent scenario calculator
```

## Features
- Responsive dark operations dashboard with city selection, status indicators, metrics, charts, alert creation, and empty map-layer state.
- FastAPI API with OpenAPI docs, SQLite persistence, registration/login, password hashing, bearer authentication, alert lifecycle, bounded CSV upload, and scenario calculations.
- User-provided CSV import supports `city,category,metric,value` and optional `unit,lat,lon`. Rows are labeled `user_csv`; timestamps omitted in CSV are assigned ingestion time.
- Scenario calculator applies a documented proportional demand/capacity ratio; it is explicitly not a causal forecast.

## Prerequisites and local run
Python 3.11+ (tested environment 3.13), Node 20+.

### macOS/Linux
```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# second terminal
cd frontend && npm install && npm run dev
```

### Windows PowerShell
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# second terminal
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and register an analyst account (10+ character password). Backend docs: http://localhost:8000/docs. Health endpoints: `/health`, `/ready`. SQLite DB is created at `backend/citymind.db` on first run.

## Configuration
Optional environment variables: `DATABASE_URL` (default `sqlite:///./citymind.db` relative to backend working directory), `CORS_ORIGINS` (comma-separated origins, default local Vite origin). Copy `.env.example` for reference; no external API keys are needed for this MVP. Do not expose the local development API publicly.

## Data and limits
- Import CSV using `POST /api/v1/imports/csv` with bearer auth, multipart field `file`, max 5 MB.
- Operational source connectors (OpenAQ, weather, OSM) are not wired in this implementation. The map panel explicitly states that the OSM base map is not connected. Never interpret imported data as live.
- No seeded operational dataset is included. Dashboard metrics display `—` until observations are imported.
- Model training, forecasting, PDF reports, full map layers, email, password reset, and production-grade session lifecycle are not implemented. No predictive accuracy is claimed.

## Quality
Backend dependency versions are pinned in `backend/requirements.txt`. Frontend production build: `cd frontend && npm run build`. Tests can be added with pytest/Vitest; automated suite not yet implemented. See `docs/limitations.md` for security and roadmap details.

## Security / production hardening
Passwords use PBKDF2-HMAC-SHA256. This MVP uses bearer authentication and a simple local database session token arrangement; production requires dedicated expiring/revocable session storage, secure cookies or well-designed token lifecycle, email verification/reset, RBAC policy enforcement on every route, migrations, rate limiting, request logging, secret management, HTTPS, backup/retention policies, and security review. Restrict CORS and use PostgreSQL/PostGIS before multi-user deployment. Do not upload personally identifying or sensitive information.

## Git safe commit
```bash
git init
git add .
git status # inspect for secrets/local databases
# ensure .env, *.db, .venv, node_modules are ignored
git commit -m "Build CityMind AI smart city intelligence MVP"
```
