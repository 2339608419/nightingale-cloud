# Nightingale Demo Runbook (5–7 minutes)

Use only the seeded patient **Maya Chen (Synthetic)** (`patient-demo-001`). Start the backend and frontend using the README, then open `http://localhost:5173`.

| Time | Role | Action | Expected result | Why it matters |
|---|---|---|---|---|
| 0:00–0:45 | Staff | Open the patient and scan the Glance View. Click **Nurse follow-up unresolved**. | Three to five ranked items and open actions are immediately visible. The page jumps to and briefly emphasizes the exact timeline source. | Demonstrates glanceability, deterministic importance, and verifiable provenance. |
| 0:45–1:30 | Staff | Review the timeline dates and origin badges. | Entries span **15 Apr 2025**, **6 Feb 2026**, and recent 2026 activity. Human roles and AI-generated entries are visually distinct; durable old facts remain full detail while low-value old content has a reversible cold-summary preview. | Demonstrates longitudinal context and safe data decay. |
| 1:30–2:15 | Staff | Add a staff note, then comment `@clinician-demo-001 please review the medication plan.` | The note appears without overwriting another section. The internal comment displays the mention and can be replied to or resolved. | Demonstrates inline collaboration and independently editable sections. |
| 2:15–3:15 | Clinician | Switch identity to **Clinician**. Accept an AI-derived highlight, then inspect the adaptive-learning explanation. | The highlight becomes accepted and future similar suggestions receive the documented deterministic entity/type bonus. Clinical safety floors remain visible in the explanation where applicable. | Demonstrates human-guided learning without giving feedback authority over clinical safety floors. |
| 3:15–4:15 | Clinician | Edit a clinician-owned note, open **Revision History**, and revert to the previous version. | A new immutable version is recorded; the prior content is restored as another version. A stale same-entry update would receive HTTP 409. | Demonstrates auditability, revert, and deterministic conflict handling. |
| 4:15–5:15 | Clinician | Review an open clinical conflict and its two source links; resolve it if desired. | Both entries remain intact. Clinician authority is explicit when hierarchy applies; equal-authority staff conflicts require clinician review. | Demonstrates provenance-preserving contradiction handling rather than silent deletion. |
| 5:15–6:15 | Clinician → Patient | Review an AI-derived patient-facing draft, approve it, then switch to **Patient**. | Draft/rejected content is hidden from the patient. Only the clinician-approved instruction appears, labeled **Clinician approved**. | Demonstrates the hard server-side human approval gate: there is no direct AI → Patient path. |

## Optional API trust proof

Use the automated tests rather than entering real data. The AI-scribe tests prove this boundary:

```text
synthetic transcript → PHI redaction → deterministic validation
  → pass: mock/opt-in provider → system-authored AI note with provenance
  → fail: withheld for review; no provider call and no timeline entry
```

The reliable demo uses the offline deterministic mock. No external LLM or real patient information is required.

## Presenter guardrails

- Keep **Demo identity simulation** visible when changing roles; it is not production authentication.
- Do not enter real patient information.
- If a browser state looks stale after a role change, refresh once; seed data is idempotent.
- Describe the benchmark as an in-process warm-path approximation, not a deployed end-to-end SLA.
