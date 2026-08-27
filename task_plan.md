# Trust Hardening Step 4 — Patient-Facing Human Approval Gate

## Goal
Add an explicit clinician approval gate for AI-generated/derived patient-facing instructions using the existing TimelineEntry, revision, RBAC, provenance, audit, and frontend architecture.

## Phases
- [x] Inspect timeline/instruction model, patient visibility, AI pipeline, audit/revision, seed data, UI, and tests
- [x] Define the smallest safe approval-state and compatibility policy
- [x] Implement additive model/schema/service/authorization and server-side filtering
- [x] Invalidate approval on content edits while preserving revision history and metadata-only audit
- [x] Add minimal clinician approval controls and patient trust indicator
- [x] Add focused approval, privacy, audit, provenance, scope, and regression tests
- [x] Run focused/relevant/full backend tests, frontend checks/build, and `git diff --check`

## Constraints
- No direct AI-to-patient path; draft and rejected AI-derived instructions are never patient-visible.
- Only clinicians may approve or reject; staff, patient, and admin remain denied.
- Preserve existing RBAC, clinic scope, internal-data restrictions, provenance, and revisions.
- Do not store clinical content or PHI in AuditLog.
- Do not touch `Operation Manual(Simplified Version).txt`, commit, or begin Trust Step 5.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| None | - | - |
| Additive TimelineEntry response fields broke an exact legacy field-set assertion | 1 | Updated the contract test to include the new approval metadata fields; all other initial regression tests passed. |
| Combined service/docs patch used a repeated 422 context that did not match | 1 | Split the status/provenance correction from documentation and applied exact contexts. |
