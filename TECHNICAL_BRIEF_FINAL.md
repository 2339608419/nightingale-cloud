# Nightingale Cloud - Shared Longitudinal Care Note

*A communication and trust layer that turns fragmented longitudinal clinical notes into an actionable, provenance-linked shared record.*

## 1. Problem and design principles

Electronic health records are effective at storing structured observations, orders, and encounter documents, but they often fail to express the patient's evolving story. Free-text notes are fragmented by visit, author, and workflow. Important risks compete with old details, unresolved actions are easy to lose, and AI-generated summaries add value only when clinicians can verify their evidence.

Nightingale Cloud is a synthetic-data-only 72-hour prototype centered on one shared Care Note per patient. It combines a longitudinal timeline with a clinician-facing Glance View, inline collaboration, revision history, and AI-scribed entries. Five principles shape the design:

- **Glanceability:** expose the three to five most actionable facts and open actions first.
- **Collaboration:** let staff and clinicians contribute without overwriting each other's sections.
- **Provenance:** make every highlighted claim traceable to an exact timeline entry and source span.
- **Deterministic safety:** use inspectable rules for authority, conflicts, ranking floors, and evidence state.
- **Abstention over unsupported generation:** withhold or require review when privacy or evidence checks fail.

The result is not a production EHR. It is a focused demonstration that AI can assist while clinicians retain verification and final authority.

## 2. Architecture

```text
React + TypeScript + Vite
            |
            v
        FastAPI API
            |
            +-- server-side RBAC and clinic scope
            +-- timeline, comments, tasks, revisions
            +-- highlight and adaptive importance engine
            +-- conflict and evidence confidence
            +-- metadata-only audit service
            +-- AI-scribe safety pipeline
            |
            v
      SQLAlchemy ORM
            |
            v
     SQLite prototype
```

FastAPI routes resolve a development identity, load the patient, enforce reusable authorization policies, and delegate to focused services. SQLAlchemy models and Pydantic API schemas remain separate. The React client is a typed REST consumer; role controls in the interface simulate identities for the demo and are not the security boundary.

The AI path has a separate safety boundary:

```text
Synthetic transcript
  -> PHI redaction
  -> redaction validation
  -> provider abstraction
  -> system-authored AI timeline entry

Validation failure
  -> WITHHELD / review
  -> no provider call
  -> no AI timeline entry
```

The default provider is a deterministic offline mock so the demo is reproducible without credentials or network access. An external provider is opt-in behind the same validated boundary.

## 3. Data model

`Patient` owns the longitudinal record. `TimelineEntry` is the canonical unit for clinician notes, staff notes, patient-facing instructions, AI summaries, and system events. Each entry records author role, timestamp, type, content, and provenance. Immutable `EntryVersion` snapshots support history and revert; update requests carry an expected version so stale same-entry edits fail with HTTP 409 while unrelated entries remain independently editable.

```text
Patient -> TimelineEntry -> EntryVersion
                    |----> Comment -> threaded replies
                    |----> TaskAssignment
                    |----> Highlight
                    |----> ConflictRecord

Highlight -> provenance_pointer
          -> TimelineEntry + exact source span
AI-derived instruction -> source AI entry
                       -> approval metadata
Clinic -> adaptive feedback counters
AuditLog -> metadata-only lifecycle records
```

Highlights never stand alone: `entry_id`, `source_span`, and a stable `timeline-entry-{id}` pointer connect each item to evidence. Conflict records retain both unchanged sources and structured entity/value comparisons. AI-derived patient instructions reuse the timeline instruction type and add draft/approved/rejected metadata rather than creating a parallel patient-content store.

## 4. Glance, prioritization, and trust

The Glance View returns up to five non-rejected highlights. Its ranking remains deterministic and explainable:

```text
base score + learned adjustment = adjusted score
final score = max(adjusted score, clinical safety floor)
```

The base score combines explicit risk, recency, unresolved work, clinical entity type, and clinician confirmation. Clinic-scoped accept/reject counters add a bounded entity and entry-type adjustment. Feedback is a ranking convenience, not evidence: it cannot change provenance, authority, approval state, or Evidence Confidence.

Safety floors apply after learning. Allergy remains at least HIGH/50; an unresolved medication dosage conflict remains at least HIGH/65; a recent or unresolved medication change remains at least MODERATE/35; and unresolved clinically relevant follow-up remains at least MODERATE/50. Repeated negative feedback therefore cannot demote a critical class below its configured floor.

Evidence Confidence is not LLM confidence. It is a deterministic state derived from verifiable evidence:

- **HIGH:** source and span resolve, with a recognized structured fact or clinician confirmation and no open conflict.
- **MEDIUM:** source and span resolve, but deterministic structured confirmation is absent.
- **LOW:** the source exists but structured evidence is inconsistent, so review is required.
- **ABSTAIN / Needs Review:** provenance is broken, the span is invalid, or an unresolved contradiction prevents safe presentation.

This directly answers the Nightingale trust hint. **What is it?** An evidence-based deterministic trust state. **How would we know if it were wrong?** The service verifies provenance, source spans, extracted fact consistency, and open conflicts. **What happens when it is wrong?** The system abstains or requires clinician review instead of displaying unsupported content as trusted.

## 5. AI safety, conflicts, and patient safety

Every AI-scribe provider call occurs after redaction and validation. The redactor covers names, Singapore-style identity numbers, and phone numbers. Validation checks that known PHI patterns and synthetic fixture names are absent, that protected terms such as Penicillin and Lisinopril and medication dosages survive, and that meaningful clinical text remains. Failure returns WITHHELD, calls no provider, logs no raw transcript, and persists no AI timeline entry.

Conflict extraction is deliberately limited to the synthetic demo vocabulary for medication and dosage, allergy status, and follow-up status. It compares clinician with AI/patient evidence, clinician with staff, and staff with staff. The prototype authority hierarchy is clinician, then staff/nurse, then AI/patient-derived evidence. A higher-authority clinician fact takes precedence without deleting the lower-authority source. Equal-authority human contradictions stay open, assert no truth, and require clinician review. Both provenance links remain resolvable.

There is no direct AI-to-patient path. AI-derived instructions begin as Draft and remain invisible to patients until a clinic-scoped clinician explicitly approves them. Rejected instructions stay internal. Editing or reverting approved AI-derived content invalidates approval, returns the instruction to Draft, and requires re-approval while prior versions remain available. Existing manually authored clinician instructions are treated as inherently clinician-approved.

## 6. RBAC, privacy, and audit

Authorization and clinic isolation are enforced server-side. Patients can retrieve only their approved patient-facing instructions and cannot access raw AI notes, internal comments, conflicts, tasks, versions, or audit data. Staff can create and edit staff notes within their clinic but cannot overwrite clinician notes or approve patient instructions. Clinicians can read permitted staff and AI context, edit clinician-owned notes, decide highlights, review conflicts, and approve patient instructions. Admins have clinic-scoped oversight but no implicit approval authority.

The prototype uses synthetic data only. Audit logs store actor, role, action, entity identifiers, timestamps, and minimal status transitions; note, comment, highlight, instruction, and transcript content are excluded. Unauthorized and no-op operations do not create successful-action events. Development identity headers are prototype identity injection, not production authentication. TLS in transit and encryption at rest are deployment controls that a real environment would supply, not claims about this local build.

## 7. Performance and verification

The final warm-path benchmark used 20 warm-ups followed by 200 measured clinician requests to the Glance endpoint.

| Metric | Result |
|---|---:|
| Median | 5.308 ms |
| P95 | 6.540 ms |
| Minimum | 4.616 ms |
| Maximum | 17.024 ms |

Environment: Windows 11, Python 3.12.13, FastAPI TestClient, and in-memory SQLite. This is an in-process backend approximation. It excludes browser rendering, network latency, deployed infrastructure, production data volume, and concurrency, so it is not evidence of a deployed end-to-end P95 at or below 300 ms.

Final verification recorded 18 passing required micro-tests, 89 passing backend tests, a passing frontend TypeScript check, and a successful frontend production build. No external LLM was invoked during verification.

## 8. Trade-offs and next steps

The prototype uses SQLite instead of a production database, SQLAlchemy `create_all` instead of migration infrastructure, and development headers instead of SSO. The deterministic mock provider favors reproducibility. Clinical extraction covers only the synthetic demonstration vocabulary and is not general medical NLP. Raw AI transcript viewing is not implemented; only stable synthetic source identifiers are retained. Data decay is a reversible policy preview rather than physical cold storage, and ambient voice capture is not implemented.

These choices intentionally prioritize a working longitudinal workflow, provenance, clinical authority, deterministic safety, evaluation, and clear demonstration within a 72-hour build window. Production next steps would begin with authenticated identity, managed migrations and storage, broader clinically validated extraction, direct source-review tooling, deployed performance testing, and operational security controls.
