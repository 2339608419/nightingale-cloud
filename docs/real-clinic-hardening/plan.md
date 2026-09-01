# Real-Clinic Hardening Plan

## Scope

This directory records the independent audit and implementation plan requested for the real-clinic failure-scenario review. It does not replace the repository-root planning files.

## Authoritative brief

- Sole source for scenario numbering, meaning, deliverables, and deadline: `C:\Users\zclin\.codex\attachments\35e2b607-3cc7-43f8-9453-bfeccac537d8\pasted-text.txt`
- Deadline: Thursday, 3 September 2026, 18:00 SGT
- Deliverables: working Git repository; automated tests based on scenarios 1–16; README setup/run instructions; 2–3 page technical brief covering scenarios 1–17, failures, attempts, and changed assumptions; demo video showing as many scenarios 1–16 as possible.

## Current phase

- Phase: 0 — Baseline audit and implementation plan
- Status: verification complete; local commit pending explicit authorization
- Application-code changes allowed: no
- Commit target: `docs: audit real-clinic failure scenarios`

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
- [ ] Commit only Phase 0 documents.

## Errors encountered

| Error | Attempt | Resolution |
|---|---:|---|
| Global `python` command was unavailable when running the planning skill's session-catchup script. | 1 | Record the failure and use the repository's existing backend virtual-environment interpreter for project verification. No retry of the same command. |
| Initial explicit `git add` could not create `.git/index.lock` because the managed workspace exposes `.git` as read-only by default. | 1 | Record the environment failure and retry the same narrow four-file staging operation with repository-scoped elevated Git permission. |

## Completion gate

Phase 0 is complete only when all checklist items are complete, evidence is recorded without unsupported claims, the test/build results are captured, the staged diff contains only this directory, and the local commit succeeds.
