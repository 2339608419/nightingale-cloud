# Phase 0 Findings

## Phase 1 initial inspection

- Phase 1 starts from confirmed HEAD `058020d428b0a597dec14363513aae1ba8b9735c`; the pre-existing root changes and untracked user materials remain excluded.
- The existing call order is already centralized in `ingest_synthetic_transcript`: `redact_phi` → `validate_redaction` → `provider.summarize`. Validation failure returns before provider invocation and before entry creation.
- Provider failures currently escape without a typed/sanitized API outcome. The external provider uses a hard-coded 30-second `urlopen` timeout, does not distinguish timeout, HTTP 503/unavailable, or invalid/empty response, and has no focused failure tests.
- The default deterministic mock is reliable offline and named `deterministic-mock`, but the API does not expose a structured generation mode. Missing OpenAI configuration silently selects mock, which should remain documented rather than represented as an external-model result.
- Current AI-scribe logs contain source ID, interaction type, redaction count, and validation reason only. Existing focused tests prove fixture name/IC/phone absence, but provider error paths and transcript clinical-body leakage are not tested.
- The safest minimal failure policy is abstention: typed provider failures return a sanitized result, create no Timeline Entry, and do not fall back at runtime to a result that could be mistaken for model output. No retry is required for this synchronous prototype.

## Phase 1 verified result

- The provider deadline is configurable through `AI_SCRIBE_PROVIDER_TIMEOUT_SECONDS`, defaults to 30 seconds, and is bounded to 0.1–120 seconds. Invalid/out-of-range configuration safely uses the default.
- External timeout, HTTP/network unavailability, malformed JSON/shape, and empty summaries are mapped to sanitized outcomes. Error bodies and exception strings are neither logged nor returned.
- Runtime external-provider failure uses safe abstention and creates no Timeline Entry or audit event. The service intentionally performs no retry.
- The offline mock remains the default and is now explicitly identified as `rule_derived_mock`; external-provider success is `external_model`, and dependency-injected test doubles are labeled separately.
- Compatibility is additive: existing `status=created|withheld`, summary, entry, provenance, redaction, and validation fields remain; new `outcome`, `generation_mode`, and `safe_abstention` fields explain the result. Provider failures use HTTP 504/503/502 while redaction withholding remains HTTP 200.
- Scenario 3 remains PARTIAL because repository tests cannot prove reverse-proxy, crash dashboard, hosting, third-party, or retention behavior. Scenario 4 remains SURVIVES. Scenarios 8 and 9 remain PARTIAL because backend safety is now proven but clinician-facing outage UI and production resilience/operations are absent.
- Initial verification before staged review: focused suite 25 passed; complete backend suite 98 passed; frontend TypeScript checks and production Vite build passed. The final post-correction counts are recorded below.

## Phase 1 staged-review correction

- Staged review identified that the client-controlled `source_id` bypassed transcript redaction through logs and provenance. The Timeline Entry ID was already a server-generated UUID, but provenance was copied into the initial EntryVersion and API response.
- The minimal correction derives `src_sha256_<digest>` with SHA-256 plus a fixed domain separator immediately inside the ingestion service. The external identifier is never logged or persisted; only the deterministic opaque reference is used in logs and `synthetic://` provenance.
- No raw-source field is added. Request-controlled log fields are now limited to an enum interaction type plus the opaque source reference; provider name is server-selected/dependency-injected, validation reason is fixed by server code, and no free text is logged.
- Final post-correction verification: focused suite 26 passed; complete backend suite 99 passed; frontend TypeScript checks and production Vite build passed.

## Baseline

- Branch: `master`
- HEAD: `84834e38f6b93b8a30d616102bb2fbb6c2ad05f7`
- HEAD message: `docs: add final technical brief`
- Authoritative scenario/deliverable source: `C:\Users\zclin\.codex\attachments\35e2b607-3cc7-43f8-9453-bfeccac537d8\pasted-text.txt`
- Deadline: Thursday, 3 September 2026, 18:00 SGT
- Required delivery set: working repository and scenario 1–16 tests; setup/run README; 2–3 page brief covering scenarios 1–17 and honest failures/changed assumptions; demo video covering as many scenarios 1–16 as possible.
- Existing tracked user changes excluded: root `task_plan.md`, `findings.md`, `progress.md`
- Existing untracked user/output files excluded: `Demo Video.mp4`, `Resume-Zhanchen Lin.pdf`, `output/`, `read.md`

## Evidence classification

Each scenario is classified as one of:

- Implemented and directly tested
- Implemented but insufficiently tested
- Demo/mock/contract only
- Missing

Each verdict cites concrete code and test locations or explicitly records that evidence is absent.

## Architecture findings

- Tracked architecture is a React/TypeScript/Vite client plus FastAPI/SQLAlchemy/SQLite backend, with backend modules separated into models, schemas, routes, services, and database setup.
- The frontend build script performs TypeScript no-emit checks for both app and Vite configuration before `vite build` (`frontend/package.json`).
- The current schema includes patients, mutable timeline entries, full entry-version snapshots, metadata-only audit logs, comments, assignments, highlights, clinic-scoped adaptive preferences, conflicts, and one-to-one AI-derived patient-instruction approval metadata (`backend/app/models/`).
- `TimelineEntry` stores mutable `content` and a provenance pointer; `EntryVersion` stores historical content/provenance snapshots. `Highlight.entry_id` and its pointer currently target the mutable entry, not an immutable version. This is an expected Phase 4 risk.
- No dedicated phone identity, delivery, message, multilingual transcript-segment, or audience-summary model appeared in the tracked model inventory.
- Timeline retrieval is patient-ID filtered and newest-first (`backend/app/services/patient_service.py:22-30`). Clinic scope is applied by routes after patient lookup rather than embedded in every service query; this works when every caller remembers the authorization step but creates a single-call-site omission risk for Phase 2.
- Full immutable entry snapshots exist and include content plus provenance pointer (`backend/app/services/revision_service.py:42-58,66-99`). Updates and reverts use an expected version and handle the uniqueness race as a deterministic version conflict (`backend/app/services/revision_service.py:128-210`).
- Collaboration queries are scoped by entry or patient IDs at the service layer; authorization and clinic checks must therefore be verified at every route call site (`backend/app/services/collaboration_service.py`).
- Data decay is a non-mutating preview only; original content remains available and durable keywords/entities are exempt (`backend/app/services/data_decay_service.py:24-66`).
- Route inspection shows patient/clinic authorization precedes reads or writes for comments, assignments, conflicts, entries, highlights, patient instructions, decay preview, and AI scribe (`backend/app/routes/`). Linked assignment entries are additionally required to belong to the requested patient (`backend/app/routes/collaboration.py:125-137`).
- `GET /importance-preferences` is clinic-scoped by the identity header and rejects patients, but it does not load a clinic entity because there is no Clinic model (`backend/app/routes/highlights.py:110-128`). In this prototype, a caller can assert arbitrary development-header identity; this is not a production tenant boundary.
- The 409 response includes the current version and protects database content, but the API does not return the rejected draft or a merge payload. Preservation of the user's typed edit therefore depends on frontend local state and requires frontend inspection for scenario 10.
- The frontend is a single demo patient page with typed API calls, role simulation, Glance, conflicts, timeline, comments, assignments, revision/revert, highlight decisions, and patient-instruction approval (`frontend/src/App.tsx`; `frontend/src/api.ts`; `frontend/src/types.ts`). There is no routing or multi-patient/clinic administration UI.
- Initial loading prioritizes patient/entries/highlights/decay, then fans out comments and versions for every visible entry plus collaboration/trust data (`frontend/src/App.tsx:89-143`). This protects initial Glance rendering from the N-entry fan-out, but larger histories would still create a substantial second-stage request fan-out.
- The generic frontend API error discards the backend response body and returns only `Request failed (<status>)` (`frontend/src/api.ts:22-39`). Thus a 409's `current_version` and explicit timeout/degraded states cannot currently be shown.
- On note-edit 409, the textarea component retains its local typed content because it is not cleared, but `editDemoNote` has no catch and the UI provides no conflict banner, retry, refresh, copy, or merge action (`frontend/src/App.tsx:227-230,488-515`). Scenario 10 protects the database but has incomplete user recovery.
- The frontend contains no AI-scribe transcript ingestion UI, phone-first access, delivery/correction workflow, multilingual segments, streaming state, or audience-specific summary views. Those capabilities cannot be demonstrated through the current UI.
- Runtime persistence defaults to local SQLite and startup calls `Base.metadata.create_all` followed by `seed_demo_data` (`backend/app/database/session.py:8-12`; `backend/app/main.py:21-26`). There is no migration framework or Clinic/User identity table.
- Seed behavior is not purely insert-if-absent: patients, comments, assignments, and highlights use `merge`, so application startup can restore/overwrite fixed demo rows and states (`backend/app/services/seed.py:69-88,216-289,342-363`). This is suitable for a stable demo but unsafe as a production initialization pattern.
- Tests create a fresh in-memory SQLite schema for every test and seed only synthetic fixtures (`backend/tests/conftest.py:12-40`). This gives isolation but does not exercise persistent-database migrations or concurrent multi-process behavior.

## Security and trust findings

- Development identity is supplied by `X-User-Id`, `X-Role`, and `X-Clinic-Id` in `backend/app/auth.py`; this is an authorization prototype, not production authentication.
- Reusable authorization functions exist in `backend/app/services/authorization_service.py` for patient/clinic access, visible-entry filtering, internal comments, AI scribe, highlights, patient-instruction approval, conflict review/resolution, collaboration, entry creation, and entry editing.
- Clinic mismatch is rejected in `require_patient_access`; patient self-access is separately checked. Route inventory shows protected patient, entry, collaboration, highlight, conflict, and AI-scribe endpoints depend on the current-user dependency.
- Patient instruction visibility checks type, approval metadata, and approved status. Only clinicians can make highlight decisions, approve/reject patient instructions, or resolve conflicts.
- Admin conflict access is oversight-only while resolution remains clinician-only.
- Audit and deeper service behavior still require line-by-line inspection; route dependency presence alone is not sufficient evidence.
- The AI-scribe call order is concretely `redact_phi` → `validate_redaction` → provider invocation in `backend/app/services/ai_scribe_service.py:34-71`. Validation failure returns before the provider and creates no timeline entry.
- AI-scribe requests must explicitly declare `synthetic: true` (`backend/app/schemas/ai_scribe.py:15-20`). This is a contract guard, not proof that submitted text is actually synthetic.
- AI-scribe logs record source ID, interaction type, counts, and validation reason, but not transcript or summary text (`backend/app/services/ai_scribe_service.py:58-87`). Focused tests assert the three fixture PHI values do not appear in logs.
- Redaction supports Singapore IDs, Singapore-style phone numbers, title-case two-part names, known synthetic fixture names, and the current patient name (`backend/app/services/redaction_service.py:5-12,38-55`). This is deterministic demo coverage, not a comprehensive PHI recognizer.
- Redaction validation detects remaining configured patterns, verifies protected demo terms/dosages, and rejects empty meaningful output (`backend/app/services/redaction_service.py:58-109`).
- The external provider has a hard-coded 30-second socket timeout (`backend/app/services/summarization_provider.py:52`), but it is not configurable and provider timeout/HTTP/invalid-response failures are not translated into explicit API states or a labeled deterministic fallback. These are Phase 1 gaps.
- Provider selection silently falls back to the deterministic mock unless both explicit `openai` mode and an API key are present (`backend/app/services/summarization_provider.py:70-78`). The successful response identifies the provider, but configuration mistakes do not return a distinct degraded/configuration state.
- Patient-facing AI-derived instructions have a tested draft/approved/rejected gate. Only clinicians can decide; edits invalidate approval; broken source provenance blocks approval; patients remain unable to read AI notes, comments, audits, or conflicts (`backend/tests/test_patient_instruction_approval.py`).
- Entry update/revert audits store version-number metadata, while trust-action audits accept only `from_status` and `to_status` keys (`backend/app/services/revision_service.py:66-99`; `backend/app/services/audit_service.py:10-38`). Clinical content is stored in version snapshots as designed, not in audit metadata.
- Clinical conflict extraction is explicitly limited to Lisinopril/Amlodipine/Metformin, Penicillin/Sulfa, and structured follow-up phrases (`backend/app/services/conflict_service.py:32-91`). It preserves both source entry IDs and uses clinician > staff > AI/patient authority; equal-rank conflict requires clinician review (`backend/app/services/conflict_service.py:103-120,123-197`).
- Evidence confidence is deterministic: mutable source entry resolution, exact substring span verification, structured extraction, and open conflict state determine HIGH/MEDIUM/LOW/ABSTAIN (`backend/app/services/evidence_confidence_service.py:29-133`). No LLM is involved.
- Highlights point to `timeline-entry-{entry.id}` and confidence verifies their span against current mutable content (`backend/app/services/highlight_service.py:65-80`; `backend/app/services/evidence_confidence_service.py:29-68`). After source editing, this can correctly abstain, but it cannot resolve the original highlight to the immutable source version. Scenario 16 is therefore partial.
- Importance is deterministic and explainable. Learned feedback is clinic-scoped and capped to [-10,+25], then centralized safety floors protect allergy, unresolved dosage conflict, recent/unresolved medication change, and unresolved follow-up (`backend/app/services/adaptive_importance_service.py:10-54`; `backend/app/services/importance_service.py:87-185`).
- A single accept/reject immediately changes learned counters; there is no minimum sample, time decay, exposure correction, exploration, or dedicated feedback undo API. Status changes reverse prior counters, but fatigue/bias and unseen-item feedback loops remain Phase 5 gaps.
- Highlight acceptance directly adds 15 points to the existing stored highlight and rejection removes the item from Glance. Future suggestions use learned preferences and safety floors, but existing highlight scores are not globally recomputed after every feedback event (`backend/app/services/highlight_service.py:18-34,87-127`).
- Every currently registered linked-object route was found to resolve the parent patient and call `require_patient_access` before returning or mutating data. This is positive code evidence, but most cross-clinic automated tests exercise patient/entry reads, AI ingestion, conflicts, or patient approval rather than a comprehensive matrix of comment/assignment/highlight/version/audit enumeration and mutation.
- Conflict API exposes both source IDs, roles, authority policy, and resolvable entry anchors while preserving both entries (`backend/app/routes/conflicts.py:28-50`). Those anchors still identify mutable entries rather than immutable source versions.
- The UI visibly separates risk, Evidence Confidence, highlight state, exact-source navigation, conflict authority/review, AI origin, approval state, and data-decay preview (`frontend/src/App.tsx:268-447`). It does not claim unsupported probability confidence.
- Frontend role-based hiding is explicitly labeled demo identity simulation and the code sends development headers on every request (`frontend/src/App.tsx:650-673`; `frontend/src/api.ts:14-38`). Security still depends on backend checks, and identity headers are trivially forgeable outside a trusted demo environment.
- The API's `synthetic: true` literal and synthetic fixture labeling are strong prototype guardrails, but there is no data-classification/DLP enforcement capable of proving arbitrary submitted transcript text is synthetic. Real-clinic use must remain prohibited.

## Test and build findings

- Pytest is configured for `backend/tests` with the backend root on the Python path (`backend/pytest.ini`).
- Frontend production build includes both TypeScript checks and Vite bundling (`frontend/package.json`).
- Execution completed successfully; exact Phase 0 results are recorded below.
- Direct tests prove the provider receives redacted text, raw synthetic transcript values are absent from persisted entry/version content and captured logs, all three supported interaction types map correctly, patient ingestion is forbidden, and clinic scope is enforced (`backend/tests/test_ai_scribe.py`).
- Redaction-abstention tests monkeypatch an unsafe redactor and prove a validation failure invokes no provider and creates no entry (`backend/tests/test_redaction_validation.py:74-103`).
- Core role tests directly bypass the frontend and verify note ownership, patient filtering, missing-identity rejection, and cross-clinic patient/entry reads (`backend/tests/test_rbac_scope.py`). Cross-clinic coverage for all linked entity routes still requires inspection.
- Existing tests directly cover 409 protection and independent different-entry edits (`backend/tests/test_concurrent_edits.py`), snapshot/revert/audit metadata (`backend/tests/test_revision_history.py`), source resolution and exact span presence (`backend/tests/test_highlight_provenance.py`), deterministic confidence and no provider invocation (`backend/tests/test_evidence_confidence.py`), safety floors (`backend/tests/test_importance_safety_floors.py`), and adaptive priority increase (`backend/tests/test_self_learning_importance.py`).
- Conflict tests cover clinician-vs-AI, identical facts, clinician authority, both source anchors, resolution, patient denial, clinic scope, clinician-vs-staff, and staff-vs-staff review (`backend/tests/test_clinical_conflicts.py`; `backend/tests/test_human_conflicts.py`).
- Collaboration tests cover comment mentions/replies/resolution, assignments, and patient denial. Trust-action tests cover metadata-only state events, idempotency, and same-clinic unauthorized attempts (`backend/tests/test_collaboration.py`; `backend/tests/test_trust_action_audit.py`).
- There are no scenario-numbered tests, delivery tests, provider timeout/503 tests, phone-first identity tests, provenance-after-source-edit tests, multilingual transcript fixtures, streaming-state tests, or audience-specific summary tests in the current inventory.
- There is no browser E2E/component test suite. Frontend evidence is currently TypeScript/build validation plus manual demo paths.
- The repository virtual environment provides Python and pytest; frontend dependencies are already present. Verification can run without installing or changing dependencies.
- Phase 0 backend verification: **89 passed, 1 warning in 4.10s** using `backend/.venv/Scripts/python.exe -m pytest -q`. The warning is a third-party `StarletteDeprecationWarning` concerning `httpx` and `starlette.testclient`; it did not fail tests.
- Phase 0 frontend verification: **passed** using `npm run build`. The script successfully completed `tsc --noEmit` for app and Node/Vite configurations, then Vite 8.2.2 production bundling (17 modules, 209.08 kB JS / 64.71 kB gzip; 13.06 kB CSS / 3.43 kB gzip).

## Documentation findings

- `README.md`, `PROJECT_REQUIREMENTS.md`, `FINAL_AUDIT_REPORT.md`, `DEMO_RUNBOOK.md`, and `TECHNICAL_BRIEF_FINAL.md` consistently label the product as synthetic-only and prototype-grade.
- Documentation explicitly disclaims development headers as production authentication, SQLite/create-all as production persistence/migrations, deterministic redaction as production DLP, data-decay preview as physical storage, and the in-process P95 result as a deployed SLA.
- Current known limitations already identify absent provider retries/rate limits/monitoring, browser E2E, voice, notification delivery, and deployment configuration (`README.md:244-268`).
- Documentation reports 89 backend tests and a passing frontend build from the prior submission; Phase 0 will independently rerun rather than rely on those figures.

## Risk-ordered follow-up plan

### Baseline verdict summary

- SURVIVES: 2 scenarios (4, 14)
- PARTIAL: 10 scenarios (2, 3, 5, 8, 9, 10, 12, 13, 15, 16)
- DOES NOT: 5 scenarios (1, 6, 7, 11, 17)

### Recommended dependency and risk order

1. **Phase 1 — PHI boundaries and AI failures (scenarios 3, 4, 8, 9).** Privacy leakage and ambiguous provider failure are the highest safety risks. Establish centralized safe errors/logging and typed timeout/unavailable/abstention states before adding more AI inputs.
2. **Phase 2 — tenant isolation (scenarios 2, 5).** Move clinic scope beneath routes and prove all linked-object paths before adding identities or delivery records that multiply tenant-linked data.
3. **Phase 4 — concurrency UX and immutable provenance (scenarios 10, 16).** Existing version snapshots make this feasible. Bind evidence to immutable versions and make rejected drafts recoverable before delivery can reference an approved version.
4. **Phase 3 — phone-first identity and delivery/correction (scenarios 1, 11, 12).** This depends on tenant membership and immutable approved-version references. Use a clearly labeled mock adapter unless a real service is explicitly authorized.
5. **Phase 5 — conflict/metric/learning hardening (scenarios 13, 14, 15).** Preserve current deterministic confidence, conflicts, caps, and safety floors; add exact allergy contradiction evidence plus bias/undo/minimum-sample controls.
6. **Phase 6 — multilingual transcript contract and audience views (scenarios 6, 7, 17).** Implement honest synthetic segment/state contracts and human confirmation. Do not imply production ASR or live clinical monitoring.
7. **Phase 7 — scenario-indexed regression and UI states.** Add tests named for scenarios 1–16 and browser-visible timeout/degraded/stale/delivery/correction/confirmation states without deleting current tests.
8. **Phase 8 — final documentation.** Reconcile README, brief, matrix, demo runbook, test counts, performance results, changed assumptions, failures, and remaining limitations.

### Authoritative scenario-to-phase mapping

- Phase 1 → scenarios 3, 4, 8, 9: PHI exits/log retention, redaction-before-provider proof, 45-second hang, one-hour 503 degradation.
- Phase 2 → scenarios 2, 5: clinic-isolation single-point failure/blast radius/second defense; Clinic B onboarding across config, schema, identity/membership, migration, and deployment.
- Phase 3 → scenarios 1, 11, 12: no-email phone/WhatsApp identity, end-to-end appointment-link delivery, wrong-dosage patient-summary gate and post-send correction.
- Phase 4 → scenarios 10, 16: simultaneous edits/user awareness and immutable addressable provenance after source mutation.
- Phase 5 → scenarios 13, 14, 15: allergy contradiction at Glance, verifiable Evidence Confidence, and interaction-learning exposure/fatigue bias.
- Phase 6 → scenarios 6, 7, 17: trilingual/code-switched downstream behavior, during-versus-after-consult allergy timing, and the complete audio/ASR/language/terminology/verification/provenance/extraction/audience rubric.
- Phase 7 → scenarios 1–16: scenario-numbered automation or honest absence/contract tests plus visible UI states.
- Phase 8 → scenarios 1–17 and all deliverables: README, 2–3 page brief, scenario matrix, demo plan/video evidence, exact limitations and failed attempts.

### Cross-phase invariants

- Synthetic data only.
- No weakening of server-side RBAC, clinic scope, patient approval, PHI redaction/validation, metadata-only audit, conflicts, or clinical safety floors.
- No claim of real delivery, real-time ASR, production authentication, production multi-tenancy, or deployed performance without direct evidence.
- Each future phase must use a narrow file set, targeted tests, complete regression, staged-diff inspection, and one local atomic commit.
