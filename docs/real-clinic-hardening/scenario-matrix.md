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

- **Verdict:** PARTIAL
- **Classification:** A real, tested synthetic phone-first portal slice exists; verification delivery and production identity remain deliberately mocked/missing
- **Where:** Patient stores only a synthetic phone digest/mask with tenant-scoped `(clinic_id, phone_digest)` uniqueness (`backend/app/models/patient.py`); one-time challenges and expiring sessions store only token digests (`backend/app/models/patient_access.py`). `backend/app/services/patient_access_service.py` returns the same public accepted response shape for known and unknown valid numbers, uses an unpersisted non-redeemable secure-random decoy for unknown numbers, and masks only submitted input. Live consumption is an atomic conditional SQL update over digest/unused/unexpired state; only a successful claim creates a one-hour session in the same transaction. Routes expose only self-scoped approved instructions and safe delivery states.
- **What breaks first:** The local mock returns the one-time token once in the HTTP response because there is no real SMS/WhatsApp provider. Anyone with the known synthetic demo number can complete this local flow; it is not identity proofing.
- **What could break later:** Production use would need out-of-band OTP delivery, throttling, recovery, consent, device/session management, authenticated clinic membership, fraud controls, a production concurrency-capable database, and versioned migrations. Format validation is separately observable by design, but account existence is not.
- **Improvement:** Replace the one-time response token with a compliant external verification adapter, add rate/attempt limits and recovery/session revocation UX, and bind verified identities to production membership without changing the self-only portal contract.
- **Evidence:** `backend/tests/test_phone_access_delivery_correction.py` proves known/unknown response equivalence, non-redeemable decoy behavior, no email requirement, digest-only storage, expiry/replay rejection, two-session atomic claim, same-phone per-clinic resolution, same-clinic uniqueness, self-only approved filtering, and denial of internal data. Post-review focused result: 16 passed; complete backend result: 135 passed.
- **Remaining limitation:** This is explicitly `synthetic_local_mock`; it is not production OTP or authenticated telecom delivery. SQLite two-session evidence is not a production multi-worker/load proof, and existing runtime databases require rebuild because no migration framework exists.

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

- **Verdict:** SURVIVES
- **Classification:** Stale writes remain database-safe and an explicit user recovery flow is implemented/tested for the prototype
- **Where:** Expected-version comparison remains in `backend/app/services/revision_service.py`; authorized structured recovery detail is built only after RBAC/clinic checks in `backend/app/routes/entries.py:41`. `frontend/src/api.ts:24` preserves structured detail and `frontend/src/App.tsx:618` preserves/compares the draft with copy, explicit reload, and cancel-and-keep actions.
- **What breaks first:** The second editor receives `entry_version_conflict`; their draft stays local and nothing is merged or retried automatically. Reloading the entire browser before copying remains a user-controlled way to lose unsaved local state.
- **What could break later:** SQLite and TestClient do not prove distributed multi-process ordering; browser crash/offline recovery is not persisted to durable local storage.
- **Improvement:** Production should use a concurrency-capable managed database and optionally encrypted time-bounded local draft recovery, without automatic clinical-text merge.
- **Evidence:** `test_concurrent_edits.py` proves N→N+1 first save, structured 409, first content retained, rejected draft absent, exactly one new version/audit, unchanged post-first approval/delivery state, no unauthorized/cross-clinic content leak, and independent-entry success. `frontend/tests/conflictRecovery.test.ts` proves typed detail, draft retention, and explicit reload. Manual UI review confirmed the comparison/actions. Phase 4 regression: 83 passed; full backend: 143 passed; frontend logic: 3 passed.
- **Remaining limitation:** No browser E2E or multi-worker production database test exists.

### Scenario 11 — Appointment link generated but never received

- **Verdict:** PARTIAL
- **Classification:** Traceable immutable mock delivery is implemented/tested; no real channel or receipt exists
- **Where:** `backend/app/models/delivery.py:8-66` records clinic/patient, mock channel, masked destination, purpose, entry, immutable approved version, actor, opaque provider reference, replacement, timestamps, and distinct status. `backend/app/services/delivery_service.py:29-155` enforces created → queued → simulated_sent → simulated_delivered or queued → failed. The seed's failed appointment-link fixture (`backend/app/services/seed.py:300-323`) and frontend delivery panel (`frontend/src/App.tsx:408-446`) explicitly label all states as synthetic mock.
- **What breaks first:** There is no actual appointment domain or provider call. The prototype can prove a link-purpose record was created, queued, and failed or remained without receipt; it cannot prove a handset received anything.
- **What could break later:** A real adapter would need idempotency, provider callbacks/signature verification, retries with budgets, number/channel validation, consent, rate limits, and operational monitoring.
- **Improvement:** Implement a compliant provider adapter and verified delivery-receipt webhook while preserving the current state meanings, immutable version binding, tenant scope, and safe audit fields.
- **Evidence:** `test_delivery_states_are_distinct_and_invalid_transition_has_no_audit` proves generated/queued/sent/delivered/failed distinction and no audit on denial. `test_delivery_failure_reason_is_allowlisted_and_rejections_have_no_side_effects` proves safe enum acceptance plus 422/no mutation/no audit for unknown, PHI-bearing, missing, or status-inapplicable reasons. Clinic-fault-injection and replacement-injection tests prove tenant isolation. Complete backend result: 135 passed.
- **Remaining limitation:** `simulated_sent` and `simulated_delivered` are never represented as real provider outcomes; scenario 11 cannot SURVIVE without a real provider and receipt.

### Scenario 12 — Patient-facing summary contains one wrong dosage

- **Verdict:** PARTIAL
- **Classification:** Approval, immutable sent-copy trace, invalidation, and replacement correction are implemented/tested locally; real phone recall/delivery remain unavailable
- **Where:** Approval now stores the exact immutable `approved_version_number` (`backend/app/models/patient_instruction.py:41`; `backend/app/services/patient_instruction_service.py:23-80`). Delivery creation resolves that EntryVersion through the clinic-scoped SQL boundary (`backend/app/services/clinic_scope_service.py:86-99`) and refuses Draft/Rejected/invalidated content. `backend/app/services/revision_service.py:102-132` keeps old versions and returns AI-derived content to Draft; `backend/app/services/delivery_service.py:158-197` supersedes unsent copies or marks simulated-sent/delivered copies correction-required. A corrected version must be clinician re-approved before `delivery_service.py:53-124` creates a new correction with `replaces_delivery_id`; the old record remains as superseded.
- **What breaks first:** If a clinician approves a wrong dose, the simulated copy can still be sent; the system is a human gate and trace/correction mechanism, not a guarantee the reviewer catches every clinical error.
- **What could break later:** A real handset may retain screenshots, notification previews, offline caches, or the original message even after the correction arrives. The system must never claim recall.
- **Improvement:** Add a clinically reviewed medication/dose confirmation checklist before approval and a real provider's separately traceable correction delivery/receipt; retain immutable old evidence and escalation if correction delivery fails.
- **Evidence:** `test_delivery_binds_approved_snapshot_and_edit_requires_traceable_correction` proves v1 binding, simulated send, edit-to-Draft, correction-required, preserved v1/v2, blocked pre-approval resend, clinician reapproval, v2 replacement, and old-record supersession. Role tests keep correction approval clinician-only; audit tests prove no dose/text/phone in metadata.
- **Remaining limitation:** No external message was sent and no phone copy can be recalled; safe behavior is “send correction, do not pretend recall.”

### Scenario 13 — Nurse allergy vs AI “no known allergy” contradiction

- **Verdict:** SURVIVES
- **Classification:** Exact nurse-first/AI-second synthetic contradiction is retained, surfaced at Glance, immutable, and clinician-reviewable
- **Where:** General no-known-allergy extraction and all-source conflict detection are in `backend/app/services/conflict_service.py:52-260`; successful AI ingestion invokes detection in `backend/app/services/ai_scribe_service.py:168`. `ConflictProvenance` binds both versions. The Top Card warning and dual-source controls are in `frontend/src/App.tsx:390`.
- **What breaks first:** Only the deterministic Penicillin/Sulfa demo vocabulary is recognized; unsupported allergens or phrasing may not create a warning.
- **What could break later:** Prototype authority order may be clinically inappropriate in another context, so it remains reviewable and is not treated as truth.
- **Improvement:** Add clinically governed terminology, reviewed extraction fixtures, and broader immutable conflict-source viewers.
- **Evidence:** `test_exact_nurse_then_ai_no_allergy_is_visible_safe_conflict` proves both entries, open conflict, staff-over-AI prototype policy, unresolved review, HIGH Glance warning, ABSTAIN, patient/Clinic B denial, resolution audit, and immutable v1 references. The edit/revert test proves pointers stay at v1. Manual UI confirmed the warning and both source actions.
- **Remaining limitation:** This is not general medical NLP and cannot establish clinical truth independently.

### Scenario 14 — Verifiable Evidence Confidence metric

- **Verdict:** SURVIVES
- **Classification:** Definition, inputs, outputs, immutable evidence, safety actions, and fail-closed behavior are aligned and tested
- **Where:** `backend/app/services/evidence_confidence_service.py:32` evaluates immutable source, version pointer, exact span, declared entity, open conflict, human confirmation, and separate source currency. `frontend/src/App.tsx` shows level/rule/action separately from CURRENT/STALE/BROKEN.
- **What breaks first:** Unsupported deterministic entities produce MEDIUM rather than evidence of medical correctness; LOW/ABSTAIN correctly require review.
- **What could break later:** Wider vocabularies require clinical validation; this remains evidence verifiability rather than truth or model calibration.
- **Improvement:** Add governed extraction rules and external clinical evaluation without converting this into model self-confidence.
- **Evidence:** Expanded tests cover HIGH/MEDIUM/LOW/ABSTAIN, pointer/version/span failures, entity mismatch, conflict, confirmation, deterministic repetition, STALE currency, no provider call, and injected invariant failure returning ABSTAIN without exception leakage.
- **Remaining limitation:** It is evidence verification, not probability of medical correctness.

### Scenario 15 — Fatigue dismissals and adaptive-ranking bias

- **Verdict:** PARTIAL
- **Classification:** Actor-aware reversible feedback, a negative aggregation guard, explicit impressions, diagnostics, review queue, caps, and floors are implemented; human/selection bias remains only partially mitigated
- **Where:** Event tables are in `backend/app/models/ranking_feedback.py`; recompute/policy/metrics in `backend/app/services/ranking_feedback_service.py`; endpoints in `backend/app/routes/highlights.py`; UI controls and review surfaces in `frontend/src/App.tsx`.
- **What breaks first:** Two clinicians may share the same workflow bias, while legacy aggregate history lacks actor/exposure reconstruction.
- **What could break later:** Small samples, correlated reviewers, stale decisions, and organization-wide conventions can still reinforce incorrect preferences.
- **Improvement:** Add time decay, governed sampling, durable privacy-reviewed impression sessions, and production identity/membership.
- **Evidence:** Tests prove one reject is suppressed, two independent clinicians enable bounded negative adjustment, decision change/undo does not drift, repeated undo is an unaudited no-op, exposure is explicit/idempotent, an unexposed item reaches the queue, clinic scope holds, and floors run last. Manual UI confirmed Undo, diagnostics, and Not previously surfaced queue.
- **Remaining limitation:** PARTIAL is retained deliberately: the controls expose and reduce selection/fatigue risk but cannot prove unbiased human behavior or clinical validity.

### Scenario 16 — Source edited after highlight creation

- **Verdict:** SURVIVES
- **Classification:** Highlight evidence is immutably version-bound and source currency is explicit
- **Where:** Additive `HighlightProvenance` in `backend/app/models/highlight.py:104` binds source entry/version/span/pointer. Binding and resolution live in `backend/app/services/highlight_provenance_service.py:31-138`; the protected snapshot endpoint is `backend/app/routes/highlights.py:149`. Glance and Revision History distinguish cited snapshot/current entry in `frontend/src/App.tsx:365` and the revision panel.
- **What breaks first:** If the bound version, pointer, or exact span is missing/corrupt, status becomes BROKEN and confidence abstains; the system does not guess from current content.
- **What could break later:** Existing databases with multiple historical versions containing the same exact span remain deliberately unbound/BROKEN rather than guessed. SQLite cannot prove a multi-process creation/edit race under production load.
- **Improvement:** Add a formal migration/backfill report and production transaction/isolation tests; retain manual review for stale clinical currency.
- **Evidence:** `test_highlight_provenance.py` proves exact creation binding, expected-version conflict, stable pointer/snapshot after edit and revert, STALE/current separation, missing-version and corrupted-span BROKEN behavior, clinic/role visibility, seed resolution, and existing-runtime synthetic backfill. Confidence remains deterministic/no-model through existing confidence tests. Manual UI verified CURRENT, STALE, and BROKEN presentations.
- **Remaining limitation:** The companion-table compatibility path is synthetic-only; external raw transcript viewing is still absent and no browser E2E suite exists.

### Scenario 17 — Complete consult intelligence and audience-readiness rubric

- **Verdict:** DOES NOT
- **Classification:** Some downstream text trust components exist, but the end-to-end consult-audio capability and most scoring dimensions are absent
- **Where:** The only ingestion contract accepts one completed text transcript and interaction type (`backend/app/schemas/ai_scribe.py:9-20`); it has no audio stream, acoustic metadata, language/speaker/timestamp segments, captured-term uncertainty, or audience target. Existing provenance, deterministic extraction, conflicts, revisions, and role filtering are separate partial building blocks, not this complete product.
- **What breaks first:** A real noisy consult cannot enter the system as streaming audio. Therefore code-switching, exact medication/dosage confirmation, live facts, and distinct audience summaries cannot be reliably produced from the actual consultation.
- **What could break later:** Even if an ASR transcript were pasted in, unsupported languages and clinical phrasing can corrupt deterministic extraction; highlights cite mutable entries; a journal lookup could be mistaken for proof of what this patient said; one summary reused across roles could expose internal detail or omit necessary clinical evidence.
- **Improvement:** Phase 6 must cover every original scoring dimension, while depending on Phase 4 immutable provenance: **real consult audio streaming**—define honest received/partial/final/failed session states rather than claiming existing support; **noisy-clinic ASR**—record synthetic acoustic/noise metadata, segment confidence/alternatives and human correction; **code-switching**—preserve per-segment language for English/Mandarin/Tamil and mixed statements; **medical terminology and dosage capture**—store the captured phrase, alternatives such as Montelukast 20 mg versus 50 mg, source timestamp, and explicit clinician/patient confirmation; **journal/reference-assisted verification**—use references only to validate terminology/plausibility and surface citations, never to decide what the patient actually took; final patient fact requires human confirmation; **multilingual readiness**—test synthetic multilingual fixtures without claiming production ASR quality; **intact provenance**—link facts and all summaries to immutable audio/transcript segments/versions; **fact extraction and mutation robustness**—test edits, corrections, stale facts, conflicts and re-extraction without silently changing old evidence; **distinct summaries**—Clinician Summary retains evidence/conflicts/clinical detail, Staff Summary contains operational tasks/follow-up, and Patient Summary uses plain approved language and remains behind the clinician approval gate.
- **Evidence:** Dimension-by-dimension current state: real streaming audio—absent; noisy-clinic ASR—absent; code-switching—absent; medical terminology/dosage capture—PARTIAL only for deterministic completed English text in `backend/app/services/conflict_service.py:32-91`; journal/reference boundary—absent, while clinician approval exists only for patient instructions; multilingual readiness—absent; intact provenance—PARTIAL because current highlights target mutable entries; fact extraction/mutation robustness—PARTIAL due limited demo vocabulary, conflict/revision support, and missing immutable-source mutation tests; distinct audience summaries—absent, because `can_view_entry` role filtering in `backend/app/services/authorization_service.py:42-62` is not audience-specific generation.
- **Remaining limitation:** A prototype contract and synthetic fixtures cannot validate real microphones, noisy-clinic ASR, language coverage, clinical accuracy, journal quality, or patient comprehension; those require provider evaluation and clinical/human studies.
