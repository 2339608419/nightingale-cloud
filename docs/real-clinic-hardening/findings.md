# Phase 0 Findings

## Phase 9 AI Scribe UI

- Staged review identified a genuine safety-view gap: initial success callback inserted only
  Timeline data, leaving Glance/conflicts/evidence stale after server conflict detection.
  Success now starts an independent all-or-nothing read of highlights (including confidence),
  permitted conflicts, review queue and metrics. Cached source views are cleared on success.
- Refreshing/failed views are explicitly not current; old safety lists/badges are withheld,
  not silently shown as fresh. Read-only retry never changes generation success/draft state.
  Initial patient loading completes before enabling Scribe, preventing its older response
  from overwriting post-generation safety data. Context disposal/latest-request epochs guard
  late reads. No full-page reload or Scribe unmount is used for this refresh.

- Existing backend protocol already supplies five outcomes; failure bodies on 502/503/504
  are root JSON, unlike the generic API helper's detail-only errors. Added a dedicated adapter;
  no backend changes, provider configuration changes or external provider calls.
- A memory-only controller owns draft/request state, synchronous submission lock, stable random
  source ID for known-safe retries, and an invalidation epoch. The keyed React form resets on
  patient/clinic/user/role change and disposes on unmount; late callbacks cannot add old entries.
- Only validated success adds a Timeline entry; failure never clears existing clinical content.
  Drafts are not saved in browser storage. Waiting disables inputs/submission. Known abstention
  permits explicit manual retry; unknown network/lost/inconsistent responses block retry and
  require refresh/Timeline inspection. No automatic retry, cancellation or reconciliation claim.
- Mode is unknown until server response, then explicitly mock/external/test double. Form does
  not enable/select providers; default backend configuration remains offline mock.
- 11 new controller/adapter tests plus 3 existing frontend tests pass. These are not DOM/E2E
  tests. Full backend regression remains 182 passes/one existing warning. Scenarios 8/9 PARTIAL.

## Phase 8 documentation/delivery reconciliation

- Confirmed Phase 7 HEAD; no application edits, dependency installation or test rerun.
- Old brief reported 89 tests and early provenance design. Updated three-unit brief targets
  2–3 pages and covers original 1–17, failed attempts and changed assumptions; not rendered.
- README now names the clone destination and avoids implying a formal Clinic model or
  authenticated independent reviewers. Old benchmark is historical, not current SLA proof.
- remaining-work.md separates local implementation, mocks, absent/external work, Clinic B
  change categories, resource decisions and delivery gates; verdicts unchanged.
- Local repo/tests/instructions exist. Recipient access, current PDF and video coverage remain
  unverified. Existing PDF/video and protected user files were not read or changed.
- Phase 7 evidence: 182 backend passes/one warning, 3 frontend passes, TypeScript/build passed.
  Phase 8 did not rerun them. No blocking defect found in documentation review; no fresh
  runtime audit is claimed.

## Phase 7 integration acceptance result

- The pre-change baseline was 163 passing backend tests. No application regression or demo
  blocker was found, so Phase 7 changes only tests and documentation.
- `test_real_clinic_scenarios.py` now supplies one direct, numbered executable acceptance test
  for every original scenario 1–16 plus a Phase 5 state-machine audit and two database smokes.
  It deliberately reuses deeper focused assertions rather than weakening or copying them.
- Phase 5 audit confirms: repeated same decision is a no-op without duplicate audit/contribution;
  one actor/highlight has one active row; accept→reject replaces state; undo is idempotent;
  negative learning needs two distinct clinician IDs (not verified independent humans, because
  development identity headers remain forgeable); one clinician across two highlights is
  still one rejector; Clinic A does not affect Clinic B; exposure reference is idempotent;
  patient/staff/admin writes are denied; the review queue is outside top Glance; metrics and
  audit metadata contain no clinical text; the importance service applies floors last.
- Cross-stage acceptance re-proves consult→Draft→approval→patient visibility/delivery,
  correction→STALE/approval invalidation/correction state, immutable highlight versions,
  dual conflict evidence, phone-session filtering, tenant scope, metadata-only/no-op audits,
  and provider-failure no-entry behavior through the numbered tests and their focused suites.
- Fresh-file SQLite create/seed and current-schema close/reopen/create_all/reseed both pass.
  This does not make historical schema upgrades compatible: existing databases predating
  column changes still require rebuild, and production requires real migrations.
- Isolated manual UI smoke used a new ignored database and an isolated local Vite proxy. It
  verified Glance display, failed-not-delivered fixture, synthetic/no-audio labeling,
  minute-two signal, Montelukast confirmation, three distinct rule-derived summaries, Draft
  approval, patient-only visibility, and zero browser console warnings/errors. Provider outage,
  clinic fault injection, stale 409, and correction flows remain TestClient/logic evidence,
  not claimed browser E2E.
- Immutable-source navigation was separately checked on the existing local dataset; it was
  not repeated in the fresh eight-entry browser run. Fresh-state immutable provenance is
  covered by TestClient, not claimed as a complete fresh-state browser rehearsal.

## Phase 6 verified design/result

- Staged review hardening makes audience-summary finalization atomic. The patient-entry helper
  retains default commit behavior for existing callers but supports transaction ownership by
  consult finalization. All entries, initial versions, Draft approval, summary companion rows,
  final state, and metadata audit commit once; injected failure rolls everything back and marks
  the session `failed` in a separate safe transaction. Failed sessions require a new session.
- Partial observations now have an explicit append-only finalization path for staff/clinician:
  a conditional current-partial claim supersedes v1, creates final v2 with a new immutable
  pointer, and only v2 derives facts. Correction and create share language-span/alternative
  validation; invalid corrections cause no state, summary, approval, or audit change.
- A Timeline Entry retains its single primary pointer. Complete multi-segment provenance lives
  in `ConsultSummary.source_provenance`; the patient instruction points through the clinician
  summary and approval gate. Correction marks summaries STALE and does not regenerate them.
- The contract is explicitly `synthetic_text_stream`: it starts after hypothetical ASR and stores no audio. Session state, simulated noise label, provider state, timed speakers, partial/final state, alternatives, uncertainty, and per-character language spans are structured rather than inferred from one blob.
- English/Malay/Hokkien code switching and English/Mandarin/Tamil readiness fixtures retain original synthetic language evidence. Unsupported labels remain unsupported and deterministic extraction emits Needs Confirmation instead of pretending the content is English or confirmed.
- A finalized minute-two allergy segment creates an internal HIGH provisional signal as soon as that text segment is received. This is not a real-time microphone/ASR claim; partial text does not generate a confirmed fact, final summaries wait for session completion, and patient visibility remains gated.
- The Montelukast 20/50 mg capture stores the exact synthetic phrase, both candidates, uncertainty, segment/version pointer, and curated prototype reference metadata. Reference scope is term/unit plausibility only. It cannot select the patient's dose; only clinician confirmation can, with metadata-only audit.
- Rule-derived completion creates different clinician, staff, and patient texts. The clinician output carries unresolved uncertainty and safety-review context; staff receives operational action language; patient receives plain language without an asserted uncertain dose and enters the existing AI-derived instruction approval/delivery workflow as Draft.
- Segment correction is append-only/versioned. It supersedes old signals/captures, makes all summaries STALE, invalidates patient approval, and never migrates old confirmation automatically. BROKEN/missing linked evidence returns a safe error rather than guessed content.
- All patient-linked consult queries constrain ConsultSession and owning Patient clinic in SQL. Patients cannot access raw consult state, segments, captures, signals, or internal summaries; staff sees only its audience summary; clinician-only actions remain server enforced.
- Synthetic source text is stored for the immutable provenance demonstration only. Logs contain opaque UUIDs, states, enums, sequence/counts; audit contains status metadata only. The Phase 6 rule generator does not invoke a Provider.
- This remains additive `create_all` compatibility, not a migration. Real audio, noisy-clinic ASR accuracy, WER/language confidence, speaker diarization, clinical validation, live reference search, and production transcript governance remain unimplemented.

## Phase 5 verified design/result

- Exact synthetic ordering is now supported: a staff/nurse `Penicillin allergy is active` entry followed by an AI/patient-derived `No known allergies` entry retains both TimelineEntries and creates an open ConflictRecord (`backend/app/services/conflict_service.py:134`). Staff-over-AI is an explicit prototype authority policy, while `unresolved_requires_review` remains true until a clinician resolves it.
- Allergy conflicts deterministically create a HIGH/65 conflict-aware Highlight if that authoritative source lacks one. Glance displays a prominent Needs Review warning and two source navigation actions; open conflict makes Evidence Confidence abstain. Patient access to the staff/AI evidence and internal conflict remains denied, and Clinic B cannot resolve Clinic A's record.
- Additive `ConflictProvenance` binds authoritative and conflicting entry version numbers/pointers at conflict creation. A focused edit→revert test proves the original v1 pointers do not silently retarget.
- Evidence Confidence has one definition: whether a Highlight is verifiable from its cited immutable evidence. Its seven named inputs, triggered rule, and required action are additive API fields without clinical text. BROKEN pointer/version/span and open conflict abstain; entity mismatch is LOW; exact unstructured evidence is MEDIUM; exact structured or human-confirmed evidence is HIGH. STALE remains separate and requests currentness review. Any evaluation invariant error fails closed to ABSTAIN without a 500 or exception text.
- Additive `HighlightFeedback` provides clinic/highlight/actor/role/decision/timestamps/entity/entry-type metadata only. One actor has one decision per Highlight. Decision change/undo recomputes aggregate contribution rather than incrementing blindly; repeated undo is a no-op without a success audit.
- Positive feedback contributes immediately. Negative feedback remains suppressed until two independent clinicians reject a category, then existing entity/entry-type weights apply subject to the `[-10,+25]` cap. Safety floors still run last, so allergy and other protected categories cannot cross their floor.
- Additive `HighlightExposure` records an explicit post-render clinician impression, idempotent by opaque display reference. Trust metrics distinguish candidate/exposed/unexposed/decided/undecided/undone/suppressed/applied/floor-protected counts and explicitly state they are not accuracy. A separate lower-ranked review queue does not disturb the Top Glance ranking.
- Existing aggregate preferences cannot be reliably reconstructed into actor/exposure history. Untouched categories remain compatible; after the first Phase 5 event for a category, its aggregate is recomputed from attributable actor events rather than mixing unverifiable legacy counts. SQLite `create_all` can add the new tables for synthetic runtime compatibility but is not a migration system.
- Verified results: Phase 5 focused 20 passed; broader security/trust regression 93 passed; complete backend 152 passed; frontend logic 3 passed; TypeScript and production build passed. Manual isolated-DB UI review confirmed the high-risk allergy warning, dual-source actions, Needs Review rule/action, Undo feedback, exposure diagnostics, and not-yet-surfaced queue.

## Phase 4 initial concurrency/provenance inspection

- Two editors starting from version N are database-safe: the first creates N+1 and one audit; the second is rejected before approval, delivery, version, audit, or conflict mutation. However, the old 409 contains only current version and frontend `requestJson` discards even that detail, so there is no explicit comparison/recovery workflow and refresh can lose the local draft.
- Highlight currently stores only mutable entry ID/span and an entry anchor. Confidence re-verifies against current content, so source edits can cause ABSTAIN or accidentally validate a repeated span in a different version; navigation cannot show the original evidence.
- The minimum runtime-compatible design is an additive one-to-one `HighlightProvenance` table rather than columns on the existing Highlight table, because SQLite `create_all` can create a new table but cannot add columns. It binds highlight, source entry, EntryVersion number, exact span, and a non-PHI version-aware pointer.
- Evidence Confidence answers whether the immutable cited evidence resolves and verifies. Source currency independently answers whether that cited version is still current. STALE therefore does not erase valid historical evidence or lower clinical risk; BROKEN causes abstention and no fallback to mutable content.
- Synthetic-only compatibility backfill binds only when exactly one immutable version contains the exact span. Missing or ambiguous evidence remains BROKEN. Formal environments still require versioned migration and stronger transaction semantics than SQLite proves.

## Phase 4 verified design/result

- Authorized edit/revert 409 responses now provide a fixed `entry_version_conflict` structure with entry ID, submitted expected version, current version/content, and current provenance (`backend/app/routes/entries.py:41`). Authorization and clinic-scoped lookup happen first. Stale rejection precedes approval/delivery/conflict mutation and rollback leaves no draft, version, or success audit.
- `frontend/src/api.ts:24` preserves structured error detail in typed `ApiError`; `frontend/src/App.tsx:618` keeps the local draft, compares it with current server text, and offers copy, explicit reload, or cancel-and-keep. Pure frontend recovery tests prove cancel preservation and explicit replacement; no automatic merge/retry exists.
- Additive `HighlightProvenance` (`backend/app/models/highlight.py:104`) binds one Highlight to source entry/version/span/pointer without altering the existing Highlight table. `bind_highlight_to_current_version` (`backend/app/services/highlight_provenance_service.py:31`) verifies the immutable current snapshot and writes binding plus Highlight in one transaction.
- Resolution (`backend/app/services/highlight_provenance_service.py:59`) produces CURRENT, STALE, or BROKEN. Evidence Confidence verifies the immutable snapshot; currency separately reports whether a newer entry version exists. STALE retains valid historical evidence and risk; BROKEN abstains and never substitutes mutable content.
- The clinic-scoped source endpoint (`backend/app/routes/highlights.py:149`) enforces the same source visibility as the current entry. Tests prove Clinic B receives no Clinic A snapshot, a patient cannot read staff/internal evidence, and a patient can read an approved instruction snapshot.
- Existing-runtime compatibility uses the additive table plus exact/unambiguous synthetic-only backfill. All four clean seed highlights bind to v1; missing/ambiguous matches remain BROKEN. Formal migrations and production database concurrency remain unimplemented.

## Phase 3 initial access/delivery/correction inspection

- Patient access currently depends on caller-asserted `X-User-Id`, `X-Role`, and `X-Clinic-Id`. Patient has no phone/email/contact credential, challenge, session, expiry, or replay state, so a no-email patient cannot actually enter through a phone-first flow.
- Existing patient visibility is a server-side portal filter: patients see only their own approved instruction entries. Approval proves clinician authorization for in-app visibility; it does not prove a message was created, queued, accepted by a channel, sent, or delivered.
- `EntryVersion` already provides immutable content snapshots, but `PatientInstructionApproval` does not identify which version was approved. A delivery system cannot safely use mutable `TimelineEntry.content` or infer that today's content equals the copy previously approved.
- Editing/reverting approved AI-derived content correctly returns approval to Draft and preserves history, but no delivery record exists to locate an obsolete copy already outside the portal. There is therefore no correction-required, replacement, supersession, or no-recall record.
- Minimal design: store only a domain-separated digest plus masked representation of a fixed synthetic E.164 contact; use securely random one-time access and session tokens whose database fields contain only digests, expirations, and consumption/revocation state; expose the mock token only once in an explicitly synthetic local response and exchange it by POST rather than URL query.
- Minimal delivery state machine: immutable delivery rows bind clinic, patient, instruction entry, the exact clinician-approved `EntryVersion.version_number`, channel/purpose, masked destination, opaque provider reference, actor, timestamps, and optional replacement relation. Server-only transitions distinguish created, queued, simulated sent, simulated delivered, failed, correction required, and superseded.
- On instruction edit/revert, created/queued old copies must become superseded so they cannot later send; simulated-sent/delivered copies must become correction-required because recall cannot be claimed. A corrected version must return through clinician approval and create a new delivery linked through `replaces_delivery_id`.
- All access and delivery endpoints must combine their own authorization boundary with Phase 2 SQL tenant predicates. Patient-session endpoints should be self-scoped and return only approved instructions plus safe delivery status, never internal provider reference, comments, audit, conflicts, tasks, or AI notes.

## Phase 3 verified design/result

- Phone bootstrap requires both clinic context and a valid synthetic E.164 contact; its SQL lookup includes `Patient.clinic_id` and `phone_is_synthetic`. Valid known and unknown requests have the same public status/field/accepted semantics. Unknown numbers receive a secure random, non-persisted decoy that cannot exchange; masking is derived only from caller input. Invalid formatting remains a separate generic validation error, not an enrollment result.
- Challenge/session tokens are 32-byte URL-safe random values and only domain-separated SHA-256 digests are persisted. Consumption is one conditional SQL update requiring matching digest, unused state, and future expiry. Only a one-row claim can create a session, and claim/session commit share one transaction. A two-session file-SQLite test proves one claimant; SQLite still does not prove production multi-worker behavior.
- Phone uniqueness is `(clinic_id, phone_digest)`, so one synthetic phone can exist in Clinic A and B but cannot duplicate inside either clinic. The challenge query requires clinic context and tests resolve the correct patient in both clinics. Existing runtime SQLite must be rebuilt; production requires a versioned migration and real Clinic/User/Membership identity.
- The full contact is absent from Patient/API responses, logs, audits, and delivery records. The deterministic contact digest remains appropriate only for fixed synthetic data; production phone lookup would require keyed protection/encryption, rotation, and governance against enumeration.
- Delivery creation resolves both the instruction and exact approved EntryVersion through Phase 2 scoped SQL. Delivery listing, mutation, replacement lookup, and edit/revert invalidation also include the stored delivery clinic plus a join to the owning Patient clinic.
- The server state allowlist distinguishes created, queued, simulated sent, simulated delivered, and failed. Failure reason is a database/API enum limited to five non-PHI codes, is required only for Failed, and is forbidden otherwise. Unknown/free-text/PHI-bearing values are rejected before mutation or audit. Correction-required/superseded are system transitions driven by content invalidation and replacement creation, not arbitrary client transitions.
- Existing AI-derived approval authority is unchanged: clinician only. Editing or reverting an approved instruction clears its approved version and patient visibility; unsent deliveries become superseded, while sent/delivered copies become correction-required. Replacement delivery cannot exist until the corrected current version is re-approved.
- All delivery audits reuse the metadata-only allowlist (`from_status`, `to_status`). Denied, invalid, and no-op changes do not add successful-action events; provider reference, destination, token, and clinical content are excluded.
- The frontend is deliberately operational rather than decorative: it labels the synthetic local mock boundary, displays masked destination and approved version, and shows correction/replacement status without claiming a real provider or recall.

## Phase 2 initial tenant-boundary inspection

- The only effective runtime clinic-isolation boundary is the clinic comparison in `require_patient_access` (`backend/app/services/authorization_service.py:29-34`), called by routes after unscoped `get_patient`/`get_entry`/`db.get` lookups. Role, self-access, note ownership, and patient visibility rules are valuable authorization controls but are not a second tenant boundary.
- If that comparison is omitted or becomes a no-op, a caller asserting Clinic B development headers and knowing or guessing Clinic A IDs can reach every currently addressable patient and linked route. There is no patient-list endpoint, so this does not automatically enumerate every tenant record, but known/guessed IDs enable reads and state changes across patient data, timeline entries, versions/audits, highlights, comments, assignments, conflicts, approvals, AI ingestion, and decay preview.
- Patient, TimelineEntry, EntryVersion, AuditLog-by-entry, Highlight, Comment, TaskAssignment, ConflictRecord, and PatientInstructionApproval are currently fetched without a clinic predicate. Tenant ownership is inferred through Patient, and no Clinic/User/Membership model or composite tenant foreign key exists.
- ImportancePreference is the exception: its read/update queries already include `ImportancePreference.clinic_id == clinic_id`; it still trusts the forgeable development identity header and therefore is not production authentication.
- The minimal reliable design keeps the existing outer route guard for RBAC/API compatibility, then re-fetches the target through centralized SQLAlchemy clinic-scoped queries before any response, content access, association, or mutation. Under normal mismatch the outer guard retains the existing 403 contract; when fault-injected to a no-op, the independent scoped query returns no object and the route uses 404/non-visible semantics.
- Indirect scoped queries will join from linked IDs through TimelineEntry or Patient to `Patient.clinic_id`; EntryVersion and AuditLog scope through their parent entry; comments through entry; highlights/assignments/conflicts through patient; approvals through instruction entry, with source entry independently scoped.
- Phase 2 is expected to add one centralized scoped-query service, update all six tenant-bearing route modules and the approval service where needed, add a parameterized guard-failure/cross-entity test matrix, and update README plus the four hardening documents. No schema migration, identity system, frontend redesign, or fake onboarding UI is justified.

## Phase 2 verified result

- `clinic_scope_service.py` now supplies the independent inner SQL boundary. Patient queries bind `Patient.id` and `Patient.clinic_id`; every linked-object lookup joins or filters through that scoped patient instead of reading globally and checking clinic ownership afterward.
- The route-level authorization guard remains intact and executes first under normal operation. Its role, patient-self, ownership, and approval rules are not duplicated into or replaced by the tenant repository.
- Guard-failure testing monkeypatches the effective route imports of `require_patient_access` to a no-op, rather than merely asserting the normal guard returns `403`. Seventeen known-ID read/write/state-change paths then fail at the inner query with `404` and neither disclose clinical markers nor create successful audits.
- Cross-tenant association injection is separately rejected: a Clinic B assignment cannot attach a known Clinic A entry. Same-clinic access continues to work with the outer comparison disabled.
- Existing indexes cover the join/filter columns used by the new queries: patient clinic, entry patient, version entry, audit entity ID, highlight patient/entry, comment entry, assignment patient/entry, conflict patient, approval source entry, and preference clinic. No speculative schema/index migration was added.
- Verified results: focused isolation suite 20 passed; required security/collaboration regressions 98 passed; complete backend suite 119 passed. The remaining warning is a third-party Starlette/httpx deprecation.
- The post-change in-process warm-path check (20 warm-ups, 200 measured requests) reported 5.849 ms median and 7.006 ms P95. This is useful only as a regression approximation because it excludes network latency, browser rendering, production data volume/storage, and concurrent users.
- Scenario 2 now SURVIVES for the repository's tested application paths. Scenario 5 remains PARTIAL because authenticated membership, first-class clinic/user schema, migration tooling, managed deployment, and operational onboarding do not exist.

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
