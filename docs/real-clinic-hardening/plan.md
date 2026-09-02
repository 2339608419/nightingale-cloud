# Real-Clinic Hardening Plan

## Scope

This directory records the independent audit and implementation plan requested for the real-clinic failure-scenario review. It does not replace the repository-root planning files.

## Authoritative brief

- Sole source for scenario numbering, meaning, deliverables, and deadline: `C:\Users\zclin\.codex\attachments\35e2b607-3cc7-43f8-9453-bfeccac537d8\pasted-text.txt`
- Deadline: Thursday, 3 September 2026, 18:00 SGT
- Deliverables: working Git repository; automated tests based on scenarios 1–16; README setup/run instructions; 2–3 page technical brief covering scenarios 1–17, failures, attempts, and changed assumptions; demo video showing as many scenarios 1–16 as possible.

## Current phase

- Phase: 7 — scenarios 1–16 integration acceptance and demo stability
- Status: verification complete; eight Phase 7 files staged, awaiting explicit commit authorization
- Application-code changes allowed: only concrete regressions found by acceptance testing
- Commit target after explicit authorization: `test: cover real-clinic resilience scenarios`

## Phase 0 objectives

- Establish the exact Git and working-tree baseline.
- Inspect requirements, documentation, backend, frontend, database models, routes, services, and tests.
- Run the complete backend test suite.
- Run frontend TypeScript validation and production build.
- Evaluate scenarios 1–17 as SURVIVES, PARTIAL, or DOES NOT.
- Distinguish tested implementation, insufficiently tested implementation, mock/demo-only behavior, and missing behavior.
- Produce a risk-ordered dependency plan for Phases 1–8.
- Stage only this directory's Phase 0 documents; create the local commit only after explicit authorization.

## Explicit exclusions

- Existing tracked changes in root `task_plan.md`, `findings.md`, and `progress.md`.
- Untracked `Demo Video.mp4`, `Resume-Zhanchen Lin.pdf`, `output/`, and `read.md`.
- Application code, tests, seed data, and runtime database changes.
- Push, rebase, force-push, reset, clean, or broad staging commands.

## Work checklist

- [x] Capture branch, HEAD, status, and existing diff summary.
- [x] Inventory architecture and documentation.
- [x] Inspect backend models, routes, services, and authorization boundaries.
- [x] Inspect frontend behavior and API integration.
- [x] Inspect all tests and map evidence to scenarios.
- [x] Run complete backend tests.
- [x] Run frontend TypeScript check and production build.
- [x] Complete scenario matrix for scenarios 1–17.
- [x] Complete findings and risk-ordered future-phase plan.
- [x] Verify unstaged and staged diffs.
- [x] Commit only Phase 0 documents (`058020d428b0a597dec14363513aae1ba8b9735c`).

## Phase 1 checklist

- [x] Confirm Phase 0 HEAD and preserve the pre-existing root working-tree changes.
- [x] Inspect the AI-scribe, redaction, validation, provider, logging, exception, audit, and test paths.
- [x] Implement typed, sanitized provider outcomes and configurable timeout handling.
- [x] Preserve and test the single redaction → validation → provider boundary.
- [x] Prove failure paths create no ordinary AI timeline entry and leak no clinical/PHI text.
- [x] Run focused tests, the complete backend suite, frontend checks/build, and diff checks.
- [x] Update scenarios 3, 4, 8, and 9 strictly from verified evidence.
- [x] Explicitly stage only Phase 1 files and request commit authorization.
- [x] Reverify and restage the Phase 1 source-reference PHI correction found during staged review.

## Phase 2 checklist

- [x] Confirm Phase 1 HEAD and preserve all pre-existing root/user working-tree state.
- [x] Enumerate every patient-ID and linked-entity access path and its tenant constraint.
- [x] Document the current single boundary, actual blast radius, and unscoped entities before code changes.
- [x] Implement a centralized independent clinic-scoped query boundary.
- [x] Add guard-failure injection and cross-entity read/write/association tests.
- [x] Run focused, relevant, full-backend, frontend-build, and diff verification.
- [x] Update scenarios 2 and 5 plus the Clinic B onboarding categories without overclaiming.
- [x] Explicitly stage only Phase 2 files and request commit authorization.

## Phase 3 checklist

- [x] Confirm Phase 2 HEAD and preserve all pre-existing root/user working-tree state.
- [x] Inspect identity, patient visibility, approval, revision, seed, and frontend patient paths.
- [x] Define the minimum phone-token, immutable delivery, and correction state machines.
- [x] Implement synthetic phone-first access without exposing plaintext credentials or destinations.
- [x] Implement clinic-scoped mock delivery bound to approved immutable versions.
- [x] Invalidate approval and mark previously sent copies correction-required after edit/revert.
- [x] Add focused scenario 1, 11, and 12 tests plus required regressions.
- [x] Add minimal frontend visibility for access, delivery, and correction states.
- [x] Update README and scenarios 1, 11, and 12 without overstating mock delivery.
- [x] Run focused, relevant, full-backend, frontend-build, and diff verification.
- [x] Explicitly stage only Phase 3 files and request commit authorization.
- [x] Remove phone-enrollment enumeration from the public challenge response.
- [x] Replace challenge SELECT/check/update with an atomic database claim.
- [x] Change phone uniqueness to `(clinic_id, phone_digest)` and prove per-clinic resolution.
- [x] Restrict delivery failure reason to a fixed safe enum with no-side-effect rejection tests.
- [x] Re-run all Phase 3 verification and precisely restage after staged review.

## Phase 4 checklist

- [x] Confirm Phase 3 HEAD and preserve all root/user working-tree state.
- [x] Inspect optimistic concurrency, 409 handling, frontend draft state, EntryVersion, Highlight provenance, confidence, seed, and SQLite compatibility.
- [x] Add authorized structured 409 recovery data without changing stale-write rejection.
- [x] Add frontend typed error handling and explicit local-draft recovery controls.
- [x] Add an additive immutable HighlightProvenance companion model and version-aware source endpoint.
- [x] Separate CURRENT/STALE/BROKEN currency from Evidence Confidence.
- [x] Add scenario 10/16 focused backend and frontend logic tests.
- [x] Run complete regression, frontend checks/build, manual CURRENT/STALE/BROKEN UI review, and diff checks.
- [x] Update README and scenarios 10/16 from final verified evidence.
- [x] Explicitly stage only Phase 4 files and request commit authorization.

## Phase 5 checklist

- [x] Confirm Phase 4 HEAD and preserve all root/user working-tree state.
- [x] Inspect conflict extraction/order, Glance visibility, immutable evidence, confidence, feedback, floors, audit, and UI.
- [x] Detect the exact nurse-allergy then AI-no-allergy ordering and retain both sources.
- [x] Bind both conflict sources to immutable versions and create a HIGH conflict-aware Glance warning.
- [x] Make Evidence Confidence definition/inputs/rules/actions explicit and fail closed.
- [x] Add actor-aware decision replacement/undo and a two-independent-clinician negative guard.
- [x] Add explicit idempotent exposure, trust diagnostics, and a lower-ranked review queue.
- [x] Prove learning-before-floor order, clinic isolation, metadata-only records, and no LLM confidence call.
- [x] Run focused/security/full backend tests, frontend tests/build, manual UI review, and diff checks.
- [x] Update README and scenarios 13–15 without overstating residual bias.
- [x] Explicitly stage only Phase 5 files and request commit authorization.

## Phase 6 checklist

- [x] Confirm Phase 5 HEAD and preserve all root/user working-tree state.
- [x] Inspect text ingestion, visibility, provenance, conflict, approval, timeout/abstention, and frontend paths.
- [x] Report the pre-change audio/ASR/language/timing/dose/audience gaps and minimum vertical slice.
- [x] Implement synthetic post-ASR session/segment state, multilingual spans, provisional signals, captures, summaries, and immutable correction behavior.
- [x] Add focused scenario 6/7/17 tests and complete regression/build/manual verification.
- [x] Update README and scenarios 6/7/17 dimension by dimension without claiming real ASR/audio.
- [x] Harden staged review: atomic summary transaction, fail-closed session state, shared correction validation, and append-only partial→final.
- [x] Explicitly stage only Phase 6 files and request commit authorization.

## Phase 7 checklist

- [x] Confirm Phase 6 HEAD and preserve all root/user working-tree state.
- [x] Run the 163-test backend baseline and map existing evidence to scenarios 1–16.
- [x] Audit Phase 5 feedback replacement, undo, exposure, negative guard, clinic scope,
  role restriction, metadata, review queue, and safety-floor ordering.
- [x] Add executable numbered scenario 1–16 acceptance tests and human-readable mapping.
- [x] Add fresh-database and current-runtime restart/seed smoke tests.
- [x] Run focused scenario, Phase 5, full backend, frontend logic, TypeScript, and build checks.
- [x] Run an isolated manual browser smoke for Glance display, multilingual consult, minute-two
  signal, Montelukast confirmation, distinct summaries, approval, and patient visibility.
- [x] Update README, Demo Runbook, and hardening evidence without changing verdict boundaries.
- [x] Explicitly stage only Phase 7 files and request commit authorization.
- [ ] Create Phase 7 commit only after explicit authorization.

## Errors encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Global `python` was unavailable for the planning skill session-catchup command at Phase 3 start. | 1 | Do not repeat the same command; use the repository virtual-environment Python for any required project scripts and recover context from the four hardening documents plus Git state. |
| The first Phase 3 focused run expected a bearer-only internal request to return `401`, but the shared TestClient fixture automatically supplied clinician development headers in addition to the bearer token. | 1 | Explicitly blank the three development identity headers for bearer-only negative checks; this tests the intended credential boundary instead of accidentally authenticating as the fixture clinician. |
| The first complete backend run had 129 passes and one API contract assertion failure because the intentionally additive `approved_version_number` response field was absent from the test's exact field set. | 1 | Update the existing contract test to include the new immutable approval-version field; no response field was removed or renamed. |
| The first local browser wait requested unsupported `networkidle` state from the in-app adapter. | 1 | Use the documented `domcontentloaded` state and then inspect a fresh semantic DOM snapshot; do not repeat the unsupported wait. |
| Global `python` command was unavailable when running the planning skill's session-catchup script. | 1 | Record the failure and use the repository's existing backend virtual-environment interpreter for project verification. No retry of the same command. |
| Initial explicit `git add` could not create `.git/index.lock` because the managed workspace exposes `.git` as read-only by default. | 1 | Record the environment failure and retry the same narrow four-file staging operation with repository-scoped elevated Git permission. |
| The first combined Phase 1 documentation patch expected `# Phase 0 Progress`, but the actual heading is `# Phase 0 Progress Log`. | 1 | No partial edit was applied; inspect the exact heading and split the patch into exact-file updates. |
| The first focused-test command used a repository-relative virtual-environment path while its working directory was already `backend`. | 1 | Use the backend-local `.venv\\Scripts\\python.exe` path on the next invocation. |
| The first focused run had one test false positive because it asserted that the common word `and` was absent from the entire structured response. | 1 | Keep the privacy assertion precise: check complete PHI values and meaningful clinical phrases rather than generic words used by safe validation metadata. |
| The first Phase 2 focused matrix setup queried comments on `entry-demo-006`, but seeded comments belong to `entry-demo-007`; all 17 parameterized cases therefore failed before exercising isolation. | 1 | Inspect the seed relationship, correct the fixture entry ID to `entry-demo-007`, and rerun the focused matrix; the three setup-independent cases already passed. |
| The first post-review focused run could not import `Base` from `app.models`. | 1 | Import the existing public `Base` export from `app.database`; no application change was needed. |
| The first duplicate-phone test used the fixture database without requesting the `client` fixture that installs its dependency override. | 1 | Add the fixture dependency to the test signature; the corrected focused suite passed. |
| The first requested regression command named a nonexistent `test_audit_trust_actions.py`. | 1 | Inspect the test inventory and rerun once with the existing `test_trust_action_audit.py`; 85 tests passed. |
| The first immutable provenance schema made the version pointer globally unique, but two highlights may legitimately cite different spans in the same immutable entry version. | 1 | Keep the version-aware pointer indexed but non-unique; highlight identity remains unique while the pointer correctly identifies the shared source version. |
| The first Phase 4 stylesheet patch expected a standalone `.source-focus` selector, while the file uses `.entry-card.source-focus`. | 1 | Inspect the exact stylesheet and add the minimal styles beside the existing error/media section. |
| The first combined focused/build command ran `npm` from the repository root rather than `frontend`. | 1 | Record the path error and run frontend commands from the frontend directory. |
| The first Node strip-types frontend test used a TypeScript parameter property unsupported in strip-only mode. | 1 | Expand `ApiError` to ordinary declared fields plus constructor assignments; three frontend recovery tests then passed. |
| The initial isolated UI backend could not bind port 8000, and direct 5174→8002 requests initially failed CORS. | 1 | Do not terminate unknown processes; verify the old ports were later free, then use allowed frontend origin 5173 with isolated backend 8002. |
| The first temporary SQLite command for BROKEN UI state had PowerShell/Python quote syntax failure. | 1 | Use a corrected single nonclinical companion-row update against only the ignored temporary Phase 4 database. |
| Two final verification invocations used repository-relative backend paths while already running from the repository or backend directory, so pytest did not start. | 1 | Correct the working-directory/path pairing and rerun the focused and complete suites; treat these as invocation errors, not test failures. |
| First Phase 5 related regression exposed the intended compatibility gap: actor events initially recomputed entity but not entry-type contribution. | 1 | Store the safe entry-type category on the same actor event and deterministically recompute both existing aggregate dimensions; restored the tested +7 positive behavior. |
| First Phase 5 focused run called immutable Highlight binding without its explicit expected-version argument and retained three old tests that expected one actor's repeated rejects to learn immediately. | 1 | Pass `None` explicitly and update the tests to the new independent-clinician negative guard; subsequent focused/security runs passed. |
| First Phase 5 frontend patch expected type aliases and a multiline CSS selector while the repository uses interfaces and compact selectors. | 1 | No partial frontend change was applied; inspect actual declarations and apply smaller exact-context patches. |
| First manual UI load used an older local frontend process pointed at an unavailable/older backend and exposed a missing-field render error. | 1 | Make label rendering defensive, then use isolated ignored Phase 5 databases and an isolated allowed-origin frontend/backend pair; manual UI review passed. |
| A final combined regression command referenced the nonexistent historical filename `test_clinic_isolation.py`, so that invocation collected no tests. | 1 | Enumerate the repository's actual test filenames, rerun the intended regression with `test_clinic_isolation_defense.py`, then run the complete suite; 93 and 152 tests passed respectively. |
| Global `python` was unavailable for the planning skill catch-up command at Phase 6 start. | 1 | Do not repeat it; recover from the committed hardening documents and Git state, and use the backend virtual-environment interpreter for project commands. |
| First Phase 6 focused test exposed a greedy Montelukast ambiguity regex that captured `0 mg` instead of `20 mg`. | 1 | Make the prefix match non-greedy so both complete candidate values are retained; rerun the focused suite. |
| Manual Phase 6 UI finalization immediately triggered the parent reload path, unmounting the Lab before its three summaries could remain visible. | 1 | Keep finalized Lab results local and remove the automatic Timeline reload; users can explicitly refresh/switch role when they want new Timeline entries. |
| The first line-reference search used an unbalanced regular expression and returned no references. | 1 | Use exact literal pattern searches across the known Phase 6 files and record the resulting line numbers. |
| Phase 6 staged-review frontend verification requested a nonexistent `npm run typecheck` script. | 1 | Use the repository's actual checks (`npx tsc --noEmit` for both tsconfigs); the production build also runs both checks before Vite and passed. |
| The first Scenario 5 acceptance assertion required 404, but the normal outer authorization boundary correctly returned 403 before the inner 404-hiding query. | 1 | Accept the established 403/404 API boundary and assert that no patient marker is disclosed; Scenario 2 separately fault-injects the outer guard and proves inner SQL returns 404. |
| A patch adding runtime smoke tests matched an earlier `iterator.close()` and temporarily placed the remainder of the Phase 5 audit test inside the restart test. | 1 | Inspect the exact function boundary, move the state-machine assertions back into their test, and rerun the entire scenario suite successfully. |
| The first isolated browser attempt reused an older ignored Phase 7 database and a pre-existing port-5173 frontend, so it was not valid fresh-state evidence. | 1 | Stop only the backend process started by this task, use a uniquely named ignored database plus an isolated Vite proxy on 5175, then rerun and verify the fresh eight-entry seed before any smoke mutation. |
| A line-reference search used a Unix-style wildcard path that PowerShell passed literally to `rg`. | 1 | Search the explicit files/directories without the unsupported wildcard and record exact scenario test lines in `scenario-test-mapping.md`. |
| Sandbox denied process command-line inspection during final cleanup. | 1 | Read-only elevated inspection showed the frontend process had exited and the old backend PID had been reused by an unrelated service. Do not terminate reused PIDs; no unrelated process was stopped. |

## Completion gate

Phase 7 is ready for commit authorization only when final evidence and test/build results are
captured, the staged diff contains only explicitly listed Phase 7 test/documentation files,
and no user-owned root files are staged. The local commit remains a separate, user-authorized
action.
