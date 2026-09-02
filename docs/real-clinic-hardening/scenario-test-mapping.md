# Scenario 1–16 Automated Acceptance Map

`backend/tests/test_real_clinic_scenarios.py` is the executable numbered index. It reuses the
deeper focused assertions listed below against a fresh synthetic database; it does not turn a
PARTIAL/DOES NOT capability into a claimed success.

| Scenario | Verdict | Direct test | Primary supporting suite | Demonstrable path | Remaining boundary |
|---:|---|---|---|---|---|
| 1 | PARTIAL | `test_scenario_01_phone_only_patient_access` | `test_phone_access_delivery_correction.py` | synthetic phone request/exchange → patient portal | mock identity/delivery only |
| 2 | SURVIVES | `test_scenario_02_clinic_guard_failure` | `test_clinic_isolation_defense.py` | known Clinic A ID with outer guard disabled | no database RLS |
| 3 | PARTIAL | `test_scenario_03_no_phi_or_provider_error_in_logs_and_audit` | AI failure/redaction/audit suites | `/ai-scribe` failure | proxy/crash/third-party retention unproven |
| 4 | SURVIVES | `test_scenario_04_provider_receives_only_redacted_validated_text` | `test_ai_scribe.py`, `test_redaction_validation.py` | `/ai-scribe` fake provider capture | deterministic PHI recognizer |
| 5 | PARTIAL | `test_scenario_05_clinic_b_isolation_not_full_onboarding` | clinic/phone tenant tests | Clinic B scoped patient lookup | no production onboarding/membership/migrations |
| 6 | PARTIAL | `test_scenario_06_code_switched_synthetic_text_and_no_audio_claim` | Phase 6 consult suite | Synthetic Consult Lab/API | no audio or ASR |
| 7 | PARTIAL | `test_scenario_07_minute_two_final_signal_partial_withheld` | Phase 6 consult suite | partial→final segment → signal | post-ASR timing only |
| 8 | PARTIAL | `test_scenario_08_provider_timeout_typed_abstention_no_entry` | `test_ai_provider_failures.py` | configured timeout → 504 abstention | synchronous worker/no circuit breaker |
| 9 | PARTIAL | `test_scenario_09_provider_unavailable_safe_abstention` | `test_ai_provider_failures.py` | 503/invalid → no entry | no outage UI/operations |
| 10 | SURVIVES | `test_scenario_10_stale_edit_safe_409_and_history` | concurrency/revision + frontend logic | stale edit → structured 409 recovery | no automatic merge/multi-worker DB proof |
| 11 | PARTIAL | `test_scenario_11_created_is_not_delivered_and_states_are_distinct` | delivery suite | created/queued/simulated sent/delivered/failed | no real channel/receipt |
| 12 | PARTIAL | `test_scenario_12_wrong_sent_version_requires_traceable_correction` | approval/revision/delivery suite | edit → Draft/correction_required → replacement | no message recall |
| 13 | SURVIVES | `test_scenario_13_nurse_ai_allergy_conflict_has_two_sources` | Phase 5/conflict/provenance suites | nurse fact + AI contradiction → Glance review | narrow demo vocabulary |
| 14 | SURVIVES | `test_scenario_14_evidence_confidence_is_deterministic_and_fail_closed` | Evidence Confidence suite | Glance evidence labels/source state | verifiability, not truth probability |
| 15 | PARTIAL | `test_scenario_15_feedback_guard_undo_exposure_queue_and_floor` | Phase 5 + safety-floor suites | decision/undo/exposure/review queue | human and selection bias remain |
| 16 | SURVIVES | `test_scenario_16_highlight_keeps_immutable_source_after_edit` | highlight provenance suite | edit source → immutable v1 + STALE | SQLite/migration limitations |

Scenario 17 remains the dimension-by-dimension rubric in `scenario-matrix.md`; it is not an
additional scenario 1–16 acceptance test.

## Exact Phase 7 evidence lines

| Scenario | Direct evidence line |
|---:|---|
| 1 | `backend/tests/test_real_clinic_scenarios.py:59` |
| 2 | `backend/tests/test_real_clinic_scenarios.py:63` |
| 3 | `backend/tests/test_real_clinic_scenarios.py:71` |
| 4 | `backend/tests/test_real_clinic_scenarios.py:75` |
| 5 | `backend/tests/test_real_clinic_scenarios.py:79` |
| 6 | `backend/tests/test_real_clinic_scenarios.py:89` |
| 7 | `backend/tests/test_real_clinic_scenarios.py:98` |
| 8 | `backend/tests/test_real_clinic_scenarios.py:102` |
| 9 | `backend/tests/test_real_clinic_scenarios.py:106` |
| 10 | `backend/tests/test_real_clinic_scenarios.py:110` |
| 11 | `backend/tests/test_real_clinic_scenarios.py:114` |
| 12 | `backend/tests/test_real_clinic_scenarios.py:118` |
| 13 | `backend/tests/test_real_clinic_scenarios.py:122` |
| 14 | `backend/tests/test_real_clinic_scenarios.py:126` |
| 15 | `backend/tests/test_real_clinic_scenarios.py:131`; Phase 5 audit `:146` |
| 16 | `backend/tests/test_real_clinic_scenarios.py:142` |
| 17 | `backend/tests/test_phase6_multilingual_consult.py:45-325`; dimension matrix in `scenario-matrix.md` |

Database smoke evidence is at `backend/tests/test_real_clinic_scenarios.py:200` and `:212`.
