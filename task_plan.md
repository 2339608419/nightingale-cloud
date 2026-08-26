# Nightingale Inline Collaboration Plan

## Goal
Add clinic-scoped internal comment threads, mentions, resolution state, and simple task assignments on top of the existing RBAC boundaries.

## Phases
- [x] Inspect existing RBAC, models, routes, seed, frontend API, and timeline UI
- [x] Add Comment and TaskAssignment persistence models and schemas
- [x] Add mention parsing, threaded comment, resolution, and task services
- [x] Add clinic-scoped collaboration endpoints and seed demo collaboration data
- [x] Add required backend collaboration tests
- [x] Add timeline comment UI and Glance Open Actions UI
- [x] Run collaboration tests, all backend tests, and frontend production build
- [x] Review scope and report results

## Constraints
- Preserve existing server-side RBAC and clinic isolation.
- No revision history, notification system, LLM integration, self-learning, or voice.
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
| Mention parser included sentence-ending `.` in `@lab_team.` | 1 | Require mention handles to end in an alphanumeric or underscore character. |
