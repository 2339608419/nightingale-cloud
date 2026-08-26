# Findings

- Repository was empty except for `.git`; there are no commits or existing user changes.
- Bundled runtimes are available under `C:\Users\zclin\.cache\codex-runtimes\codex-primary-runtime\dependencies`.
- Architecture: FastAPI route/schema/service/model/database layers and a React/Vite page with a small typed REST client.
- Backend tests use dependency override with SQLite `StaticPool`; they do not execute the production startup lifespan.
- Frontend type checking runs with `--noEmit`, preventing config artifacts from being written into source directories.
- Existing timeline ordering is already enforced server-side with `timestamp DESC`.
- Timeline role/type fields are currently unconstrained strings, and the old `patient_insight` seed type is outside the requested type vocabulary.
- The current seed exits when the demo patient exists; Phase 2 needs fixed-ID upserts so existing runtime databases receive updated synthetic entries.
- Fixed-ID `Session.merge` upserts allow the ignored Phase 1 SQLite runtime database to receive the expanded timeline on next application startup without manual deletion.
- Phase 2 left a stable frontend anchor in the form `timeline-entry-{entry_id}`, suitable as the Highlight provenance target.
- The existing startup uses SQLAlchemy metadata creation, so importing a Highlight model is sufficient to add its SQLite table without redesigning persistence.
- Highlight provenance pointers use the exact stable DOM target ID while `source_span` is separately verified against the originating timeline content.
- Demo importance scores use an explicit 2026-08-26 reference time so seed output is reproducible; the scoring function accepts a current or supplied reference time.
