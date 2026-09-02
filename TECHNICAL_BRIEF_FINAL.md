# Nightingale Cloud — Real-Clinic Evidence Brief

Zhanchen Lin · Synthetic data only · 3 September 2026

Three-page technical brief, updated through Phase 9. Implementation baseline:
`0517978a715c67f12e2487917b31721553809ace`. Synthetic prototype verdicts are not
production-readiness claims.

## Page unit 1 — Architecture, privacy, and clinic readiness

Nightingale combines one longitudinal Care Note per patient, a ranked Glance View,
collaboration and auditable clinician decisions. It is a prototype, not a production EHR.

```text
React/TypeScript/Vite → REST → FastAPI authorization → clinic-scoped SQL
                                              → SQLAlchemy / SQLite
Patient → TimelineEntry → immutable EntryVersion → approval → mock delivery
                     ↘ comments/tasks; highlights → version/span provenance
                     ↘ conflicts → two immutable sources; metadata-only audit
Consult → immutable segments → signals/captures → three audience summaries
```

Outer role/self-access authorization and inner clinic-filtered SQL are independent
boundaries. They do not replace production identity: development headers remain forgeable.
Formal Clinic/User/Membership models, migrations and database RLS are absent.

| Scenario | Verdict | Implemented evidence; first remaining failure |
|---|---|---|
| 1 Phone-only patient | PARTIAL | Digest lookup, atomic one-use challenge, self-only portal; mock token delivery does not prove phone ownership. |
| 2 Isolation guard bug | SURVIVES | Disabling outer guard still yields scoped SQL denial for foreign IDs; forged clinic identity remains outside that proof. |
| 3 Other PHI exits | PARTIAL | Application errors/logs and metadata audits tested; proxy, crash dashboard and external retention unverified. |
| 4 Ordering | SURVIVES | Raw synthetic text → redaction → validation → provider; validation failure calls no provider and creates no entry. |
| 5 Clinic B | PARTIAL | Scoped queries and same-phone/per-clinic lookup work; production onboarding/membership/migrations absent. |
| 6 Trilingual consult | PARTIAL | Code-switched synthetic text/spans survive; real speech cannot enter this text-only contract. |
| 7 Minute-two allergy | PARTIAL | Final post-ASR segment creates provisional signal at supplied offset; no audio-time detection. |
| 8 Model hangs | PARTIAL | Configurable deadline, waiting/duplicate lock and timeout UI; synchronous worker capacity remains limited. |
| 9 Hour-long 503 | PARTIAL | Typed failure/manual retry UI and labeled mock; no operational failover or circuit breaker. |

Client source IDs become stable opaque SHA-256 references before persistence/logging;
this prevents direct plaintext leakage, not guessing attacks. Only validated redacted text
crosses the provider boundary. The separate Consult Lab is offline rule-derived and stores
synthetic segments for provenance; no provider receives them. TLS, encryption and external
retention controls remain deployment work.

Evidence: `backend/tests/test_real_clinic_scenarios.py:59–106`. Exact per-scenario
file/line, services and failure analysis are in
[scenario-test-mapping](docs/real-clinic-hardening/scenario-test-mapping.md) and
[scenario-matrix](docs/real-clinic-hardening/scenario-matrix.md).

## Page unit 2 — Editing, delivery, and clinical trust

| Scenario | Verdict | Implemented evidence; first remaining failure |
|---|---|---|
| 10 Concurrent edits | SURVIVES | Expected-version updates reject stale writes with 409; UI retains draft with explicit recovery. Browser crash can lose unsaved text. |
| 11 Link never received | PARTIAL | Created/queued/simulated-sent/simulated-delivered/failed differ; no provider receipt proves handset delivery. |
| 12 Wrong dose sent | PARTIAL | Approval binds a version; edits invalidate approval and flag sent copies for correction. Review can miss errors; remote copies cannot be recalled. |
| 13 Nurse allergy vs AI | SURVIVES | Exact synthetic contradiction produces HIGH/Needs Review with both immutable sources; unsupported phrasing may escape extraction. |
| 14 Evidence Confidence | SURVIVES | Deterministic version/span/entity/conflict checks fail closed; verifiability is not medical truth or probability. |
| 15 Biased learning | PARTIAL | Reversible feedback, two-ID negative guard, exposure de-duplication and separate review queue; correlated bias/spoofable identity remain. |
| 16 Edited source | SURVIVES | Cited version/span remain immutable; currency becomes STALE. Missing/corrupt evidence becomes BROKEN/ABSTAIN, never guessed. |

Risk answers potential harm; importance answers review order; Evidence Confidence answers
verifiability; CURRENT/STALE/BROKEN answers currency. Ranking applies bounded learned
adjustment before safety floors. Allergy and unresolved dosage conflicts retain HIGH floors.
Two distinct clinician IDs do not prove two independent humans. Feedback cannot approve
patient instructions.

Phase 9 AI Scribe distinguishes success, redaction-withheld, timeout, unavailable and invalid
provider response. Waiting locks duplicate submission; mode is confirmed as mock/external
only from the response. Drafts stay in memory, clear on identity/patient change, and survive
known failures for explicit manual retry. Network/lost responses lock retry as outcome unknown:
refresh and inspect Timeline first. Late responses cannot update a changed context.
Success independently refreshes Glance, conflicts and Evidence Confidence. Failed reads show
NOT UPDATED and offer read-only refresh; generation remains successful, not retryable.

AI-derived instructions follow Draft → clinician Approved or Rejected. Patients cannot see
raw AI notes or internal collaboration. Existing manual clinician instructions remain
inherently approved for compatibility. Changes to approved AI-derived content/evidence require
reapproval. Delivery retains the approved EntryVersion and replacement relationship, not
a claim to erase a sent copy. Audit stores actor/action/entity/status, not clinical text.

Evidence: `backend/tests/test_real_clinic_scenarios.py:110–197`, plus mapped revision,
approval, delivery, conflict, confidence and Phase 5 suites. SURVIVES applies to the tested
synthetic prototype, not unrestricted clinical language or production load.

## Page unit 3 — Scenario 17, lessons, verification and delivery

**Scenario 17 overall: PARTIAL.** Real streaming audio and noisy-clinic ASR: **DOES NOT**.
Code-switching: **SURVIVES for synthetic text** with ordered spans. Terminology/dosage:
**SURVIVES for demo vocabulary**, retaining Montelukast 20/50 mg ambiguity until clinician
confirmation. Reference assistance: **PARTIAL**; the curated term/unit catalog is neither
journal search nor proof of a patient's dose. Multilingual readiness: **PARTIAL**, without
evaluated speech accuracy or comprehension studies.

Provenance: **SURVIVES in prototype**. Complete segment-version pointer lists live in
`ConsultSummary.source_provenance`; each TimelineEntry has one primary pointer, and
patient output traces through clinician summary/approval. Mutation robustness: **PARTIAL**;
partial→final and corrections append versions and invalidate derived state, but vocabulary
and multi-worker validation remain narrow. Distinct clinician/staff/patient summaries:
**SURVIVES as rule-derived outputs**, not model generation. Finalization commits all three
together; failure rolls back partial output and closes the session as failed. Evidence:
`backend/tests/test_phase6_multilingual_consult.py:45–325` and the full dimension matrix.

**Failed attempts and changed assumptions.** One clinic guard, mutable source anchors and
pre-model redaction alone were insufficient: independent scoped queries, version-bound
evidence and opaque source IDs were added. Phone enumeration, non-atomic challenge use,
global phone uniqueness and free-text failure reasons were corrected. A greedy dose regex
lost part of a dose; tests exposed it. Summaries initially committed independently; fault
injection drove an atomic transaction. An older local server invalidated initial fresh-state
demo evidence; a separate fresh setup was used. SQLite/create_all still cannot migrate old
column changes. Small services, offline mock and human review remain appropriate demo choices.
Phase 9 review exposed a Timeline-only success update that left safety warnings stale;
independent guarded clinical refresh corrected it without regenerating the note.

**Verification provenance.** Latest Phase 9 evidence: **182 backend passes, one existing
Starlette/httpx deprecation warning**; frontend **18 passes**, both TypeScript checks and
production build passed. These were not rerun during this brief/PDF task. The final UI-only
correction reused the earlier backend run. Phase 7 fresh and
current-schema restart smoke passed, not general historic migration. Manual UI covered
Glance, consult, confirmation, summaries and approval; other paths use TestClient evidence,
not comprehensive browser E2E. No real provider/message was invoked. Historical
20-warmup/200-request Glance median 5.308 ms/P95 6.540 ms was an earlier in-process
TestClient/in-memory SQLite measurement, not current deployed SLA evidence.

**Delivery status.** This Markdown is the source of the updated three-page PDF. Video coverage,
recipient access and email remain pending; existing video was not inspected or replaced.
Record selected scenarios with mock labels and check recipient access before sending.
Original deadline: 3 September 2026,
18:00 SGT. [Remaining work](docs/real-clinic-hardening/remaining-work.md) separates delivery
checks from identity, messaging, audio/reference resources and user decisions. Phase 8
completion does not mean all requirements are implemented.
