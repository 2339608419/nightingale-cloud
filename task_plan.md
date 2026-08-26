# Nightingale Glance View and Highlights Plan

## Goal
Add a fast Glance View backed by deterministic highlights with verifiable navigation to existing timeline sources.

## Phases
- [x] Inspect existing models, startup, routes, seed, tests, API client, and timeline anchors
- [x] Add Highlight persistence model and response schema
- [x] Centralize deterministic importance scoring
- [x] Seed source-grounded synthetic highlights
- [x] Add ranked highlights retrieval endpoint and provenance tests
- [x] Build Glance View with provenance navigation and source emphasis
- [x] Run and fix all backend tests and frontend production build
- [x] Review scope and report results

## Constraints
- No authentication/RBAC, revision history, comments, LLM integration, self-learning, or voice.
- Preserve clean boundaries for future prompts.
- Claim only commands actually executed.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| `python` was not on PATH during session catchup | 1 | Located the bundled Python runtime before implementation. |
| Dependency installs were blocked by sandbox networking | 1 | Re-ran approved installs with network access; both completed. |
| Frontend build could not find `node` from pnpm child process | 1 | Re-run with the bundled Node `bin` directory prepended to the process PATH. |
| TypeScript build lacked Vite ambient types and rejected an unnecessary node-config option | 1 | Added `vite/client` types and removed `allowImportingTsExtensions`. |
| Existing Phase 1 SQLite contained legacy `patient_insight`, which strict Phase 2 enum loading rejected during seed merge | 1 | Normalize only the known fixed demo entry to `staff_note` before ORM upserts. |
