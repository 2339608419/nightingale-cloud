# Nightingale Longitudinal Timeline Plan

## Goal
Expand the existing Nightingale timeline into a constrained, multi-date longitudinal feed without changing the established architecture or adding unrelated features.

## Phases
- [x] Inspect existing model, schema, service, seed, route, tests, and frontend
- [x] Constrain timeline roles and entry types
- [x] Seed realistic multi-date synthetic longitudinal data idempotently
- [x] Add clinical timeline presentation, AI distinction, provenance, and stable anchors
- [x] Expand retrieval and ordering tests
- [x] Run and fix backend tests and frontend production build
- [x] Review scope and report results

## Constraints
- No highlights, RBAC, revision history, comments, LLM integration, or self-learning.
- Preserve clean boundaries for future prompts.
- Claim only commands actually executed.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| `python` was not on PATH during session catchup | 1 | Located the bundled Python runtime before implementation. |
| Dependency installs were blocked by sandbox networking | 1 | Re-ran approved installs with network access; both completed. |
| Frontend build could not find `node` from pnpm child process | 1 | Re-run with the bundled Node `bin` directory prepended to the process PATH. |
| TypeScript build lacked Vite ambient types and rejected an unnecessary node-config option | 1 | Added `vite/client` types and removed `allowImportingTsExtensions`. |
