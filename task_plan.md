# Nightingale Server-Side RBAC Plan

## Goal
Add reusable header-based development identity, server-side role authorization, and clinic isolation without redesigning existing product modules.

## Phases
- [x] Inspect routes, models, schemas, services, seed, tests, and frontend API path
- [x] Add reusable development identity dependency and centralized authorization policies
- [x] Protect patient, timeline, highlight, and internal-comment placeholder reads
- [x] Add authorized note creation and update endpoints
- [x] Seed a second-clinic patient and implement required RBAC micro-tests
- [x] Add clearly labeled frontend demo identity simulation
- [x] Run new RBAC tests, all backend tests, and frontend production build
- [x] Review scope and report results

## Constraints
- Development headers simulate identity; this is authorization, not production authentication.
- No comment persistence, revision history, LLM integration, self-learning, or voice.
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
