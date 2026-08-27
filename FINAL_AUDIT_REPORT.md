# Nightingale 72HR Build — Final Submission Audit

Audit date: 26 August 2026. Results reflect inspected code and commands run in this
workspace; they are not production certification.

## Core product

| Requirement | Status | Evidence / limitation |
|---|---|---|
| Shared Care Note | PASS | One patient page combines header, Glance, actions, and longitudinal timeline. |
| Glance View | PASS | Four ranked items show risk reason, state, and source action; API limit is five. |
| Longitudinal Timeline | PASS | Newest-first entries span required dates/types and have stable anchors. |
| AI-scribed entries | PASS | Three types, system authorship, visual AI badge, mock-first ingestion. |
| Comments/collaboration | PASS | Add, thread, mention, resolve/unresolve, and assignments are implemented/tested. |
| Revision history | PASS | Full snapshots with actor/time metadata and frontend history. |
| Revert | PASS | Authorized revert creates a new version restoring prior content. |
| Provenance | PARTIAL | Entry/span integrity is tested and UI jumps to the entry; raw AI transcript segments are not retained/viewable. |
| Conflict handling | PARTIAL | OCC returns 409 for stale same-entry writes; separate entries are independent, but no document-level CRDT exists. |
| Clinician precedence/conflict review | PASS | Deterministic medication, allergy, and follow-up conflicts retain both sources while marking the clinician entry authoritative. |

## RBAC

| Requirement | Status | Evidence / limitation |
|---|---|---|
| Patient restrictions | PASS | Own record/instructions only; AI notes and internal collaboration/version data blocked. |
| Staff restrictions | PASS | Staff-note write only; clinician overwrite, raw AI, and cross-clinic access denied. |
| Clinician restrictions | PASS | AI/staff read; clinician-owned write only; staff overwrite denied. |
| Clinic scope | PASS | Patient gate protects patient, entry, highlight, collaboration, and AI routes. |
| Server-side enforcement | PASS | Reusable authorization service protects routes independently of frontend. |
| Production authentication | PARTIAL | Forgeable headers are intentionally demo-only and unsafe for real data. |

## Privacy

| Requirement | Status | Evidence / limitation |
|---|---|---|
| Synthetic data only | PASS | Seeds are labeled synthetic; AI request requires `synthetic=true`. |
| Redaction before LLM | PASS | Name, Singapore ID, and phone redaction precedes provider invocation; fake-provider test verifies input. |
| No PHI in logs | PASS | Metadata-only AI logging is tested against raw examples. |
| TLS/encryption assumptions | PASS | README and technical brief document assumptions and non-implementation. |
| No raw transcript persistence | PASS | Transcript is absent from entry and version snapshots. |

## Tests

| Required file | Status | Coverage |
|---|---|---|
| `test_rbac_scope.py` | PASS | Cross-role writes, patient restrictions, clinic scope, missing identity. |
| `test_revision_history.py` | PASS | Version, revert, metadata-only audit. |
| `test_highlight_provenance.py` | PASS | Retrieval, source entry/span, ordering, score. |
| `test_concurrent_edits.py` | PASS | Independent entries and stale-write 409. |
| `test_self_learning_importance.py` | PASS | Acceptance bonus, rejection, decision RBAC. |
| Full suite | PASS | 43 passed in 1.61 s; one dependency deprecation warning. |

## Bonus and deliverables

| Requirement | Status | Evidence / limitation |
|---|---|---|
| Adaptive importance | PASS | Deterministic clinic-scoped entity/type weights with explanations. |
| Hybrid data decay | PARTIAL | Reversible tier/summary preview; no physical cold-store migration. |
| README | PASS | Required setup, architecture, security, demo, and mechanism sections present. |
| `ATTRIBUTION.txt` | PASS | Libraries/providers and known licenses listed. |
| Technical brief | PASS | Architecture, schema, assumptions, trade-offs, scope, and P95 included. |
| Demo-ready seed | PASS | Primary patient, boundary fixture, dates, mixed sources, highlights/comments/actions. |
| Clean Git history | PASS | Phase commits inspected through Phase 9; audit changes await review/commit. |

## Performance

- Command: `python scripts/benchmark_glance.py --requests 200 --warmups 20`
- Endpoint: `GET /patients/patient-demo-001/highlights`
- Requests: 200 after 20 warmups
- Median: 4.221 ms
- P95: 5.048 ms (nearest-rank)
- Range: 3.317–6.898 ms
- Environment: Windows 11, Python 3.12.13, FastAPI 0.141.1,
  SQLAlchemy 2.0.52, in-memory SQLite, in-process TestClient.

Status: **PARTIAL** for the end-to-end `<=300 ms` requirement. The measured backend
warm path is below the threshold, but excludes network/process latency, concurrent
load, production data volume, other frontend calls, and browser rendering. Core
Glance data now renders before per-entry collaboration/history fan-out completes.

## Final verification

- Backend: `64 passed, 1 warning in 2.89s`.
- Frontend: TypeScript checks and Vite build passed; 17 modules; JS 206.73 kB
  (64.23 kB gzip), CSS 12.01 kB (3.19 kB gzip).
- Config: Vite `/api` proxy targets local FastAPI; CORS allows local Vite origins;
  default runtime SQLite file is ignored.
- External LLM invoked during audit: **No**.

## Five highest-risk remaining issues

1. Demo identity headers are forgeable; verified authentication is mandatory before
   handling any real data.
2. Conflict extraction intentionally recognizes only the documented synthetic demo
   vocabulary and is not general clinical NLP.
3. AI provenance identifies a stable synthetic source, but the original transcript
   segment is not retained for direct review.
4. Audit events are persisted and tested, but there is no clinic-wide audit review
   interface or export in this prototype.
5. P95 is a single-process approximation; deployed/browser performance, contention,
   larger records, and frontend collaboration fan-out remain unmeasured.
