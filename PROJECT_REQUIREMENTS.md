# Project Requirements — Demo-ready prototype

This repository contains the demo-ready Nightingale Cloud 72-hour prototype. Only synthetic data is permitted.

## In scope

- React, TypeScript, and Vite frontend
- FastAPI REST backend with SQLAlchemy and SQLite
- Longitudinal timeline, Glance highlights, provenance, collaboration, tasks, and AI-scribed entries
- Server-side role and clinic scoping using development identity headers
- Full-snapshot revision history, metadata-only audit logs, revert, and optimistic concurrency
- Deterministic importance scoring with clinic-scoped adaptive feedback
- PHI redaction before provider invocation and reliable offline summarization
- Read-only, reversible data-decay preview
- Idempotent synthetic demo seed
- Demo-focused React patient page and complete backend micro-tests

## Explicitly deferred

Production authentication, production EHR integration, real PHI, voice capture, notification delivery, physical cold-tier storage, and production deployment infrastructure remain excluded.

## Architecture constraints

- HTTP routes must not contain persistence setup or seed logic.
- ORM entities and response schemas remain separate.
- Database sessions are injected so tests and later authorization layers can replace dependencies.
- Only synthetic data may be committed to this repository.
