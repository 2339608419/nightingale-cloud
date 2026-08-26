# Nightingale Demo Readiness and Documentation Plan

## Goal
Make the existing application reliably demonstrate the three candidate scenarios, add a reversible data-decay preview, and complete handoff documentation.

## Phases
- [x] Inspect clean repository, demo seed, timeline/Glance/collaboration UI, tests, dependencies, and README
- [x] Strengthen primary-patient seed for Scenarios A–C without weakening RBAC
- [x] Add read-only, reversible data-decay preview service/API/tests
- [x] Add demo UI paths for staff note creation, clinician editing, completed actions, learning feedback, and decay states
- [x] Polish clinical hierarchy, AI origin, provenance, Glance dominance, and action visibility
- [x] Rewrite README with all 17 required sections and add ATTRIBUTION.txt
- [x] Run complete backend tests, frontend production build, runtime smoke checks, and scope review

## Constraints
- Synthetic data only.
- Preserve existing RBAC and raw AI-note visibility rules.
- Data decay is a read-only representation; originals and provenance remain available.
- Avoid architectural rewrites and unnecessary animation.
- Keep demo flows reliable without external services.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| Browser could not reach `127.0.0.1:5173` because the pnpm argument form left Vite bound to localhost | 1 | Navigate to the advertised `http://localhost:5173` origin instead. |
| In-app browser remained isolated from the host localhost server even though shell HTTP checks returned 200 | 2 | Stop browser retries; verify demo data and routes through real application lifespan/API smoke tests. |
