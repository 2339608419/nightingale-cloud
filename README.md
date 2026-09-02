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

Run exactly those micro-tests with:

```powershell
cd backend
python -m pytest tests/test_rbac_scope.py tests/test_revision_history.py tests/test_highlight_provenance.py tests/test_concurrent_edits.py tests/test_self_learning_importance.py -q
```

## 8. Demo identities and roles

The role selector is labeled **Demo identity simulation**. It sends `X-User-Id`, `X-Role`, and `X-Clinic-Id` development headers.

| Role | User ID | Demo behavior |
|---|---|---|
| Patient | `patient-demo-001` | Own patient-facing instructions only |
| Staff | `staff-demo-001` | Staff notes, permitted context, comments, tasks |
| Clinician | `clinician-demo-001` | Clinician notes, AI notes, decisions, revisions |
| Admin | `admin-demo-001` | Clinic-scoped oversight |

All primary identities use clinic `clinic-demo-001`. A second synthetic clinic record demonstrates isolation.

### Synthetic phone-first access

Phase 3 adds a local-only phone-first vertical slice for the seeded patient. It does
not require email and it does not contact a real phone provider:

```text
synthetic E.164 input + clinic context
→ normalize and domain-separated SHA-256 lookup
→ securely random, 10-minute one-time challenge
→ POST token exchange (never a query-string credential)
→ one-hour patient session
→ self-only approved instructions and safe delivery status
```

The database stores only the synthetic contact digest and masked destination. Challenge
and session credentials are stored only as irreversible digests with server-generated
expiry and consumed/revoked state. The local mock returns the challenge token once in
the response so the flow is demonstrable; production must deliver it out-of-band and
must never return it to the requesting browser. Tokens, full phone numbers, and clinical
content are not written to logs or audit metadata.

Valid known and unknown numbers intentionally receive the same HTTP status, fields,
`accepted=true`, mode, warning, and caller-derived masked-destination shape. For an
unknown number, the local mock returns a secure random, short-lived-looking decoy
challenge/token that is not persisted and can never be exchanged. Production wording
must remain generic: “If that number is available, we sent verification information.”
Invalid E.164 formatting is rejected separately as input validation; it never reports
whether an account exists. A live challenge is consumed with one conditional SQL update
(`token digest`, unused, unexpired), and the claim plus session creation commit in one
transaction. This is database atomicity rather than a process-local lock.

Phone lookup uniqueness is tenant-scoped through `(clinic_id, phone_digest)`: the same
synthetic number may identify different synthetic patients in different clinics, while
duplicates inside one clinic are rejected. Existing Phase 3 SQLite files must be rebuilt
for this prototype schema change; production requires a versioned migration. SQLite
tests exercise two independent database sessions, but do not prove multi-worker behavior
on a production database.

The existing development-header identities remain available for the original demo and
are not production authentication. The phone-first route is also a synthetic prototype,
not production OTP, account recovery, consent, device binding, or identity proofing.

## Demo runbook

Use [`DEMO_RUNBOOK.md`](DEMO_RUNBOOK.md) for a timed 5–7 minute walkthrough. It covers Glance/provenance, multi-date context, staff–clinician collaboration, adaptive importance, revision/revert, conflict review, and the clinician approval gate for AI-derived patient instructions.

## 9. RBAC enforcement

RBAC and clinic scope are enforced server-side through two independent application
boundaries:

- Routes retain the outer `require_patient_access` authorization guard. It enforces
  role, patient self-access, note ownership, approval authority, and the normal
  cross-clinic `403` contract.
- `clinic_scope_service.py` is an inner data-access boundary. Its SQL queries include
  `Patient.clinic_id` directly; linked entry, version, audit, highlight, comment,
  assignment, conflict, and approval lookups join back to the owning patient before
  returning an object. If the outer clinic comparison is omitted or fault-injected
  to a no-op, a foreign-clinic object remains invisible and the route returns `404`.
- Importance preferences are directly filtered by their stored `clinic_id`.

- Patient: self-only, patient-facing instructions; no internal comments, tasks, raw AI notes, or revision internals.
- Staff: create/edit staff notes only; permitted clinical context; no clinician-note overwrite or cross-clinic access.
- Clinician: create/edit clinician notes and instructions; view staff and AI notes; no staff-note overwrite.
- Admin: oversight within the admin's clinic; no implicit cross-clinic access.

Frontend hiding is convenience only. Authorization failures return `401`/`403`, while
the inner tenant query uses non-disclosing `404` semantics. Fault-injection tests
disable the outer clinic comparison and verify that known Clinic A IDs still cannot
be read or mutated by Clinic B.

### Clinic B onboarding readiness

The tenant-aware query boundary improves application isolation, but it is not a
complete clinic-onboarding platform. Launching Clinic B would require separate work:

1. **Configuration:** clinic display/configuration, allowed origins, provider/channel
   settings, secrets, and feature flags.
2. **Schema:** first-class `Clinic`, `User`, and `ClinicMembership` records; explicit
   tenant ownership constraints/indexes; and versioned migrations.
3. **Identity and membership:** replace forgeable development headers, verify a user's
   clinic roles, and support users who belong to multiple clinics.
4. **Data migration:** create Clinic A/B, backfill tenant ownership, detect orphaned or
   cross-tenant links, and remove production-startup demo-seed overwrite behavior.
5. **Deployment and operations:** managed database and migrations, TLS, managed
   secrets/encryption, backup/restore, tenant-aware monitoring, capacity planning,
   and incident response.
6. **Application and product:** onboarding workflow, clinic administration, user
   invitations, support, and offboarding.

These items remain explicitly `PARTIAL`; no placeholder model or UI is presented as a
production onboarding implementation.

## 10. PHI redaction pipeline

```text
POST /ai-scribe
→ validate synthetic-only input
→ clinic/RBAC authorization
→ redact_phi (names, Singapore IC/ID, phone)
→ validate_redaction (remaining PHI, protected clinical terms, output integrity)
→ pass: summary provider receives validated redacted text only
→ fail: abstain with "AI scribe withheld pending redaction review"
→ persist summary + stable provenance only after validation passes
```

Redaction occurs in `backend/app/services/ai_scribe_service.py` before provider invocation. Raw transcripts are not logged, stored in timeline entries, or stored in version snapshots. Tests use a capturing fake provider to prove it receives only redacted text.

Validation is deterministic and reports only safe categories and counts. It checks
for remaining Singapore IDs, phone numbers, and known synthetic fixture names;
verifies that Penicillin, Lisinopril, allergy terminology, and medication dosages
present in the input survive redaction; and requires meaningful output beyond
placeholders. A failed check invokes no provider and creates no AI timeline entry.

## 11. AI provider and mock behavior

The deterministic mock provider is the default and makes the demo independent of network access and credentials. External OpenAI Responses use is opt-in:

```powershell
$env:AI_SCRIBE_PROVIDER = "openai"
$env:OPENAI_API_KEY = "..."
$env:OPENAI_MODEL = "gpt-5-mini" # optional
$env:AI_SCRIBE_PROVIDER_TIMEOUT_SECONDS = "30" # optional, bounded to 0.1–120 seconds
```

If explicit selection or the key is absent, mock mode is used. Both providers sit
behind the same validation gate, so even an explicitly configured external provider
cannot receive text that failed redaction validation. The API identifies mock output
as `rule_derived_mock`; it is never presented as an external-model result. Runtime
provider timeout, unavailability/503, malformed, or empty responses produce a typed
safe-abstention result and no timeline entry. Provider response bodies and exception
text are not returned or logged, and this synchronous prototype performs no retry.
Client-provided AI source identifiers are never logged or persisted directly. Before
logging or provenance creation, the ingestion service converts them to a stable,
one-way `src_sha256_<digest>` reference using SHA-256 with a fixed domain separator;
the original identifier is not stored in a parallel field.
No model or API output is bundled.

## 12. Provenance design

Every highlight stores `entry_id`, `source_span`, and `provenance_pointer`. The pointer uses stable DOM target `timeline-entry-{entry_id}`. Source spans are validated against source content. Clicking a Glance item scrolls to the originating entry; AI ingestion separately stores an opaque stable source such as `synthetic://ai-scribe/src_sha256_<digest>#transcript`, never the client-provided identifier.

Clinician note creation and editing also run a deterministic conflict check for the
synthetic medication/dosage, allergy-status, and follow-up-status vocabulary. When a
clinician value differs from an existing AI/patient-derived value, the clinician
entry remains authoritative and an internal conflict record links to both unchanged
timeline entries. Clinicians can resolve the warning; patients cannot access it.

The same deterministic extractor also compares human-authored demo facts. Authority
is explicit: clinician-authored facts outrank staff/nurse human notes, which outrank
AI-scribed or patient-derived facts. Lower-authority evidence is retained unchanged
with provenance to both timeline entries. Equal-authority contradictions (including
staff versus staff) remain open with `clinician_review_required`; the UI labels both
as sources and does not invent an authoritative truth. This remains deliberately
limited to the synthetic medication/dosage, allergy-status, and follow-up vocabulary.

AI-derived patient-facing instructions reuse `TimelineEntry(type=instruction)` plus
a one-to-one approval metadata record. They are created as `draft`, must point to a
same-patient AI timeline source with resolvable provenance, and become patient-visible
only after a clinic-scoped clinician approves them. Staff, patient, and admin cannot
approve or reject. Rejected items stay internal. Editing or reverting approved
AI-derived content returns it to `draft`, clears approval metadata, preserves immutable
versions, and requires re-approval. Existing manually clinician-authored instructions
remain inherently clinician-approved for backward compatibility. Approval, rejection,
and invalidation audits store status transitions only—never instruction or AI text.

### Mock delivery and post-send correction

Patient delivery is explicitly simulated. A delivery binds clinic, patient, instruction,
masked destination, channel/purpose, actor, and the exact immutable EntryVersion approved
by the clinician. It never reads mutable TimelineEntry content as the sent copy.

```text
created → queued → simulated_sent → simulated_delivered
              ↘ failed

approved copy edited/reverted:
created/queued → superseded
simulated_sent/simulated_delivered → correction_required
corrected version → clinician re-approval → new replacement delivery
old correction_required delivery → superseded
```

Only allowlisted server transitions are accepted. No receipt means the record remains
`simulated_sent`; generated/queued never means delivered. Invalid and no-op transitions
create no successful audit. Delivery audits store status metadata only. Patients see
masked destinations and safe states, not provider references or internal content.

The seeded failed `appointment_link` fixture demonstrates that creating a link/message
does not prove receipt. This repository sends no SMS or WhatsApp and has no real delivery
receipt. An already sent copy cannot be recalled: the safe workflow sends a separately
approved correction and preserves both immutable versions and both delivery records.
Failed deliveries accept only server-defined safe reason codes:
`invalid_destination`, `channel_unavailable`, `receipt_unavailable`,
`provider_timeout`, or `provider_rejected`. Free text, provider error bodies, clinical
content, names, phone numbers, and unknown codes are rejected before persistence; audit
metadata continues to contain only status transitions.

Evidence confidence is computed when highlights are read; it is not stored as a
model-generated opinion. An exact entry pointer and exact source-span match are
required. A recognized deterministic clinical fact with no open conflict is `HIGH`;
exact evidence without a structured match is `MEDIUM`; a structured entity mismatch
is `LOW` and requires review. Missing/broken provenance, a missing source span, or an
open contradiction produces `ABSTAIN`/`Needs review`, so the item is not presented as
a normal trusted fact. Clinician confirmation can elevate otherwise exact evidence,
but cannot repair broken provenance or override an open conflict. The response adds
the level, concise reason, review flags, and each verification outcome without using
an LLM or an arbitrary percentage.

Extraction and generation are separate trust boundaries. Deterministic extractors
recognize only the documented synthetic medication, allergy, and follow-up vocabulary
for scoring, confidence, and conflict checks. The summarizer may paraphrase validated
redacted input, but its output never supplies its own confidence and cannot directly
become patient-visible. Broken evidence or failed privacy validation causes abstention;
AI-derived patient instructions remain draft until a clinician approves them.

## 13. Revision and version control

Editable notes use immutable full snapshots in `EntryVersion`. Updates require `expected_version`; stale same-entry writes return HTTP `409`, while separate entries remain independent. Revert restores a selected snapshot as a new version. `AuditLog` stores actor/action/status metadata only, never clinical content. It covers entry edit/revert plus highlight decisions, comment resolution changes, assignment completion/reopening, and conflict resolution. No-op and unauthorized requests do not create successful-action events. Git history is organized into feature commits; runtime databases and build artifacts are ignored.

## 14. Self-learning importance mechanism

This is an adaptive heuristic, not an ML model. The base combines risk, recency, unresolved actions, clinical entity, and clinician confirmation. Clinic-scoped feedback adds:

- accepted entity `+5`; rejected entity `-2`
- accepted source entry type `+2`; rejected source entry type `-1`
- total learned bonus capped to `[-10, +25]`

Only clinicians accept/reject. Identical decisions are idempotent; changing a decision reverses previous counters. `GET /importance-preferences` exposes counts, weights, and explanations.

Adaptive feedback is intentionally bounded because user behavior can be sparse,
biased, or mistaken. Preferences are clinic-scoped, inspectable, and capped; they do
not change source evidence, authority, Evidence Confidence, or patient approval. The
clinical safety floor is applied after learning, so repeated rejection cannot demote
critical allergy, unresolved dosage-conflict, medication-change, or follow-up classes
below their configured minimum.

After the learned adjustment, a centralized deterministic safety policy enforces
minimum score/risk floors: allergy HIGH/50; unresolved medication dosage conflict
HIGH/65; recent or unresolved medication change MODERATE/35; and unresolved clinical
follow-up MODERATE/50. Suggestion responses add base, learned, adjusted, floor, final,
and `floor_applied` fields. Non-critical categories remain fully responsive to
positive and negative feedback.

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
- Tenant isolation has two tested application-layer boundaries, but no database row-level
  security, authenticated clinic membership, or composite tenant foreign keys.
- PHI detection is deterministic pattern matching, not production clinical NER/DLP.
- External-provider retries, rate limits, and operational monitoring are not implemented.
- Preference updates are not designed for multi-process high-contention workloads.
- Data decay is a representation preview, not physical cold-tier storage.
- No browser E2E suite, voice capture, real notification provider/receipt, phone-message
  recall, production OTP/identity proofing, or deployment configuration.
- Phase 3 adds tables through prototype `create_all`; there is still no migration
  framework. Existing synthetic runtime databases must be recreated for this schema.

### Warm-path Glance benchmark

Run the repeatable backend approximation from `backend/`:

```bash
python scripts/benchmark_glance.py --requests 200 --warmups 20
```

Final-submission measurement on Windows 11, Python 3.12.13, FastAPI 0.141.1,
SQLAlchemy 2.0.52, and in-memory SQLite: 200 measured requests after 20 warmups,
median 5.308 ms and P95 6.540 ms for
`GET /patients/patient-demo-001/highlights`. This in-process TestClient measurement
includes routing, authorization, SQLAlchemy query work, and serialization, but
excludes network latency, other frontend requests, and browser rendering. It is a
warm-path approximation, not a production SLA result.

## 17. Synthetic-data security notice

**Use synthetic data only.** Seeded names, identifiers, encounters, comments, transcripts, and clinical facts are fictional. This prototype is not an EHR, does not provide medical advice, and is not approved for real PHI. TLS and encryption at rest are deployment assumptions, not implemented infrastructure here.
