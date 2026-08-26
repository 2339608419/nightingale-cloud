# Clinician-vs-AI/Patient Conflict Fix Plan

## Goal
Add deterministic, clinic-scoped conflict detection and clinician resolution for medication/dosage, allergy status, and follow-up status without changing unrelated architecture.

## Phases
- [x] Confirm clean Phase 10 checkpoint and recover prior context
- [x] Inspect current persistence, clinician create/edit, authorization, schemas, and frontend data flow
- [x] Define deterministic fact extraction and conflict lifecycle
- [x] Add ConflictRecord model/schema/service/routes and hook clinician create/edit
- [x] Add internal conflict warning, dual-source navigation, authoritative label, and resolve control
- [x] Add focused conflict/RBAC/provenance tests
- [x] Run focused tests, full backend suite, frontend production build, and scope review

## Constraints
- No general NLP, redesign, broad features, or unrelated audit fixes.
- Clinician entry is authoritative; prior AI/patient entry remains unchanged.
- Patient cannot access conflicts; clinic scope and server-side authorization are mandatory.
- Provenance must resolve to both existing timeline entries.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| None | - | - |
