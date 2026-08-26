# Nightingale Care Note Prototype

> **Security disclaimer:** This prototype uses synthetic data only. Do not enter, import, or process real patient information.

## 1. Project overview

Nightingale is a shared longitudinal care-note prototype for clinicians, staff, patients, administrators, and AI-scribed information. It replaces fragmented visit notes with a single timeline, a provenance-linked Glance View, collaboration, auditable revisions, clinic-scoped authorization, and deterministic importance ranking.

The primary demo patient is `Maya Chen (Synthetic)` (`patient-demo-001`). The architecture intentionally favors a small, reliable 72-hour prototype over production-EHR complexity.

## 2. Architecture

```text
React + TypeScript + Vite
          │ REST + development identity headers
          ▼
FastAPI routes → authorization policies → domain services
                                         ├─ timeline / collaboration
                                         ├─ revision / audit
                                         ├─ importance / adaptive feedback
                                         ├─ PHI redaction → summary provider
                                         └─ reversible data-decay preview
          │
          ▼
SQLAlchemy → SQLite
```

Backend code is separated into `models`, `schemas`, `routes`, `services`, and `database`. Authorization is enforced in FastAPI before protected service operations. The React client is a typed REST consumer; frontend role controls are demo identity simulation, not the security boundary.

## 3. Tech stack

- Frontend: React, TypeScript, Vite
- Backend: FastAPI, Pydantic
- Persistence: SQLAlchemy, SQLite
- API: REST/JSON
- Tests: pytest with isolated in-memory SQLite
- Default AI provider: deterministic offline mock

## 4. Setup

Python 3.11+ and Node.js 20+ are recommended.

```powershell
git clone <repository-url>
cd "Nightingale Cloud"

cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

cd ..\frontend
npm install
```

No external API key is required for the reliable demo path.

## 5. Backend run

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Startup creates the ignored `backend/nightingale.db` and idempotently seeds synthetic demo records.

## 6. Frontend run

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to FastAPI. Use `VITE_API_URL` to override the API origin.

## 7. Test commands

```powershell
cd backend
python -m pytest -q

cd ..\frontend
npm run build
```

Required candidate micro-tests are `test_rbac_scope.py`, `test_revision_history.py`, `test_highlight_provenance.py`, `test_concurrent_edits.py`, and `test_self_learning_importance.py`.

## 8. Demo identities and roles

The role selector is labeled **Demo identity simulation**. It sends `X-User-Id`, `X-Role`, and `X-Clinic-Id` development headers.

| Role | User ID | Demo behavior |
|---|---|---|
| Patient | `patient-demo-001` | Own patient-facing instructions only |
| Staff | `staff-demo-001` | Staff notes, permitted context, comments, tasks |
| Clinician | `clinician-demo-001` | Clinician notes, AI notes, decisions, revisions |
| Admin | `admin-demo-001` | Clinic-scoped oversight |

All primary identities use clinic `clinic-demo-001`. A second synthetic clinic record demonstrates isolation.

## Demo runbook

### Scenario A — Glance View and AI provenance

1. Select **Staff** and open the primary patient page.
2. Read the four high-value Glance items and open actions.
3. Click **Nurse follow-up unresolved**, marked with an exact-source action.
4. The page jumps to and briefly emphasizes the staff-safe, AI-derived timeline source. Raw AI-scribed note types remain hidden from staff.

### Scenario B — Collaboration, audit, and learning

1. As **Staff**, use **Add staff note**, then add `@clinician-demo-001 please review the medication plan.` as a comment.
2. Switch to **Clinician** and accept the AI-derived follow-up suggestion.
3. Observe the Adaptive Learning signal (`follow up +5`, `system event +2`) for future similar information.
4. Edit a clinician-owned note. Open **Revision History** to view versions and revert to the prior snapshot.
5. Resolve or unresolve the comment to demonstrate collaboration state.

### Scenario C — Longitudinal context

The timeline includes April 15, 2025; February 6, 2026; and recent August 2026 entries across human and AI origins. Glance ordering shows why current risk and unresolved work outrank older low-value information. Open and recently completed actions are both visible. Older low-priority entries display a cold-summary preview while durable hypertension/allergy facts remain full-detail.

## 9. RBAC enforcement

RBAC and clinic scope are enforced server-side in `authorization_service.py`:

- Patient: self-only, patient-facing instructions; no internal comments, tasks, raw AI notes, or revision internals.
- Staff: create/edit staff notes only; permitted clinical context; no clinician-note overwrite or cross-clinic access.
- Clinician: create/edit clinician notes and instructions; view staff and AI notes; no staff-note overwrite.
- Admin: oversight within the admin's clinic; no implicit cross-clinic access.

Frontend hiding is convenience only. Unauthorized requests return `401` or `403` from FastAPI.

## 10. PHI redaction pipeline

```text
POST /ai-scribe
→ validate synthetic-only input
→ clinic/RBAC authorization
→ redact_phi (names, Singapore IC/ID, phone)
→ summary provider receives redacted text only
→ persist summary + stable provenance
```

Redaction occurs in `backend/app/services/ai_scribe_service.py` before provider invocation. Raw transcripts are not logged, stored in timeline entries, or stored in version snapshots. Tests use a capturing fake provider to prove it receives only redacted text.

## 11. AI provider and mock behavior

The deterministic mock provider is the default and makes the demo independent of network access and credentials. External OpenAI Responses use is opt-in:

```powershell
$env:AI_SCRIBE_PROVIDER = "openai"
$env:OPENAI_API_KEY = "..."
$env:OPENAI_MODEL = "gpt-5-mini" # optional
```

If explicit selection or the key is absent, mock mode is used. No model or API output is bundled.

## 12. Provenance design

Every highlight stores `entry_id`, `source_span`, and `provenance_pointer`. The pointer uses stable DOM target `timeline-entry-{entry_id}`. Source spans are validated against source content. Clicking a Glance item scrolls to the originating entry; AI ingestion separately stores a stable source such as `synthetic://ai-scribe/{source_id}#transcript`.

Clinician note creation and editing also run a deterministic conflict check for the
synthetic medication/dosage, allergy-status, and follow-up-status vocabulary. When a
clinician value differs from an existing AI/patient-derived value, the clinician
entry remains authoritative and an internal conflict record links to both unchanged
timeline entries. Clinicians can resolve the warning; patients cannot access it.

## 13. Revision and version control

Editable notes use immutable full snapshots in `EntryVersion`. Updates require `expected_version`; stale same-entry writes return HTTP `409`, while separate entries remain independent. Revert restores a selected snapshot as a new version. `AuditLog` stores actor/action/version metadata only, not note content. Git history is organized into feature commits; runtime databases and build artifacts are ignored.

## 14. Self-learning importance mechanism

This is an adaptive heuristic, not an ML model. The base combines risk, recency, unresolved actions, clinical entity, and clinician confirmation. Clinic-scoped feedback adds:

- accepted entity `+5`; rejected entity `-2`
- accepted source entry type `+2`; rejected source entry type `-1`
- total learned bonus capped to `[-10, +25]`

Only clinicians accept/reject. Identical decisions are idempotent; changing a decision reverses previous counters. `GET /importance-preferences` exposes counts, weights, and explanations.

## 15. Data decay policy

The prototype implements a safe, read-only preview at `GET /patients/{patient_id}/decay-preview`:

- entries within 180 days: full detail
- older low-priority entries: deterministic cold-summary representation
- durable allergy, risk, chronic-condition, hypertension, and major-procedure facts: exempt and full detail
- every representation retains provenance and reports `original_available: true`

The service never mutates or deletes `TimelineEntry`. It demonstrates future hot/cold storage while remaining reversible and auditable.

## 16. Known limitations

- Development headers are not production authentication.
- SQLite and metadata `create_all` are prototype persistence, not a migration strategy.
- PHI detection is deterministic pattern matching, not production clinical NER/DLP.
- External-provider retries, rate limits, and operational monitoring are not implemented.
- Preference updates are not designed for multi-process high-contention workloads.
- Data decay is a representation preview, not physical cold-tier storage.
- No browser E2E suite, voice capture, notification delivery, or deployment configuration.

### Warm-path Glance benchmark

Run the repeatable backend approximation from `backend/`:

```bash
python scripts/benchmark_glance.py --requests 200 --warmups 20
```

Final-audit measurement on Windows 11, Python 3.12.13, FastAPI 0.141.1,
SQLAlchemy 2.0.52, and in-memory SQLite: 200 measured requests after 20 warmups,
median 4.221 ms and P95 5.048 ms for
`GET /patients/patient-demo-001/highlights`. This in-process TestClient measurement
includes routing, authorization, SQLAlchemy query work, and serialization, but
excludes network latency, other frontend requests, and browser rendering. It is a
warm-path approximation, not a production SLA result.

## 17. Synthetic-data security notice

**Use synthetic data only.** Seeded names, identifiers, encounters, comments, transcripts, and clinical facts are fictional. This prototype is not an EHR, does not provide medical advice, and is not approved for real PHI. TLS and encryption at rest are deployment assumptions, not implemented infrastructure here.
