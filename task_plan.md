# Trust Hardening Step 2 — Evidence Confidence

## Goal
Add deterministic, evidence-derived confidence to all Highlight responses and a minimal Top Card label without changing scoring or unrelated behavior.

## Phases
- [x] Recover context and inspect Highlight/provenance/conflict serialization paths
- [x] Define deterministic confidence levels and review behavior
- [x] Implement centralized confidence evaluation and additive response fields
- [x] Add minimal Top Card confidence/review presentation
- [x] Add focused tests including conflict, broken provenance, determinism, and no-LLM proof
- [x] Run focused/full backend tests, frontend checks/build, and diff review

## Constraints
- No scoring replacement, LLM self-confidence, patient approval, redaction changes, broad UI redesign, or Trust Step 3.
- Compute confidence only from database-verifiable evidence and deterministic extraction.
- Preserve existing response fields and RBAC semantics.
- Do not touch `Operation Manual(Simplified Version).txt`.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| README patch context did not match | 1 | Reapplied at the stable next-section heading; content was added without changing application behavior. |
