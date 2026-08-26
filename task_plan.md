# Nightingale Revision History Plan

## Goal
Add full-snapshot note history, metadata-only auditing, safe revert, and deterministic optimistic concurrency without changing existing authorization boundaries.

## Phases
- [x] Inspect existing models, update route/service, RBAC rules, tests, seed, and frontend timeline
- [x] Add EntryVersion and AuditLog persistence plus response/request schemas
- [x] Add transactional versioned edit, history, audit, and revert services/routes
- [x] Initialize version 1 for seeded and newly created entries
- [x] Add required revision-history and concurrent-edit backend tests
- [x] Add timeline Revision History UI with permitted revert and refresh
- [x] Run focused tests, all backend tests, frontend production build, and scope review

## Constraints
- Full snapshots; no diff storage.
- Audit logs contain metadata only, never note content.
- Preserve existing clinic scope and role/ownership edit rules.
- Stale same-entry writes return HTTP 409; separate entries remain independent.
- No unrelated Phase 7 functionality.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| Focused pytest path was repeated after setting the working directory to `backend` | 1 | Re-run with paths relative to `backend`. |
