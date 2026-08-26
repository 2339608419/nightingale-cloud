# Nightingale Required Micro-tests and Adaptive Importance Plan

## Goal
Complete the required candidate micro-test set and add a deterministic, inspectable adaptive heuristic for future highlight ranking.

## Phases
- [x] Inspect all backend tests and existing highlight model/service/scoring/frontend paths
- [x] Add clinic-scoped adaptive preference persistence and explainable scoring
- [x] Add highlight suggestion generation plus clinician accept/reject endpoints
- [x] Add frontend status presentation and accept/reject controls
- [x] Add `test_self_learning_importance.py` and verify all five required micro-test files
- [x] Document adaptive heuristic weights and remaining limitations
- [x] Run complete backend suite, frontend production build, and final scope review

## Constraints
- No complex ML model; use deterministic counters and capped additive bonuses.
- Preserve base risk/recency/entity/task/confirmation scoring and provenance requirements.
- Preference state is clinic-scoped and inspectable.
- Clinician remains final authority for accept/reject.
- Do not implement unrelated features.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| None yet | - | - |
