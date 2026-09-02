# Real-Clinic Failure Scenario Matrix

## Verdict definitions

- **SURVIVES**: the current implementation handles the scenario, with directly traceable code and adequate automated evidence.
- **PARTIAL**: some behavior exists, but the first real user failure, an important edge case, or adequate evidence remains.
- **DOES NOT**: the capability is absent or the current implementation cannot safely support the scenario.

## Evaluation template

Each scenario records:

- Verdict
- Classification
- Where
- What breaks first
- What could break later
- Improvement
- Evidence
- Remaining limitation

## Scenario evaluations

### Scenario 1 — Patient without email / phone-first access

- **Verdict:** DOES NOT
- **Classification:** Missing
- **Where:** Current identity is only three development headers in `backend/app/auth.py:22-39`; no User, phone identity, OTP, session, or delivery model exists. `frontend/src/App.tsx:39-49` hard-codes demo identities.
- **What breaks first:** A patient cannot enroll, authenticate, or access the system using a phone number; they can only be simulated by selecting a demo role.
- **What could break later:** Treating client-supplied headers as identity would allow impersonation outside the local demo.
- **Improvement:** Phase 3 should add a synthetic phone-first identity contract and explicit prototype verification/session boundary without requiring email.
- **Evidence:** Repository model/route inventory; `test_rbac_scope.py::test_protected_endpoint_requires_development_identity` proves only that headers are required, not that identity is authenticated.
- **Remaining limitation:** Production OTP, account recovery, consent, device binding, and identity proofing would remain external services.

### Scenario 2 — Clinic-isolation single point fails

- **Verdict:** SURVIVES
- **Classification:** Implemented with two independent application-layer boundaries and directly fault-injection tested across addressable linked objects
- **Where:** The outer boundary remains `require_patient_access`, specifically `user.clinic_id != patient.clinic_id`, in `backend/app/services/authorization_service.py:29-34`; it preserves role/self/ownership authorization and the normal `403` contract. The independent inner boundary is `backend/app/services/clinic_scope_service.py:30-246`: every patient or linked-object query includes `Patient.clinic_id`, joining EntryVersion and AuditLog through TimelineEntry (`:69-102`), comments through entry (`:137-167`), and assignments, conflicts, and approvals through their owning patient (`:170-246`). Importance preferences retain their direct `clinic_id` predicate.
- **What breaks first:** If only the outer comparison fails, the original blast radius would be every addressable Clinic A record whose ID is known or guessed. Phase 2 now prevents that failure mode: the inner SQL predicate returns no foreign-clinic object and routes use non-disclosing `404` semantics before content access, association, persistence, or successful-action audit creation.
- **What could break later:** A future route that bypasses both the authorization guard and scoped-query calling convention, forged development identity headers, or direct database access could still violate isolation. Role/visibility checks remain separate and must not be replaced by tenant filtering.
- **Improvement:** Require all new tenant-linked routes to use the centralized scoped-query service; in production add authenticated clinic membership, migration-backed tenant constraints/composite keys where practical, and database row-level security or an equivalent independently operated data boundary.
- **Evidence:** `backend/tests/test_clinic_isolation_defense.py:239-329` monkeypatches each route module's effective outer guard to a no-op. Its 17-case matrix proves Clinic B receives `404` for known Clinic A patient, timeline, decay, entry, version, audit, highlight, comment, assignment, conflict, approval, and AI-scribe IDs/actions; it also proves no clinical markers, state changes, or successful AuditLog events escape. Separate cases prove same-clinic access still works, cross-tenant assignment-entry injection is rejected, and importance preferences remain clinic-filtered. Phase 2 focused result: 20 passed; complete backend result: 119 passed.
- **Remaining limitation:** This verdict is limited to the repository's tested application paths and asserted development identities. SQLite has no row-level security, headers are forgeable, and there is no authenticated membership or database-level tenant policy.

### Scenario 3 — PHI escaping through logs, errors, or metadata

- **Verdict:** PARTIAL
- **Classification:** Implemented and directly tested for AI-scribe success, redaction-withheld, provider-failure, response, and audit paths; infrastructure-wide controls remain unproven
- **Where:** `backend/app/services/ai_scribe_service.py` one-way transforms the external source identifier to `src_sha256_<digest>` before logging or persistence, then logs only that opaque reference, interaction type, provider category, redaction count, and sanitized outcome. It never logs Provider exception objects or response bodies. `backend/app/routes/ai_scribe.py` returns fixed safe messages. Trust audit metadata remains allowlisted in `backend/app/services/audit_service.py`. The repository still has no reverse-proxy/crash-dashboard integration, third-party processor inventory, or retention/deletion policy.
- **What breaks first:** The tested AI-scribe boundary rejects error-body leakage, but an unrelated future route/logger or infrastructure access/error log could still capture request context because there is no deploy-time organization-wide logging/DLP enforcement.
- **What could break later:** Framework, reverse-proxy, hosting, crash-report, and third-party retention behavior cannot be proven from this repository.
- **Improvement:** Add deployment-specific safe logging configuration, log-field allowlists, retention/deletion controls, third-party processor review, and production log scanning before real-clinic use.
- **Evidence:** Existing AI/redaction/audit privacy tests plus `test_ai_provider_failures.py::test_typed_provider_failures_safely_abstain_without_entry_or_audit`, `::test_unexpected_provider_error_body_is_never_logged_or_returned`, and `::test_external_source_id_is_stably_opaque_across_response_and_persistence`.
- **Remaining limitation:** Pattern-based tests cannot prove absence of every PHI type in production infrastructure logs.

### Scenario 4 — Redaction/validation must precede provider invocation

- **Verdict:** SURVIVES
- **Classification:** Implemented and directly tested for the supported synthetic patterns
- **Where:** The only provider gateway remains `ingest_synthetic_transcript`: external source ID → opaque source reference, then transcript `redact_phi` → `validate_redaction` → early `redaction_withheld` or `provider.summarize`. Entry persistence occurs only after a non-empty successful provider result, and uses only the opaque source reference.
- **What breaks first:** Unsupported PHI formats or names outside deterministic recognition may pass; the required call order itself does not fail.
- **What could break later:** A new provider entry point could bypass this single ingestion service unless architectural enforcement/tests cover it.
- **Improvement:** Keep all future provider integrations behind this gateway and extend deterministic PHI recognition only with clinically reviewed synthetic fixtures.
- **Evidence:** `test_ai_scribe.py::test_provider_receives_only_redacted_text`; `test_redaction_validation.py::test_remaining_phone_and_id_withhold_without_provider_or_entry`; Phase 1 timeout/503 tests inspect the encoded external request and prove it contains placeholders rather than raw name, IC, or phone.
- **Remaining limitation:** This is synthetic deterministic DLP, not clinically validated PHI detection.

### Scenario 5 — Clinic B onboards next Monday

- **Verdict:** PARTIAL
- **Classification:** Application query isolation now has a tested second boundary and a second clinic can be seeded, but there is no supported onboarding or production multi-clinic operating model
- **Where:** `Patient.clinic_id`, clinic-scoped importance preferences, and centralized linked-object clinic queries exist (`backend/app/models/patient.py:12-14`; `backend/app/models/importance_preference.py:8-16`; `backend/app/services/clinic_scope_service.py`). `clinic-demo-002` is seeded (`backend/app/services/seed.py:79-87`). There is still no Clinic model, User/ClinicMembership model, migration framework, provisioning command, clinic administration UI, or deployment configuration.
- **What breaks first:** Staff for Clinic B cannot be provisioned or authenticated as members. An operator must manually invent header values and insert data; the frontend remains hard-coded to Clinic A and Maya Chen (`frontend/src/App.tsx:39-49`).
- **What could break later:** Demo startup `merge` operations can overwrite fixed rows; all clinics share one SQLite file and deployment; tenant IDs are derived through patient relationships rather than consistently stored/constrained; backup, deletion, key rotation, observability, and capacity cannot be managed per clinic.
- **Improvement:** Required changes are explicitly separated: **config**—clinic display/config, allowed origins, provider/channel settings, secrets, and feature flags; **schema**—Clinic, User, and ClinicMembership, tenant ownership constraints/indexes, and migration versioning; **identity/membership**—replace asserted headers, verify clinic-role membership, and handle one user in multiple clinics; **data migration**—create Clinic A/B, backfill ownership, detect orphan/cross-tenant links, and remove production-startup demo seed overwrite; **deployment/operations**—managed database and migrations, TLS/secrets/encryption, backup/restore, tenant-aware monitoring, capacity planning, and incident response; **application/product**—onboarding workflow, clinic administration, invitations, support, and offboarding.
- **Evidence:** Current second-clinic seed, existing normal-scope tests, and `backend/tests/test_clinic_isolation_defense.py` prove application-layer isolation even when the outer guard is disabled. No onboarding, authenticated membership, migration, production deployment, or administration test exists.
- **Remaining limitation:** Phase 2 improves isolation readiness only. Clinic B still cannot safely launch next Monday without the listed identity, schema, migration, operations, and product work.

### Scenario 6 — Multilingual/code-switched clinical transcript

- **Verdict:** DOES NOT
- **Classification:** Missing
- **Where:** `AiScribeRequest` accepts one undifferentiated text string in `backend/app/schemas/ai_scribe.py:15-20`; no language segment, speaker, timestamp, or uncertainty schema exists.
- **What breaks first:** If a trilingual sentence is manually submitted as text, the deterministic mock normalizes and truncates it without language awareness (`backend/app/services/summarization_provider.py:13-22`). The system cannot state what ASR produced, preserve which phrase was Malay/English/Hokkien, or connect extracted facts to timed multilingual evidence. Conflict extraction recognizes only a small English demo vocabulary, so downstream facts, conflicts, confidence and ranking may omit or misclassify non-English content.
- **What could break later:** Medication names/dosages may be normalized incorrectly without visible uncertainty or human confirmation.
- **Improvement:** Phase 6 should add a synthetic transcript-segment contract with language, speaker, timestamp, text, and confirmation state.
- **Evidence:** No multilingual fixtures/tests or matching model/API/UI were found.
- **Remaining limitation:** Real ASR accuracy and dialect support would remain provider/device concerns.

### Scenario 7 — Allergy mentioned at minute two: during or after consult

- **Verdict:** DOES NOT
- **Classification:** Missing; only post-submission text processing exists
- **Where:** `/ai-scribe` processes a complete transcript synchronously (`backend/app/routes/ai_scribe.py:21-63`). No stream/session state, partial transcript, timed segment ingestion, or live allergy warning exists.
- **What breaks first:** The product cannot honestly warn during a live consultation; it can only create or withhold a note after receiving complete text.
- **What could break later:** Users may mistake post-processing conflict detection for real-time safety monitoring.
- **Improvement:** Phase 6 should explicitly model received/partial/final/withheld states and label allergy detection as post-session unless a real streaming contract is implemented.
- **Evidence:** No streaming endpoints, state models, tests, or UI were found; README already states voice capture is absent.
- **Remaining limitation:** Production streaming ASR, latency, speaker diarization, and medical term accuracy remain out of scope.

### Scenario 8 — External provider timeout

- **Verdict:** PARTIAL
- **Classification:** Backend timeout, safe abstention, and persistence behavior are implemented/tested; clinician-facing waiting/recovery UI is absent
- **Where:** `AI_SCRIBE_PROVIDER_TIMEOUT_SECONDS` configures a bounded 0.1–120 second external-provider deadline in `backend/app/services/summarization_provider.py`. Socket/URL timeout becomes `provider_timeout`; the route returns a fixed 504 abstention body and creates no entry.
- **What breaks first:** A 45-second hang is cut off at the configured deadline, but the existing frontend has no AI-scribe ingestion screen or waiting/timeout/retry state, so the clinician experience is only an API contract.
- **What could break later:** A synchronous request still occupies a worker until the deadline. There is intentionally no retry, cancellation, circuit breaker, queue, or distributed outage coordination.
- **Improvement:** A later UI/evaluation phase should expose waiting and retry guidance; production architecture would require bounded queues, cancellation, circuit breaking, and monitoring.
- **Evidence:** `test_ai_provider_failures.py::test_openai_provider_timeout_uses_configured_deadline_and_abstains` proves the configured 0.25-second deadline is passed to the provider and no Timeline Entry is returned; the parameterized failure test proves no entry or audit change.
- **Remaining limitation:** Circuit breaking, queueing, cancellation, rate limits, and distributed tracing would remain production work.

### Scenario 9 — Provider unavailable / deterministic degradation

- **Verdict:** PARTIAL
- **Classification:** Runtime 503/malformed/empty failures safely abstain and default mock is explicitly labeled; broader degraded Glance behavior and operational configuration remain incomplete
- **Where:** Provider failures are typed as `provider_unavailable` or `invalid_provider_response`; fixed 503/502 responses contain no Provider body and persist no ordinary AI entry. Default offline output carries `generation_mode=rule_derived_mock` and a Rule-derived mock message rather than pretending to be an external-model result.
- **What breaks first:** The failed consult produces no new summary, which is the safe policy. Existing Glance items remain visible but are not connected to outage time or explicitly marked stale. There is no AI-scribe frontend workflow displaying the abstention.
- **What could break later:** Explicit `openai` mode without a key still selects the labeled mock rather than surfacing a configuration error; there is no provider health monitoring, SLA, or outage history.
- **Improvement:** Add operational configuration validation/health visibility and UI handling in a later phase without weakening the current no-entry abstention rule.
- **Evidence:** `test_ai_provider_failures.py` covers HTTP 503, typed unavailable, malformed JSON, empty responses, unexpected error bodies, no persistence/audit changes, and explicit mock labeling.
- **Remaining limitation:** Reliable external operation still needs retries with budgets, monitoring, and provider SLAs.

### Scenario 10 — Concurrent edits and recovery from 409

- **Verdict:** PARTIAL
- **Classification:** Database safety implemented/tested; user recovery incomplete
- **Where:** Expected-version comparison and uniqueness race handling in `backend/app/services/revision_service.py:128-160`; 409 response in `backend/app/routes/entries.py:58-71`; local textarea in `frontend/src/App.tsx:488-515`.
- **What breaks first:** The stale write is safely rejected, but the frontend shows no actionable conflict message because `requestJson` discards response details and edit handling has no recovery flow.
- **What could break later:** Users may refresh and lose their local draft or manually overwrite after copying without a comparison view.
- **Improvement:** Phase 4 should retain draft text, expose current server version/content safely, and provide refresh/copy/retry or explicit merge choices.
- **Evidence:** `test_concurrent_edits.py::test_stale_same_entry_edit_is_rejected_with_409` and `::test_permitted_edits_to_different_entries_are_independent`.
- **Remaining limitation:** SQLite tests do not prove multi-process transaction behavior under production load.

### Scenario 11 — Appointment link generated but never received

- **Verdict:** DOES NOT
- **Classification:** Missing
- **Where:** Patient instructions have approval status only (`backend/app/models/patient_instruction.py`); no Message/DeliveryAttempt model or adapter exists.
- **What breaks first:** The application can create an instruction/action but has no appointment-link generator or sender. The first failed assumption is that creating or displaying a link inside the application means a phone/WhatsApp/SMS provider accepted and delivered it; no destination, queue, provider response, receipt, retry, or failure state exists.
- **What could break later:** Staff could assume an approved instruction reached the patient when it only became visible inside the prototype.
- **Improvement:** Phase 3 should add a clearly labeled mock delivery adapter, delivery state machine, timestamps, actor, version, and synthetic destination.
- **Evidence:** No delivery code/tests/UI; README explicitly lists notification delivery as absent.
- **Remaining limitation:** Real delivery receipts and channel compliance require an external provider.

### Scenario 12 — Patient-facing summary contains one wrong dosage

- **Verdict:** PARTIAL
- **Classification:** Human gate and revision protection exist before in-app patient visibility; phone delivery and post-send correction do not
- **Where:** AI-scribe summary generation persists an internal AI entry after redaction/validation (`backend/app/services/ai_scribe_service.py:69-87`). An AI-derived patient instruction must reference an AI source, starts Draft, and only a clinician may approve it (`backend/app/routes/patients.py:93-136`; `backend/app/services/patient_instruction_service.py:16-68`). Editing approved content invalidates approval and preserves versions (`backend/app/services/revision_service.py:102-160`). There is no phone delivery record.
- **What breaks first:** A wrong dosage cannot directly reach the prototype patient view because the clinician gate blocks Draft content, but the gate only requires resolvable provenance—not a structured dosage comparison or explicit checklist confirming dose/current version. If a clinician approves the error, it becomes visible in the portal; there is no real phone path to trace.
- **What could break later:** Editing the current instruction could make the internal record correct while the patient retains an untracked obsolete message.
- **Improvement:** Before approval, require the clinician to inspect the immutable source, extracted medication/dose, conflict state, and exact instruction version. Delivery must reference that approved immutable version. If already sent, preserve the original delivered copy, mark it superseded/corrected, create and reapprove a corrected version, and send a separately traceable correction; never imply the old phone message can be silently edited.
- **Evidence:** `test_patient_instruction_approval.py::test_editing_approved_instruction_invalidates_approval_and_preserves_version` covers pre-delivery approval invalidation only.
- **Remaining limitation:** Channel-specific recall is generally impossible; correction delivery must be explicit.

### Scenario 13 — Nurse allergy vs AI “no known allergy” contradiction

- **Verdict:** PARTIAL
- **Classification:** Allergy contradiction machinery exists, but the original nurse-first then AI-later ordering is not detected
- **Where:** Allergy extraction and negation handling exist in `backend/app/services/conflict_service.py:70-81`; conflict creation can preserve both sources and rank staff above AI in `:103-197`; open conflicts make Evidence Confidence abstain (`backend/app/services/evidence_confidence_service.py:70-95`) and the UI shows both sources (`frontend/src/App.tsx:344-366`). However, `detect_conflicts_for_entry` immediately returns for a changed SYSTEM/AI entry (`backend/app/services/conflict_service.py:123-131`), and AI ingestion does not call conflict detection (`backend/app/services/ai_scribe_service.py:69-87`).
- **What breaks first:** With the exact original order—nurse records Penicillin allergy, then the patient tells the AI “no known allergies”—both entries appear in the timeline but no ConflictRecord is created by the later AI entry. The clinician may continue to see an existing allergy highlight if one was created, but receives no deterministic warning that the new AI statement contradicts it.
- **What could break later:** Even supported conflicts miss allergens/phrasings outside Penicillin/Sulfa/simple negation, and mutable source edits can change the displayed evidence after conflict creation.
- **Improvement:** Phase 5 should run conflict comparison whenever a relevant AI/patient entry is created as well as on human edits, preserve both sources, apply staff-over-AI authority without silently deleting evidence, make the Glance item Needs Review, and add the exact nurse-first/AI-second scenario test.
- **Evidence:** Current allergy extractor test and AI-first/human-later conflict tests pass, but no test exercises nurse-first/AI-second creation. Static call-path inspection proves the later AI entry does not trigger detection.
- **Remaining limitation:** This is not general medical NLP and cannot establish clinical truth independently.

### Scenario 14 — Verifiable Evidence Confidence metric

- **Verdict:** SURVIVES
- **Classification:** Implemented and directly tested
- **Where:** Deterministic inputs and mapping in `backend/app/services/evidence_confidence_service.py:29-133`; concise UI display in `frontend/src/App.tsx:277-293`.
- **What breaks first:** Unsupported structured facts often receive MEDIUM rather than clinically validated extraction confidence; broken evidence safely abstains.
- **What could break later:** Mutable source entries cause old confidence to become ABSTAIN rather than resolving the original version.
- **Improvement:** Phase 5 should retain deterministic definitions and Phase 4 should bind confidence to immutable source versions.
- **Evidence:** All five tests in `backend/tests/test_evidence_confidence.py`, including determinism, open conflict, broken provenance, and no provider call.
- **Remaining limitation:** It is evidence verification, not probability of medical correctness.

### Scenario 15 — Fatigue dismissals and adaptive-ranking bias

- **Verdict:** PARTIAL
- **Classification:** Safety floors/caps implemented and tested; bias controls incomplete
- **Where:** Clinic-scoped counters and cap in `backend/app/services/adaptive_importance_service.py:10-54`; floors applied after learning in `backend/app/services/importance_service.py:139-185`; feedback updates in `backend/app/services/highlight_service.py:87-127`.
- **What breaks first:** One rejection immediately changes future ranking, and rejected noncritical items disappear from Glance; there is no minimum sample or explicit undo control in the UI.
- **What could break later:** Exposure bias reinforces categories already shown, stale preferences persist indefinitely, and sparse feedback may encode individual fatigue.
- **Improvement:** Phase 5 should add feedback undo, minimum samples, decay/offline audit, and an exploration or review mechanism while retaining caps and safety floors.
- **Evidence:** `test_self_learning_importance.py`; `test_importance_safety_floors.py` proves repeated allergy rejection cannot cross the HIGH floor.
- **Remaining limitation:** Adaptive heuristics are not clinically validated learning and should remain decision support only.

### Scenario 16 — Source edited after highlight creation

- **Verdict:** PARTIAL
- **Classification:** Staleness is detected; original evidence is not resolvable from the highlight
- **Where:** Highlight stores mutable `entry_id`, substring, and entry anchor (`backend/app/models/highlight.py`; `backend/app/services/highlight_service.py:65-80`). Confidence rechecks current content and abstains when span is missing (`backend/app/services/evidence_confidence_service.py:29-68`). Entry versions retain snapshots (`backend/app/models/revision.py:9-26`).
- **What breaks first:** After source editing, clicking the highlight opens the new entry content, not the original evidence; confidence may say Needs Review but cannot navigate to the original version.
- **What could break later:** A coincidentally repeated span could still verify against the wrong version/context.
- **Improvement:** Phase 4 should store source version/snapshot identity and mark stale or resolve directly to the immutable version.
- **Evidence:** Existing provenance tests validate only current entry/span; no source-mutation test exists.
- **Remaining limitation:** External synthetic URI targets are identifiers only; raw transcript source viewing is not implemented.

### Scenario 17 — Complete consult intelligence and audience-readiness rubric

- **Verdict:** DOES NOT
- **Classification:** Some downstream text trust components exist, but the end-to-end consult-audio capability and most scoring dimensions are absent
- **Where:** The only ingestion contract accepts one completed text transcript and interaction type (`backend/app/schemas/ai_scribe.py:9-20`); it has no audio stream, acoustic metadata, language/speaker/timestamp segments, captured-term uncertainty, or audience target. Existing provenance, deterministic extraction, conflicts, revisions, and role filtering are separate partial building blocks, not this complete product.
- **What breaks first:** A real noisy consult cannot enter the system as streaming audio. Therefore code-switching, exact medication/dosage confirmation, live facts, and distinct audience summaries cannot be reliably produced from the actual consultation.
- **What could break later:** Even if an ASR transcript were pasted in, unsupported languages and clinical phrasing can corrupt deterministic extraction; highlights cite mutable entries; a journal lookup could be mistaken for proof of what this patient said; one summary reused across roles could expose internal detail or omit necessary clinical evidence.
- **Improvement:** Phase 6 must cover every original scoring dimension, while depending on Phase 4 immutable provenance: **real consult audio streaming**—define honest received/partial/final/failed session states rather than claiming existing support; **noisy-clinic ASR**—record synthetic acoustic/noise metadata, segment confidence/alternatives and human correction; **code-switching**—preserve per-segment language for English/Mandarin/Tamil and mixed statements; **medical terminology and dosage capture**—store the captured phrase, alternatives such as Montelukast 20 mg versus 50 mg, source timestamp, and explicit clinician/patient confirmation; **journal/reference-assisted verification**—use references only to validate terminology/plausibility and surface citations, never to decide what the patient actually took; final patient fact requires human confirmation; **multilingual readiness**—test synthetic multilingual fixtures without claiming production ASR quality; **intact provenance**—link facts and all summaries to immutable audio/transcript segments/versions; **fact extraction and mutation robustness**—test edits, corrections, stale facts, conflicts and re-extraction without silently changing old evidence; **distinct summaries**—Clinician Summary retains evidence/conflicts/clinical detail, Staff Summary contains operational tasks/follow-up, and Patient Summary uses plain approved language and remains behind the clinician approval gate.
- **Evidence:** Dimension-by-dimension current state: real streaming audio—absent; noisy-clinic ASR—absent; code-switching—absent; medical terminology/dosage capture—PARTIAL only for deterministic completed English text in `backend/app/services/conflict_service.py:32-91`; journal/reference boundary—absent, while clinician approval exists only for patient instructions; multilingual readiness—absent; intact provenance—PARTIAL because current highlights target mutable entries; fact extraction/mutation robustness—PARTIAL due limited demo vocabulary, conflict/revision support, and missing immutable-source mutation tests; distinct audience summaries—absent, because `can_view_entry` role filtering in `backend/app/services/authorization_service.py:42-62` is not audience-specific generation.
- **Remaining limitation:** A prototype contract and synthetic fixtures cannot validate real microphones, noisy-clinic ASR, language coverage, clinical accuracy, journal quality, or patient comprehension; those require provider evaluation and clinical/human studies.
