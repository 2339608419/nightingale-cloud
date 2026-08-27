# Trust Hardening Step 3 — Human-Human Conflict Detection

## Goal
Extend the existing deterministic ConflictRecord pipeline to human-authored contradictions while preserving current clinician-versus-AI/patient behavior, RBAC, provenance, and UI architecture.

## Phases
- [x] Inspect existing model, service, write entry points, authority presentation, and tests
- [x] Define explicit deterministic source authority and review semantics
- [x] Extend existing conflict reconciliation without general NLP or unrelated changes
- [x] Reuse/update conflict API and UI only where authority visibility requires it
- [x] Add focused human-human conflict and regression tests
- [x] Run focused/full backend tests, frontend build, and `git diff --check`

## Constraints
- Preserve existing categories and clinician-versus-AI/patient behavior.
- Keep all evidence and both resolvable timeline-entry provenance links.
- Staff-versus-staff remains open and requires clinician review; do not invent authoritative truth.
- Preserve patient exclusion and clinic scope.
- Do not touch `Operation Manual(Simplified Version).txt`, commit changes, or begin Trust Step 4.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| Combined delete/add patch targeted the same plan path twice | 1 | Recreated the plan in a separate patch operation. |
| Initial multi-file implementation patch missed an export-list context | 1 | Split the change into smaller model, service, route, and frontend patches. |
| Existing AI conflict tests selected an older newly eligible human source first | 1 | Process sources oldest-first so the newest contradictory evidence remains first in the existing feed. |
| README documentation patch used an unstable wrapped-text context | 1 | Reapplied using the exact surrounding lines. |
| Full suite exposed tied conflict timestamps on Windows | 1 | Added deterministic microsecond sequence within each detection batch so newest-source ordering is stable. |
