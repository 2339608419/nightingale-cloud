# Nightingale Care Note — Technical Brief

## Purpose and scope

Nightingale is a synthetic-data-only 72-hour prototype of a shared longitudinal
Care Note. It combines a patient timeline, fast clinical Glance View,
provenance-linked highlights, internal collaboration, versioned edits, and a
PHI-safe AI-scribe path. It is intentionally not a production EHR.

## Architecture

```text
React + TypeScript + Vite
  | REST + demo identity headers
  v
FastAPI routes
  |-- centralized authorization checks
  |-- Pydantic request/response schemas
  v
Domain services
  |-- timeline / collaboration / revisions
  |-- deterministic importance + adaptive preferences
  |-- PHI redaction -> mock or opt-in LLM provider
  |-- reversible data-decay preview
  v
SQLAlchemy ORM -> SQLite
```

FastAPI dependencies resolve a development identity from `X-User-Id`, `X-Role`,
and `X-Clinic-Id`. Routes load the patient, enforce clinic and role policy, then
call focused services. Frontend permission checks improve usability only; the API
rejects unauthorized operations independently.

The patient header and Glance View render after core patient, timeline, highlight,
and decay requests. Comments, versions, tasks, and preference signals load afterward
so per-entry collaboration fan-out does not block the clinical summary.

## Data schema and relationships

```text
Patient 1 ---- * TimelineEntry 1 ---- * EntryVersion
   |                    |
   |                    +---------- * Comment
   |                                  | parent -> threaded replies
   |                    +------ * ConflictRecord * ------+
   |                         authoritative entry     conflicting entry
   +------ * Highlight * ------------+
   |          | entry_id + source_span + DOM provenance pointer
   +------ * TaskAssignment (optional entry_id)

Clinic (logical scope via Patient.clinic_id) ---- * ImportancePreference
TimelineEntry 1 ---- * AuditLog (entity_type + entity_id)
```

`TimelineEntry` is the canonical longitudinal unit. It records patient, author role
and identifier, timestamp, constrained type, content, and source pointer. AI-scribe
entries use `author_role=system`, one of three AI types, and a stable synthetic source
identifier. Raw transcripts are not stored.

Each `Highlight` references an entry and exact source substring. Its browser pointer
is `timeline-entry-{entry_id}`; clicking scrolls to and emphasizes that entry.
Highlights retain risk, reason, status, entity, unresolved state, score, and
clinician confirmation. Comments use a nullable parent for replies. Assignments are
patient-scoped and optionally entry-linked. Versions are immutable full snapshots.
Audit logs hold actor/action/entity/version metadata and omit note content. A unique
`(entry_id, version_number)` constraint supports optimistic concurrency.

Conflict records preserve normalized prior and clinician-authoritative values and
reference both unchanged timeline entries. Open records are internal and may be
resolved only by a clinician.

## Trust, privacy, and authorization

```text
explicitly synthetic request
  -> patient + clinic authorization
  -> redact_phi(name, Singapore ID, phone)
  -> provider receives redacted text only
  -> redacted summary persisted as system-authored timeline entry
```

The default summarizer is deterministic and offline; external OpenAI use is opt-in.
Logs contain source ID, interaction type, and redaction count, never transcript text.
A capture-provider test proves only redacted text crosses the provider boundary. TLS
and encryption at rest are deployment assumptions, not local infrastructure.

Patients are limited to their own instructions and cannot access raw AI notes,
comments, tasks, versions, or preferences. Staff edit only staff notes and cannot
view raw AI notes. Clinicians can read AI/staff context and edit only clinician-owned
note types. Admins have clinic-scoped oversight. Demo headers are not authentication
and require replacement before any real deployment.

## Prioritization, adaptation, and decay

The base score is additive: risk (0–40), recency (0–15), unresolved action (20),
entity (10–20), and clinician confirmation (15). Glance returns up to five
non-rejected highlights sorted by score.

Adaptive heuristic learning records clinic-scoped accept/reject counts for entity and
entry-type categories. Acceptance adds future bonuses (+5 entity, +2 entry type),
while rejection subtracts smaller values. The combined bonus is capped from -10 to
+25 and exposed with counts and explanations. This is not an ML model.

Clinical safety floors are applied after this learned adjustment. Allergy cannot fall
below HIGH/50; unresolved medication dosage conflicts cannot fall below HIGH/65;
recent or unresolved medication changes cannot fall below MODERATE/35; and unresolved
clinical follow-up cannot fall below MODERATE/50. The suggestion response exposes the
base score, learned adjustment, adjusted score, selected rule/floor, final score, and
whether enforcement changed the result.

Evidence confidence is a separate, response-time trust evaluation rather than part of
importance ranking. Exact provenance and source-span verification are prerequisites;
recognized deterministic facts with no conflict are HIGH, exact but unstructured
evidence is MEDIUM, and a structured entity mismatch is LOW/review. Broken evidence
or any open contradiction yields ABSTAIN/Needs review. The evaluation exposes its
inputs and reason, is deterministic, and never invokes an LLM provider.

Data decay is read-only: recent entries remain full, old low-priority entries receive
a compact preview, and durable allergy/risk/keyword facts remain full. Original
entries and provenance are never deleted.

## Assumptions, trade-offs, and scope decisions

- SQLite and synchronous SQLAlchemy favor demo reliability over horizontal scale.
- Full snapshots simplify revert correctness at the cost of storage.
- Entries act as independently editable sections; there is no rich-text CRDT.
- OCC rejects stale writes with HTTP 409; clients reload and reconcile.
- AI provenance is stable, but raw transcript spans are not retained for viewing.
- Seed data covers 15 April 2025, 6 February 2026, and recent August events.
- Central AuditLog covers note edits/reverts and supported trust-state transitions:
  highlight decisions, comment resolution, assignment status, and conflict resolution.
  Trust events contain status metadata only and skip denied or no-op requests.
- AI/patient-versus-clinician conflicts are detected for a deliberately small,
  deterministic demo vocabulary; broader clinical language remains out of scope.

## Warm-path performance approximation

`backend/scripts/benchmark_glance.py` seeds in-memory SQLite, warms the route, then
measures each request with a monotonic high-resolution clock. The audit ran 20
warmups and 200 clinician requests to
`GET /patients/patient-demo-001/highlights`.

| Metric | Result |
|---|---:|
| Median | 4.221 ms |
| P95 (nearest rank) | 5.048 ms |
| Minimum | 3.317 ms |
| Maximum | 6.898 ms |

Environment: Windows 11 (`10.0.26200`), Python 3.12.13, FastAPI 0.141.1,
SQLAlchemy 2.0.52, TestClient transport, and in-memory SQLite. The backend route is
below 300 ms in this controlled warm-path approximation. This is not a deployed or
browser-observed P95: it excludes network/process boundaries, concurrent load,
production data volume, other frontend calls, and rendering.
