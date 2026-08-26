# Project Requirements — Step 1

This repository is the first architecture slice of the Nightingale Cloud 72-hour prototype.

## In scope

- React, TypeScript, and Vite frontend
- FastAPI REST backend with SQLAlchemy and SQLite
- `Patient` and `TimelineEntry` persistence models
- `GET /health`, `GET /patients/{patient_id}`, and `GET /patients/{patient_id}/entries`
- Idempotent synthetic demo seed
- Patient header, placeholder Glance View, and timeline page
- Minimal backend API tests

## Explicitly deferred

Authentication, RBAC, comments, revision history, highlights, AI functions, PHI redaction, adaptive ranking, voice capture, and data decay are intentionally excluded from this step.

## Architecture constraints

- HTTP routes must not contain persistence setup or seed logic.
- ORM entities and response schemas remain separate.
- Database sessions are injected so tests and later authorization layers can replace dependencies.
- Only synthetic data may be committed to this repository.

