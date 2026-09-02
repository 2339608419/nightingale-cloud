# Remaining work and delivery gates

Phase 8 is documentation/delivery reconciliation, not completion of every feature.
Baseline: Phase 7 `c6c3f309d28709c2060665eafb9f704af961f1cf`. Synthetic data only.
Scenario numbering and deadline follow the original interviewer brief; verdicts are unchanged.

## Requirement classification

Implemented means locally implemented/tested, not production-ready. Simulated describes
the external boundary; a scenario may contain both implemented controls and a simulated channel.

| Scenario | Implemented locally | Only simulated | Not implemented / external resources needed |
|---:|---|---|---|
| 1 | Phone digest, atomic challenge, patient session/filtering | Challenge delivered in local response | Verified phone ownership, production OTP/identity provider |
| 2 | Outer authorization + independent SQL tenant scope | Synthetic clinic identities | Verified membership, database RLS, production load evidence |
| 3 | Sanitized errors/logs, metadata audits, opaque source IDs | Synthetic PHI tests | Proxy/crash/vendor retention audit; infrastructure access/policy |
| 4 | Redact → validate → provider; fake-provider capture tests | Offline mock/provider failure doubles | Broad clinical DLP evaluation; external provider privacy review |
| 5 | Clinic-scoped queries and phone uniqueness | Clinic B fixture | Config, schema, membership, migration, deployment and onboarding below |
| 6 | Text/language span preservation | Post-ASR multilingual fixtures | Real speech recognition and language-quality evaluation |
| 7 | Final-segment provisional signal, append-only partial→final | Supplied minute-two offset | Live audio latency/ASR evaluation |
| 8 | Configurable timeout and safe abstention | Hung provider test | Outage UI, worker/circuit-breaker operational validation |
| 9 | Typed failure/no entry, offline mock | 503/invalid response tests | Long-outage monitoring and bounded recovery operations |
| 10 | 409 recovery, independent-entry editing, snapshots | TestClient/local concurrency | Durable crash recovery, production DB contention tests |
| 11 | Immutable delivery state and safe failure enum | Sent/delivered/failed channel | Messaging account, consent/templates, signed receipts |
| 12 | Approval, invalidation, correction/replacement history | Patient phone delivery | Correction delivery/escalation; no guaranteed remote recall |
| 13 | Exact allergy conflict, two immutable sources, review | Demo clinical vocabulary | Governed broader clinical extraction/evaluation |
| 14 | Deterministic evidence checks and abstention | Synthetic correctness fixtures | Clinical correctness studies, not model self-confidence |
| 15 | Actor decisions/undo, exposure, review queue, final floors | Distinct development actor IDs | Authenticated independent people, bias evaluation |
| 16 | Version/span provenance, STALE/BROKEN | Local runtime fixtures | Migration/backfill reports, multi-worker validation |
| 17 | Immutable segments, ambiguity/confirmation, atomic distinct summaries | Post-ASR text, curated catalog, rule-derived output | Streaming audio/noisy ASR, journal integration, clinical multilingual validation |

Scenario 17 includes all dimensions: real audio streaming and noisy-clinic ASR are DOES NOT;
code-switching, dosage capture, provenance and audience summaries work only in the documented
prototype scope. Reference assistance, multilingual readiness and extraction/mutation robustness
remain PARTIAL. A journal can check general evidence, never confirm what this patient said or
which dose is intended; human confirmation must remain separate.

## Minimum next steps, resources and decisions

| Priority | Work and smallest next step | Account / cost / user decision |
|---|---|---|
| P0 delivery | Render updated Markdown to 2–3 page PDF; check all pages and links; do not assume existing PDF is current | Choose export tool/layout and destination; no dependency installed this phase |
| P0 delivery | Record selected 1–16 scenarios using runbook; review labels, audio and timestamps | User recording/review time; choose duration and output filename; existing video untouched |
| P0 delivery | Verify intended repository/zip includes authorized commits, links are recipient-accessible, and final email attachments match | User authorization for publication/sending and recipient access check; no push/send performed |
| P1 identity/tenancy | Replace forgeable headers; model Clinic/User/Membership and select active clinic from verified membership | Identity provider account, hosting budget and multi-membership policy; costs depend on vendor/usage |
| P1 privacy/operations | Inventory proxy/crash/provider logs and retention; configure safe redaction, access and incident handling | Infrastructure/vendor admin access, approved retention/legal policy; possible hosting/monitoring fees |
| P1 persistence | Add versioned migrations; validate orphan/cross-tenant links; test managed DB concurrency and restore | DB host/account/budget; retention/RPO/RTO decisions; never migrate real data in this prototype task |
| P1 delivery | Implement one approved messaging adapter and signed receipt callback with bounded retries/idempotency | SMS/WhatsApp provider account, sender/template approval, consent policy and per-message budget |
| P2 reliability | Add visible outage state and bounded worker recovery; measure deployed warm-path latency | Hosting/load-test budget and latency target; old benchmark is not current SLA proof |
| P2 audio/languages | Evaluate one streaming ASR adapter on consented or synthetic noisy/code-switched material before integration | ASR account or local hardware, audio-minute/compute budget, language reviewers and consent policy |
| P2 clinical/reference | Version a reviewed terminology/reference set and test capture errors and dose ambiguity | Clinician time, journal/API access/licensing if used; choose supported vocabulary/languages |
| P2 learning | Verify real actors, audit correlated decisions and review-queue sampling without lowering floors | Clinical governance and study design; no claim of unbiased learning |
| P3 UX/storage | Browser E2E/crash recovery and true hot/cold storage only after privacy/retention design | Browser test environment/storage budget; user prioritization; current decay is preview only |

No vendor selected and no price quoted/verified. These are resource categories, not permission
to buy services or use real patient data.

### Clinic B changes must stay distinct (scenario 5)

- Config: display, allowed origins, provider/channel settings, secrets and feature flags.
- Schema: Clinic/User/Membership, tenant constraints/indexes and migration versions.
- Identity/membership: authenticated role and active clinic, including multi-clinic users.
- Data migration: create clinics/backfill ownership, validate orphan/cross-tenant links,
  remove production demo-seed overwrite behavior; do not treat create_all as migration.
- Deployment: managed DB, TLS/encryption/secrets, backup/restore, tenant monitoring,
  capacity and incident response.
- Product: onboarding/admin, invitation, support and offboarding workflows.

## Delivery checklist — evidence, not a submission claim

- [x] Local Git Phase 7 baseline and scenario 1–16 tests exist.
- [x] README setup/run/test instructions and detailed scenario mapping exist.
- [x] Phase 8 Markdown brief covers 1–17, failure attempts and changed assumptions.
- [ ] Exported current brief PDF visually checked and verified at 2–3 pages.
- [ ] New-feature video coverage reviewed with a scenario/timestamp list.
- [ ] Recipient-accessible repo/zip and exact submitted revision checked.
- [ ] Final email/attachments reviewed and sent by authorized user.

Existing `Nightingale_Technical_Brief.pdf` is tracked but not inspected or regenerated here.
Existing `Demo Video.mp4` is user-owned and has not been read, overwritten or assessed.
Original submission: reply under “Nightingale 72HR Build — <Your Name>”, repo link/zip,
brief and demo to irakumar@ntngale.com; cc frank.ng@ntu.edu.sg and carrene.teo@ntu.edu.sg.
Original deadline: 3 September 2026, 18:00 SGT; no claim of on-time submission is made.
