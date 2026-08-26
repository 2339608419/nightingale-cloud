# Nightingale AI Scribe and PHI Redaction Plan

## Goal
Add a synthetic-only AI-scribe ingestion pipeline that redacts PHI before provider invocation and creates provenance-linked AI timeline entries reliably without external services.

## Phases
- [x] Inspect current timeline creation, version initialization, authorization, dependencies, and documentation
- [x] Add deterministic PHI redaction with structured non-sensitive metadata
- [x] Add provider abstraction, deterministic mock, and opt-in external provider
- [x] Add clinic-scoped AI-scribe schemas, service, and endpoint
- [x] Add fake-provider, provenance, entry-type, and log-safety tests
- [x] Document redaction call chain, provider selection, and raw transcript non-persistence
- [x] Run dedicated tests, complete backend suite, frontend build, and final scope review

## Constraints
- Synthetic data only; reject requests not explicitly marked synthetic.
- Redaction must occur before every provider call.
- Never log or persist the raw transcript.
- Provenance is a stable source identifier, never the summary text.
- Offline mock mode must remain the reliable default.
- No voice recording or unrelated features.

## Errors Encountered
| Error | Attempt | Resolution |
|---|---:|---|
| None yet | - | - |
