# Nightingale Care Note — Prototype

A synthetic-data-only longitudinal patient care-note prototype with timeline, highlights, collaboration, server-side RBAC, revision history, and AI-scribe ingestion.

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
- `POST /ai-scribe`

Unknown patient IDs return `404`. Timeline entries are returned newest first.

## AI scribe and PHI redaction

The ingestion call chain is:

`POST /ai-scribe` → clinic/RBAC authorization → `redact_phi` → summary provider → timeline entry.

Redaction occurs in `backend/app/services/ai_scribe_service.py` before the provider is called. Names, Singapore-style IC/ID values, and phone numbers are replaced by `[NAME]`, `[ID]`, and `[PHONE]`. Logs contain only the synthetic source ID, interaction type, and redaction count. The raw transcript is never stored; only the generated redacted summary is persisted. Provenance is a stable synthetic identifier such as `synthetic://ai-scribe/source-001#transcript`.

The deterministic offline provider is the default and requires no credentials. External OpenAI summarization is opt-in:

```powershell
$env:AI_SCRIBE_PROVIDER = "openai"
$env:OPENAI_API_KEY = "..."
$env:OPENAI_MODEL = "gpt-5-mini" # optional
```

If either explicit provider selection or the key is absent, the application stays in deterministic mock mode. Only already-redacted text is sent to the external provider.

## Adaptive importance heuristic

Highlight ranking uses an explainable additive heuristic, not an ML model. The existing risk, recency, unresolved-action, clinical-entity, and clinician-confirmation score remains the base. Clinic-scoped feedback counters add a learned bonus to future similar suggestions:

- accepted entity category: `+5`; rejected entity category: `-2`
- accepted source entry type: `+2`; rejected source entry type: `-1`
- combined learned bonus is capped between `-10` and `+25`

Only clinicians can accept or reject suggestions. Feedback is idempotent for repeated identical decisions, and changing a decision reverses the prior counter before applying the new one. `GET /importance-preferences` exposes counts, weights, and a plain-language calculation for the current clinic. Each suggestion response separately returns its base score, learned bonus, and contributing preference explanations.

## Current limitations

Development identity headers simulate authentication; this is not production authentication and the application is not suitable for real patient data. AI summaries are deterministic by default, redaction is intentionally prototype-grade, and synthetic source transcripts are not retained or retrievable. Adaptive importance learns only from explicit highlight decisions; comment-frequency and keyword-topic learning remain future extensions.
