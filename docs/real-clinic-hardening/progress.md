# Phase 0 Progress Log

## Phase 9 — AI Scribe request recovery UI

- Review correction: success now refreshes clinical safety views independently of generation;
  failure marks Glance/conflicts/Evidence Confidence NOT UPDATED with read-only retry.
  Existing success/draft is retained and generation remains locked. Four new refresh tests
  cover updated evidence/conflicts, failed reads, context switch and latest-request ordering.
  Frontend final: 18 passed; TypeScript app/config and build passed (22 modules, 92 ms).
  Backend was not rerun for this frontend-only correction; prior Phase 9 182-pass result below
  remains attributed to that earlier run. No browser E2E or external provider invocation.

- Confirmed HEAD `3d2f7a6a08ed2204b5cee8a7c881f5786c4d8061`; user files protected.
- Added minimal panel, dedicated root-response adapter, memory-only controller and tests;
  reused backend contract and existing form styles. No backend or dependency changes.
- First frontend test run: 14 passed; build failed TS5097 on the runtime .ts import used by
  Node strip-types tests. Enabled allowImportingTsExtensions under existing noEmit; subsequent
  tests, app/config TypeScript checks and build passed without weakening assertions.
- Frontend: 14 passed (11 new); backend: 182 passed, one existing Starlette/httpx warning
  in 18.59s. No real provider invoked. No rendered browser smoke performed this phase.
- Updated scenario 8/9 mapping and remaining work without upgrading PARTIAL. Long-outage,
  worker capacity, production SLA and unknown-outcome reconciliation remain unsolved.
- Final build passed (21 modules, 89 ms); working/staged diff checks passed. Twelve files
  explicitly staged: six frontend/config/test files and six hardening documents. User-owned
  root files/media remain unstaged; no commit or push. Awaiting authorization.

## Phase 8 — final documentation and delivery reconciliation

- Confirmed master HEAD `c6c3f309d28709c2060665eafb9f704af961f1cf`.
- Read original requirements and targeted docs; calibrated README, final brief, runbook,
  four hardening documents and new remaining-work.md. No application/test changes.
- No test/build/benchmark rerun: attributed Phase 7 evidence is 182 backend passes/one warning,
  3 frontend passes and both TypeScript checks/production build passed.
- No PDF rendering, video reading, upload, email or push. Current PDF pagination/content,
  new-feature video coverage and recipient access remain unverified; verdicts unchanged.
- Two patch attempts failed without changes: same-path delete/add, then an incorrect matrix
  heading. Used exact update patches after checking the heading; no application files touched.
- Final path/diff/scope checks precede staging. Commit requires authorization; no next phase.
- Final local Markdown links passed; brief is approximately 1,149 whitespace-separated words,
  not rendered pages. Working diff has no backend/frontend changes; diff format check passed.
  Eight Phase 8 documents are the explicit staging scope; protected user files remain excluded.

## Phase 7 — integration acceptance and demo stability

- Confirmed Phase 6 HEAD `25dabb04ff8eca6f9eebb8122406c3c200408f65`; protected root
  planning and personal/output files remain untouched and excluded.
- Pre-change full backend baseline: **163 passed, 1 third-party warning**.
- Added one direct named acceptance test for every original scenario 1–16, a dedicated Phase 5
  feedback state-machine audit, and fresh/current-runtime SQLite smoke tests. Added the concise
  scenario-test mapping document.
- Scenario suite final: **19 passed, 1 warning**. Phase 5 audit/floor set: **13 passed, 1 warning**.
- Complete backend final: **182 passed, 1 warning in 17.20s**. Warning is the existing
  Starlette TestClient/httpx deprecation; no test was skipped, xfailed, deleted, or weakened.
- Frontend logic: **3 passed**. TypeScript app and Vite-config checks passed. Production build
  passed with **19 modules transformed in 128 ms**.
- Fresh database create/seed and current synthetic runtime restart/reseed passed. Historical
  pre-column-change SQLite remains a documented rebuild/migration boundary.
- Manual isolated UI smoke passed for Glance display, failed delivery label,
  multilingual fixture, minute-two signal, Montelukast confirmation, distinct summaries,
  approval, and patient visibility. It used only synthetic data/local mocks and is explicitly
  not an automated browser E2E test.
- Immutable-source browser navigation was checked separately on existing local data;
  fresh-state immutable-source evidence is automated TestClient coverage.
- No application-code regression required a fix. Two acceptance-test expectation/layout errors
  and one invalid initial browser baseline were corrected and recorded in the plan error table.
- Precisely staged eight Phase 7 test/documentation files only. Root user changes and personal
  materials remain unstaged; generated files remain ignored. No commit or push; Phase 8 not started.

## Phase 6 — implementation and verification

- Staged-review corrections completed: atomic three-audience finalization with fail-closed
  `failed` semantics, shared create/correct validation, and explicit append-only partial→final.
- Fault injection on the second entry proves zero partial TimelineEntry, EntryVersion,
  PatientInstructionApproval, ConsultSummary, or successful finalization-audit persistence.
  Normal completion creates exactly three summaries once; repeated completion returns 409.
- Post-review verification: Phase 6 focused **11 passed**; relevant AI/redaction/provenance/
  conflict/approval/delivery/RBAC/clinic/audit regression **120 passed**; complete backend
  **163 passed** (each backend run has one third-party deprecation warning). Frontend logic
  **3 passed**; direct TypeScript checks and production build passed (19 modules, 92 ms).
- Confirmed Phase 5 HEAD `385ef1667541c9ce84e863c389b3414cf60c93b5`; root planning changes and personal/output files remain excluded.
- Added additive synthetic consult session, immutable/versioned transcript segment, provisional safety signal, clinical capture, and audience summary tables. No real audio or ASR path was added.
- Added state- and clinic-scoped APIs for contiguous segment ingestion, correction, capture confirmation, finalization, and audience-filtered summary retrieval.
- Finalized minute-two allergy text produces an internal HIGH provisional signal immediately; partial input produces no confirmed fact or final summary.
- Montelukast ambiguity retains both candidates and a curated-reference boundary; clinician confirmation is metadata-audited and never selected by reference or LLM.
- Completed sessions generate distinct rule-derived clinician/staff/patient outputs; patient output reuses Draft → clinician approval → immutable mock delivery.
- Segment correction preserves v1, creates v2, supersedes old captures/signals, marks summaries STALE, and invalidates approved patient visibility.
- Initial Phase 6 focused result before staged-review hardening: **7 passed, 1 third-party warning in 1.00s**. Initial AI/redaction/provenance/conflict/approval/delivery/RBAC/clinic/audit regression: **109 passed, 1 warning in 8.69s**. Initial complete backend: **159 passed, 1 warning in 14.38s**.
- Frontend logic: **3 passed**; final TypeScript and Vite production build passed (19 modules, 92 ms).
- Manual isolated synthetic UI verified the explicit post-ASR/not-audio label, receiving/completed states, minute-two HIGH provisional allergy signal, Montelukast 20/50 confirmation, reference boundary, provider-not-invoked label, and three visibly distinct rule-derived summaries. The first automatic-refresh behavior was corrected and the final state reverified.
- Documentation line references, manual UI evidence, diff checks, and explicit 20-file Phase 6 staging are complete. Root user files remain unstaged; no commit has been created.

## Phase 5 — implementation and verification

- Confirmed Phase 4 HEAD `551a4a5128ce027b172ae593f2bc31dfce44b14d`; pre-existing root planning changes and personal/output materials remain excluded.
- Inspected deterministic extraction, authority, conflict/Glance, immutable provenance, Evidence Confidence, preferences, weights/floors, audit, authorization, AI-scribe, and frontend decision paths; reported the pre-change behavior and risks.
- Extended conflict detection to successful AI/patient-derived ingestion, added general no-known-allergy extraction for the fixed synthetic vocabulary, conflict-aware HIGH Glance generation, and immutable dual-source ConflictProvenance.
- Added structured Evidence Confidence inputs/rule/action and fail-closed ABSTAIN behavior. Confidence remains deterministic and provider-free; source currency remains separate.
- Added actor-aware feedback replacement/undo, two-independent-clinician negative threshold, idempotent explicit exposure, diagnostic metrics, and independent lower-ranked review queue.
- Focused implementation runs exposed and corrected: omitted explicit expected-source version, an entity-only compatibility recomputation, old single-actor negative-learning assertions, actual frontend interface/CSS shapes, and an older local frontend/backend mismatch. All are recorded in the Phase 5 error table.
- Phase 5 focused safety/trust suite: **20 passed, 1 third-party warning in 2.38s**. The broader RBAC/clinic/revision/approval/audit/AI/conflict/provenance/concurrency regression: **93 passed, 1 third-party warning in 8.96s**.
- Complete backend: **152 passed, 1 third-party warning in 14.26s**.
- Frontend recovery logic: **3 passed**; TypeScript checks and Vite production build passed (18 modules, 92 ms).
- Manual isolated synthetic UI verified: HIGH allergy conflict at Glance, both source buttons with immutable v1 labels, abstention rule/action, Undo feedback, explicit exposure diagnostic (`not accuracy`), and a lower-ranked `Not previously surfaced` review candidate. Temporary ignored databases only; no user/runtime database was used.
- Final diff and precise staging remain pending; no commit has been created.

## Phase 4 — started

- Confirmed Phase 3 HEAD `dd926de9e06c3cbb2365e3acf8de27b8ce82b8fc`; root planning files and personal/output materials remain untouched and excluded.
- Audited version conflict, revision transaction, authorization/tenant ordering, Highlight/confidence, seed, frontend edit state, and runtime SQLite behavior; reported the exact current failure behavior before modification.
- Added authorized structured 409 detail and a typed frontend ApiError. The edit component now preserves and compares the local draft, supports copy, explicit server reload, and cancel-with-draft, with no automatic merge or overwrite.
- Added additive `HighlightProvenance`, deterministic CURRENT/STALE/BROKEN resolution, immutable snapshot endpoint, exact version/span binding, guarded expected-source-version conflict, seed/backfill support, and separate source-currency UI.
- First focused run failed at seed because version pointers were incorrectly globally unique; two highlights legitimately cite entry 006 version 1. Removed that uniqueness while retaining the index.
- A first stylesheet patch missed the compound selector and was corrected after inspection. A first combined npm invocation used the repository root; the backend focused suite still completed. The first Node strip-only test exposed unsupported parameter-property syntax; ordinary fields fixed it.
- Final Phase 4 focused backend suite (concurrency, provenance, and evidence confidence): **19 passed, 1 third-party warning in 1.45s**. Frontend recovery logic: **3 passed**.
- Added patient visibility parity assertion: approved instruction evidence is readable to its patient, while internal staff evidence is denied. Added both missing-version and corrupted-span BROKEN assertions.
- Phase 4 security regression set covering concurrency, revision, provenance, confidence, RBAC, clinic isolation, approval, delivery, and audit: **83 passed, 1 warning in 7.36s**.
- Final complete backend suite: **143 passed, 1 third-party warning in 11.53s**.
- Frontend Node recovery tests: **3 passed**. TypeScript checks and production build passed (18 modules transformed, 93 ms).
- Manual isolated-DB browser review verified CURRENT “Cites version 1”, STALE “Source has changed” with immutable v1 snapshot after source v2, and BROKEN “Needs review · Immutable cited evidence cannot be resolved.” No user/runtime database was used.
- Port 8000 was initially unavailable and the first 5174 direct-origin load failed CORS; after verifying old ports were no longer bound, the isolated review used allowed origin 5173 with backend 8002. A first temporary SQLite mutation command had quoting syntax failure; a corrected nonclinical binding-only command was used once.

## Phase 3 — started

- Staged review identified four required corrections before commit: enrollment enumeration, non-atomic challenge consumption, globally unique phone digest, and free-text delivery failure reason. Commit remains blocked while these are corrected and reverified.
- Replaced the enrollment-revealing response with a uniform accepted response for all valid numbers. Unknown numbers now receive a secure random non-persisted decoy challenge/token; exchange always fails, and the mask is derived solely from submitted input.
- Replaced SELECT/check/update consumption with one conditional SQL UPDATE over digest, unused state, and expiry. Claim and patient-session creation share a transaction; a two-independent-session file-SQLite test proves only the first claim succeeds.
- Replaced global phone uniqueness with `(clinic_id, phone_digest)` and seeded the same synthetic phone in Clinic A and Clinic B. Tests prove correct clinic resolution and same-clinic duplicate rejection.
- Replaced arbitrary delivery failure strings with a five-value safe enum. Failed requires an enum value, non-Failed forbids it, and rejected unknown/PHI-bearing inputs leave delivery state and AuditLog unchanged.
- The first corrected focused collection failed because the test imported `Base` from the wrong module; corrected to `app.database`. The next run had one fixture-setup failure because the duplicate constraint test had not requested `client`; corrected without changing application behavior.
- Post-review focused Phase 3 suite: **16 passed, 1 third-party warning in 1.66s**.
- The first regression command used the wrong audit test filename and collected no tests; after inspecting the test inventory, the corrected RBAC/clinic-isolation/revision/approval/audit/AI regression set passed **85 tests, 1 warning in 7.08s**.
- Complete backend suite after all four corrections: **135 passed, 1 third-party warning in 9.77s**.
- Frontend TypeScript checks and production Vite build passed (17 modules transformed, 94 ms). Diff and precise staged verification follow.

- Confirmed Phase 2 HEAD `1036572c4f80e3bf1deeaffb44b539c599f9e25f` on `master`.
- Confirmed root `findings.md`, `progress.md`, `task_plan.md`, video, resume, `output/`, and `read.md` remain user-owned and excluded.
- Re-read all four hardening documents and began the phone identity, patient visibility, instruction approval, revision, seed, and frontend inventory.
- Planning-session catchup could not use a global `python` executable; the failure is recorded in the hardening plan and no root planning file was touched.
- Added additive Patient synthetic-contact metadata, one-time phone challenge/session models, and patient-delivery state with tenant, immutable version, masked destination, opaque mock reference, and replacement linkage.
- Added domain-separated contact/token hashing, secure random single-use challenge exchange, expiring patient sessions, and self-only approved-instruction/delivery portal routes. The local mock token is returned once and is never persisted in plaintext.
- Added server-controlled delivery creation/transitions, clinic-scoped delivery/version queries, metadata-only audits, approval-version binding, and edit/revert hooks that supersede unsent copies or mark simulated-sent/delivered copies correction-required.
- First focused run: 10 passed and 1 failed because the test fixture's default clinician headers were still present during a bearer-only restriction assertion. The application path was not bypassed; the test now explicitly removes those fixture headers before retrying.
- Corrected Phase 3 focused suite: **11 passed, 1 third-party warning in 1.02s**.
- Required Phase 3, approval, clinic-isolation, RBAC, revision/concurrency, audit, and AI-scribe regression set: **80 passed, 1 third-party warning in 6.17s**.
- Added a compact frontend delivery/access panel that labels the local mock boundary, displays immutable approved version and masked destination, distinguishes all delivery/correction states, and exposes only server-allowed mock transitions/replacement creation.
- First complete backend run: **129 passed, 1 failed** because the exact-field API test did not yet include the additive `approved_version_number`; updated that compatibility assertion. Frontend TypeScript checks and production build passed on the same run (`vite v8.2.2`, 17 modules, 99 ms).
- Corrected complete backend suite: **130 passed, 1 third-party warning in 8.21s**.
- Manual local UI inspection on a fresh Phase 3 database verified the visible “Synthetic local mock / Not real SMS or WhatsApp” boundary, masked `+65••••0001` destination, failed appointment-link state, immutable approved v1 label, and clinician-approved Version 1 timeline detail. Correction-required and replacement behavior is proven by the focused API test rather than mutating the manual inspection dataset.
- Tightened the phone bootstrap lookup to require clinic context in its SQL predicate and moved edit/revert delivery lookup behind a reusable Patient-joined Phase 2 scoped query, so no new patient/delivery path relies on a global object read as its effective tenant boundary.
- Final post-tightening verification: Phase 3 focused suite **11 passed in 1.01s**; complete backend suite **130 passed in 8.53s**; frontend TypeScript checks and production build passed (`vite v8.2.2`, 17 modules, 96 ms). The sole warning remains the third-party Starlette/httpx deprecation.

## Phase 2 — started

- Confirmed Phase 1 HEAD `b0fe21256da4363b938f7ceb6713c8d0b201ea9f` on `master`.
- Confirmed the three root planning-file modifications plus video, resume, `output/`, and `read.md` remain user-owned and excluded.
- Re-read all four hardening documents and began a complete route/service/model inventory before selecting the inner tenant-query design.
- Enumerated patient, entry, version/audit, highlight, comment, assignment, conflict, approval, AI-scribe, decay, and importance-preference access paths. Confirmed all except importance preferences currently depend on an unscoped lookup followed by the single outer clinic guard.
- Selected a two-boundary design that preserves existing outer authorization and 403 behavior, then requires a separate SQL query joined to `Patient.clinic_id` before data use; fault injection of the outer comparison will therefore yield an inner 404 rather than exposure.
- Added the centralized `clinic_scope_service.py` query boundary for patients, entries, versions, entry audits, highlights, comments, assignments, conflicts, and patient-instruction approvals.
- Updated patient, AI-scribe, and entry/version/audit/approval paths so the existing outer guard runs first and a separately clinic-scoped SQL result is required before use or mutation.
- Updated collaboration reads/mutations and parent-comment association checks to require independently scoped entry/comment/patient/assignment queries.
- Updated highlight and conflict reads/mutations so both target records and indirect source entries are re-resolved through the clinic-scoped query boundary before use.
- Added a 17-case guard-failure matrix plus same-clinic, cross-tenant assignment injection, importance-preference, no-audit, and no-clinical-content checks. The first run exposed a test-fixture entry-ID mistake before isolation assertions; corrected it from seeded entry 006 to 007.
- Corrected Phase 2 focused isolation suite: **20 passed, 1 third-party deprecation warning in 2.19s**.
- Required RBAC/collaboration/revision/conflict/approval/AI/audit regression set including Phase 2 matrix: **98 passed, 1 third-party warning in 6.26s**.
- Complete backend suite: **119 passed, 1 third-party warning in 7.32s**.
- Reviewed tenant-query join columns and confirmed existing model indexes cover the new scoped lookups; no unmeasured schema optimization was introduced.
- Updated README and scenarios 2/5 to distinguish the outer authorization guard from the inner SQL tenant boundary and to separate all six Clinic B onboarding work categories.
- Frontend TypeScript checks and production build passed (`vite v8.2.2`, 17 modules, 127 ms).
- Rechecked the warm Glance/highlights path after adding tenant predicates: 20 warm-ups and 200 measured in-process requests produced 5.849 ms median and 7.006 ms P95. This excludes network, browser rendering, production storage/volume, and concurrency.

## Phase 1 — started

- Confirmed HEAD `058020d428b0a597dec14363513aae1ba8b9735c` on `master`.
- Confirmed root `findings.md`, `progress.md`, `task_plan.md`, video, resume, `output/`, and `read.md` are pre-existing user state and remain excluded.
- Read all four Phase 0 hardening documents and inspected the current AI-scribe, redaction, validation, provider, logging, audit, route/schema, and focused-test paths.
- Selected a minimal design: configurable provider deadline, typed sanitized provider failures, safe abstention with no entry persistence, additive API outcome/generation-mode fields, no retry, and clearly labeled deterministic mock behavior.
- Logged and corrected one failed documentation patch caused by an exact-heading mismatch; it applied no partial changes.
- Implemented typed provider failures, bounded environment-configured timeout, safe abstention, additive response outcome/generation-mode fields, and explicit rule-derived mock labeling.
- Added focused timeout, 503, invalid/empty response, no-entry, no-audit, redacted-provider-input, and no-error-body-leak tests.
- Corrected a focused-test invocation path error, then corrected one overly broad privacy assertion that matched the safe common word `and`; the implementation itself did not fail that check.
- Final focused Phase 1/redaction suite after the generation-mode allowlist review: **25 passed, 1 third-party deprecation warning in 0.89s**.
- An intermediate complete backend run passed **97 tests** before the final malformed-response test was added; a final full run is still required.
- Updated README provider configuration and failure semantics without changing frontend behavior.
- Final complete backend suite: **98 passed, 1 third-party deprecation warning in 4.71s**.
- Frontend `npm run build`: passed both TypeScript no-emit checks and the Vite production build (17 modules transformed).
- Updated only scenarios 3, 4, 8, and 9 from verified Phase 1 evidence; verdicts remain honestly calibrated as PARTIAL, SURVIVES, PARTIAL, and PARTIAL.
- `git diff --check` passed. The full working-tree name check still shows the three pre-existing root planning-file modifications, while Phase 1 changes are confined to the explicitly listed backend, test, README, and hardening-document files.
- Staged review found a client-controlled `source_id` PHI outlet in logs and provenance. Confirmed entry IDs were already UUIDs, then replaced all raw source logging/persistence with a stable SHA-256 opaque reference and expanded regression coverage across success and failure paths.
- Final post-correction focused Phase 1 suite: **26 passed, 1 third-party deprecation warning in 0.99s**.
- Final post-correction complete backend suite: **99 passed, 1 third-party deprecation warning in 4.78s**.
- Post-correction frontend production build passed both TypeScript checks and Vite bundling (17 modules transformed).
- Post-correction `git diff --check` and `git diff --cached --check` passed. Explicit staging contains only the 12 Phase 1 files; the three pre-existing root planning-file modifications and all user media/output files remain unstaged.

## 2026-09-02

- Read the supplied Phase 0 requirements and safety constraints.
- Captured branch, HEAD, working-tree status, and diff summary.
- Confirmed pre-existing tracked and untracked files that must be excluded.
- Created an independent planning directory rather than modifying root planning files.
- Planning session-catchup failed because a global `python` executable is unavailable; recorded the error and selected the repository virtual environment for later project tests.
- Inventoried all tracked files, package scripts, pytest configuration, and ignore rules.
- Initially evaluated scenario meanings from the phase mapping because the original wording was not yet available.
- Inspected all backend model definitions and the route/authorization function inventory.
- Recorded initial architecture, authorization, missing-model, and mutable-provenance findings.
- Inspected the AI-scribe, redaction, validation, provider, authorization, and patient-instruction approval call paths with line numbers.
- Inspected focused AI-scribe, redaction, RBAC, and patient-approval tests.
- Recorded verified safety ordering and current timeout/degradation limitations.
- Inspected patient, revision, audit, collaboration, conflict, importance, adaptive-learning, highlight, evidence-confidence, and data-decay services with line numbers.
- Recorded mutable-provenance, service-layer tenant-boundary, limited deterministic vocabulary, and learning-bias findings.
- Inspected every registered backend route with line numbers and verified current parent-patient authorization call sites.
- Inventoried all test functions and inspected the focused concurrency, revision, provenance, confidence, safety-floor, learning, conflict, collaboration, audit, and data-decay suites.
- Identified missing scenario-numbered, delivery, timeout/failure, immutable-provenance mutation, multilingual, streaming, and audience-summary tests.
- Inspected all tracked frontend source and the main action/render paths with line numbers.
- Inspected requirements, final audit, demo runbook, README, and final technical brief claims relevant to safety, limitations, and performance.
- Recorded incomplete frontend 409 recovery, discarded backend error details, absent browser E2E, and absent advanced workflow UI findings.
- Inspected database setup, application lifespan, full synthetic seed behavior, test fixtures, dependency pins, and schema declarations.
- Confirmed the repository virtual environment and frontend dependency directory are available for verification.
- Recorded the startup seed overwrite risk, lack of migrations/Clinic/User tables, and limitation of the synthetic request flag.
- Read the complete interviewer-authored scenarios 1–17 from the supplied attachment and adopted it as the sole source for numbering, meaning, deliverables, and the 2026-09-03 18:00 SGT deadline.
- Recalibrated the scenario matrix against the original wording, especially scenario 2 clinic-isolation single-point failure, scenario 5 Clinic B onboarding, and every scoring dimension in scenario 17.
- Corrected scenario 13 from SURVIVES to PARTIAL after verifying that nurse-first/AI-second conflict creation is not triggered, and corrected scenario 12 from DOES NOT to PARTIAL because the clinician approval gate exists even though phone delivery/correction does not.
- Completed the baseline verdict summary and risk/dependency-ordered plan for Phases 1–8.
- Verified all 17 scenario records contain every required evaluation field.
- Verified the independent audit documents contain no trailing whitespace.
- Phase 0 verification and documentation are complete; the local commit remains intentionally pending explicit authorization. Only the four files in this directory are intended for that future atomic commit.
- Initial explicit staging failed before changing the index because the managed environment denied creation of `.git/index.lock`; the retry will request repository-scoped Git write permission and retain the same four-file target list.
- Phase 0 application work is stopped; no Phase 1 work has begun.

## Verification results

- Complete backend suite: `89 passed, 1 warning in 4.10s`.
- Frontend TypeScript checks: passed as the first two commands within `npm run build`.
- Frontend production build: passed with Vite 8.2.2.
- External provider: not invoked by this verification; tests use mock/fake providers.

## Files created in this phase

- `docs/real-clinic-hardening/plan.md`
- `docs/real-clinic-hardening/findings.md`
- `docs/real-clinic-hardening/progress.md`
- `docs/real-clinic-hardening/scenario-matrix.md`
