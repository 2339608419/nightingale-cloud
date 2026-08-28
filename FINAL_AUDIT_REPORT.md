# Nightingale 72HR Build — Final Submission Audit

Audit date: 28 August 2026. This is an evidence-based prototype assessment, not production certification.

## Submission checklist

| Area | Requirement | Status | Verified evidence / limitation |
|---|---|---|---|
| Core | Shared longitudinal Care Note | PASS | One patient page combines header, dominant Glance View, actions, and newest-first timeline. |
| Core | Glance View and deterministic ranking | PASS | Up to five items show risk, reason, state, Evidence Confidence, and source navigation. |
| Core | Timeline and mixed authorship | PASS | Required dates and human/AI types are seeded; each entry has `timeline-entry-{id}`. |
| Core | AI-scribed ingestion | PASS | Three interaction types create system-authored entries through validated redaction and an offline mock by default. |
| Core | Collaboration | PASS | Threaded comments, mentions, resolve/unresolve, assignments, complete/reopen are implemented and tested. |
| Core | Revision, revert, audit | PASS | Immutable full snapshots, metadata-only audit events, and authorized revert are tested. |
| Core | Concurrent edit handling | PASS | Independent entries do not overwrite each other; stale same-entry updates receive HTTP 409. |
| Trust | Highlight provenance | PASS | Entry pointers and exact source spans resolve in automated tests; UI jumps to the source entry. |
| Trust | Raw AI source inspection | PARTIAL | AI entries retain stable synthetic source identifiers, but raw transcript segments are deliberately not persisted or viewable. |
| Trust | Conflict detection and authority | PASS | Deterministic medication/dosage, allergy, and follow-up conflicts cover human–human and human–AI/patient sources; both entries remain. |
| Trust | Evidence Confidence and abstention | PASS | Confidence derives from resolvable evidence, structured extraction, conflicts, and human confirmation; no LLM confidence call. |
| Trust | Clinical safety floors | PASS | Critical category floors apply after learned adjustment and are regression-tested against repeated rejection. |
| Trust | No direct AI → Patient path | PASS | AI-derived instructions start draft; only clinician approval makes them patient-visible; edits invalidate approval. |
| RBAC | Patient restrictions | PASS | Self-only approved instructions; raw AI, staff/clinician internals, comments, conflicts, versions, tasks, and audit data remain hidden. |
| RBAC | Staff restrictions | PASS | Staff-owned notes and permitted context only; no clinician overwrite, raw AI access, approval, or cross-clinic access. |
| RBAC | Clinician restrictions | PASS | Clinician-owned writes, AI/staff reads, decisions/review; no staff overwrite or cross-clinic access. |
| RBAC | Admin and clinic scope | PASS | Admin is clinic-scoped oversight and cannot approve patient instructions; reusable backend policies enforce all scope. |
| RBAC | Production authentication | PARTIAL | Identity headers are intentionally forgeable demo simulation and must be replaced before real deployment. |
| Privacy | Synthetic-only boundary | PASS | Seed and AI inputs are synthetic-only; README forbids real patient information. |
| Privacy | PHI redaction before provider | PASS | Name, Singapore ID, and phone redaction is followed by deterministic validation before any provider call. |
| Privacy | Provider abstention / logs | PASS | Failed validation calls no provider and creates no AI entry; tests verify no raw transcript/PHI in logs. |
| Privacy | TLS and encryption assumptions | PASS | Documented as deployment assumptions, not implemented local infrastructure. |
| Tests | Five required micro-test files | PASS | Exact invocation passed 18 tests. |
| Tests | Complete backend suite | PASS | 89 tests passed; one third-party TestClient deprecation warning. |
| Tests | Frontend type/build | PASS | Both TypeScript projects passed `--noEmit`; Vite production build succeeded. |
| Bonus | Adaptive importance | PASS | Bounded, deterministic, clinic-scoped entity/type feedback is inspectable and tested. |
| Bonus | Hybrid data decay | PARTIAL | Safe reversible summary/tier preview exists; no physical cold-storage migration. |
| Bonus | Voice capture | MISSING | Explicitly out of scope; no voice recording/transcription pipeline. |
| Deliverable | README | PASS | Setup, operation, tests, identities, RBAC, privacy, AI, provenance, versions, learning, decay, limitations, and disclaimer are present. |
| Deliverable | Technical brief | PASS | 1,264 words with architecture, schema, trust design, trade-offs, and measured P95. |
| Deliverable | Attribution | PASS | Direct major libraries, purposes, known licenses, mock behavior, and optional provider terms are listed. |
| Deliverable | Demo-ready seed/runbook | PASS | Idempotent synthetic dataset plus a standalone timed 5–7 minute walkthrough. |

## Required test evidence

```text
Candidate micro-tests: 18 passed, 1 warning in 0.92s
Complete backend suite: 89 passed, 1 warning in 4.18s
Frontend: TypeScript checks passed; Vite built 17 modules in 132ms
```

The warning comes from FastAPI/Starlette's current TestClient compatibility layer and does not fail the suite.

## Warm-path Glance benchmark

Command: `python backend/scripts/benchmark_glance.py --requests 200 --warmups 20`

| Measurement | Result |
|---|---:|
| Warmups | 20 |
| Measured requests | 200 |
| Median | 5.308 ms |
| P95 (nearest rank) | 6.540 ms |
| Minimum | 4.616 ms |
| Maximum | 17.024 ms |

Environment: Windows 11 (`10.0.26200`), Python 3.12.13, FastAPI 0.141.1, SQLAlchemy 2.0.52, in-memory SQLite/StaticPool, and in-process FastAPI TestClient. The backend warm route is below 300 ms in this controlled approximation. Status is **PARTIAL** for the end-to-end SLA because network/process boundaries, concurrent load, larger production records, the other patient-page requests, and browser rendering are excluded.

External LLM invoked during verification: **No**.

## Core missing requirements

No hard core-product requirement is known to be completely missing. The two material partials are direct inspection of raw AI transcript segments (not persisted by privacy design) and deployed/browser P95 evidence. Voice capture is an optional bonus and is missing.

## Five highest remaining risks

1. Development identity headers are forgeable; production identity, session security, and authorization claims are not implemented.
2. Clinical extraction/conflict logic intentionally covers only the synthetic demo vocabulary and is not general medical NLP.
3. AI provenance has stable identifiers but no retained raw transcript viewer, limiting exact source-span review for newly ingested summaries.
4. The P95 result is an in-process approximation, not a concurrent deployed or browser-observed measurement.
5. SQLite `create_all`, single-process adaptive counters, and preview-only cold storage are prototype mechanisms, not production operational designs.
