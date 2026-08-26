# Nightingale Care Note — Architecture Slice

A small working foundation for the Nightingale Cloud longitudinal patient care-note prototype. This first step intentionally implements only patient and timeline read paths.

## Repository layout

```text
frontend/                 React + TypeScript + Vite
  src/api.ts              Typed REST client
  src/App.tsx             Demo patient page
backend/                  FastAPI + SQLAlchemy
  app/database/           Engine, session, declarative base
  app/models/             Persistence entities
  app/schemas/            API response schemas
  app/routes/             REST endpoints
  app/services/           Queries and synthetic seed
  tests/                  Isolated API tests
PROJECT_REQUIREMENTS.md   Current scope and deferrals
```

## Backend setup and run

Python 3.11+ is recommended.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`. Startup creates `backend/nightingale.db` and idempotently seeds synthetic patient `patient-demo-001`.

## Frontend setup and run

Node.js 20+ is recommended.

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` calls to the backend. Set `VITE_API_URL` to use another API origin.

## Tests and build

```powershell
cd backend
python -m pytest

cd ..\frontend
npm run build
```

## API

- `GET /health`
- `GET /patients/{patient_id}`
- `GET /patients/{patient_id}/entries`

Unknown patient IDs return `404`. Timeline entries are returned newest first.

## Current limitations

This architecture slice has no authentication or authorization and is not suitable for real patient data. It has no write APIs, collaboration, audit history, highlights, AI, or PHI redaction. The Glance View is deliberately a placeholder for a later step.
