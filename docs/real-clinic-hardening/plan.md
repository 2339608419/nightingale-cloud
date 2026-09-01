# Real-Clinic Hardening Plan

## Scope

This directory records the independent audit and implementation plan requested for the real-clinic failure-scenario review. It does not replace the repository-root planning files.

## Authoritative brief

- Sole source for scenario numbering, meaning, deliverables, and deadline: `C:\Users\zclin\.codex\attachments\35e2b607-3cc7-43f8-9453-bfeccac537d8\pasted-text.txt`
- Deadline: Thursday, 3 September 2026, 18:00 SGT
- Deliverables: working Git repository; automated tests based on scenarios 1–16; README setup/run instructions; 2–3 page technical brief covering scenarios 1–17, failures, attempts, and changed assumptions; demo video showing as many scenarios 1–16 as possible.

## Current phase

- Phase: 1 — PHI egress, provider ordering, timeout, and safe degradation
- Status: in progress
- Application-code changes allowed: only the minimum changes for original scenarios 3, 4, 8, and 9
- Commit target after explicit authorization: `feat: harden PHI boundaries and AI failure handling`

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

## Errors encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Global `python` command was unavailable when running the planning skill's session-catchup script. | 1 | Record the failure and use the repository's existing backend virtual-environment interpreter for project verification. No retry of the same command. |
| Initial explicit `git add` could not create `.git/index.lock` because the managed workspace exposes `.git` as read-only by default. | 1 | Record the environment failure and retry the same narrow four-file staging operation with repository-scoped elevated Git permission. |
| The first combined Phase 1 documentation patch expected `# Phase 0 Progress`, but the actual heading is `# Phase 0 Progress Log`. | 1 | No partial edit was applied; inspect the exact heading and split the patch into exact-file updates. |
| The first focused-test command used a repository-relative virtual-environment path while its working directory was already `backend`. | 1 | Use the backend-local `.venv\\Scripts\\python.exe` path on the next invocation. |
| The first focused run had one test false positive because it asserted that the common word `and` was absent from the entire structured response. | 1 | Keep the privacy assertion precise: check complete PHI values and meaningful clinical phrases rather than generic words used by safe validation metadata. |

## Completion gate

Phase 0 is complete only when all checklist items are complete, evidence is recorded without unsupported claims, the test/build results are captured, the staged diff contains only this directory, and the local commit succeeds.
