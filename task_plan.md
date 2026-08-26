# Nightingale Final Submission Audit Plan

## Goal
Audit the completed prototype against the candidate brief, add a measured warm-path benchmark, fix only concrete hard-requirement issues, and produce an evidence-backed final report.

## Phases
- [x] Read project requirements, README, attribution, and enumerate all backend/frontend/test files
- [x] Read and audit every backend model/schema/route/service plus all tests
- [x] Read and audit all frontend source and runtime/build configuration
- [x] Build requirement checklist with PASS/PARTIAL/MISSING evidence
- [x] Add and run repeatable warm-path Glance benchmark with median/P95 reporting
- [x] Fix only concrete hard-requirement, security, provenance, test, or demo blockers
- [x] Run full backend tests, frontend production build, runtime/config checks, and final diff review
- [x] Write and deliver final audit report with top five remaining risks

## Constraints
- No redesign, major feature work, broad refactors, or cosmetic-only changes.
- Never fabricate benchmark numbers; record request count, median, P95, environment, and limitations.
- Prioritize hard requirements, demo blockers, security/provenance, required tests, performance, then docs.
- Treat claims as unverified until supported by code inspection and executed commands.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| Initial documentation patch expected a README line that differed from the file | 1 | Re-anchored to the exact Known Limitations section; no application effect. |
