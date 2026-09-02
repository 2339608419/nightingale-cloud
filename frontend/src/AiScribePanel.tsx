import { useLayoutEffect, useState, useSyncExternalStore } from "react";
import { submitAiScribe } from "./api";
import { createScribeController, scribeMessages } from "./aiScribeRecovery";
import type { Interaction } from "./aiScribeRecovery";
import type { ApiIdentity, TimelineEntry } from "./types";

interface Props { patientId: string; identity: ApiIdentity; onCreated: (entry: TimelineEntry) => void }

// A changed patient OR identity creates a fresh controller/draft, even without page reload.
export function AiScribePanel(props: Props) {
  const key = JSON.stringify([props.patientId, props.identity.clinicId, props.identity.userId, props.identity.role]);
  return <ScribeForm key={key} {...props} />;
}

function ScribeForm({ patientId, identity, onCreated }: Props) {
  const [controller] = useState(() => createScribeController(patientId, identity, submitAiScribe, onCreated));
  const state = useSyncExternalStore(controller.subscribe, controller.getSnapshot);
  useLayoutEffect(() => { controller.activate(); return () => controller.dispose(); }, [controller]);
  const waiting = state.phase === "waiting";
  const modeLabel = state.mode === "rule_derived_mock" ? "Rule-derived mock (offline)"
    : state.mode === "external_model" ? "External model" : state.mode === "test_double" ? "Test double"
    : "Server-selected; not yet confirmed (default configuration: offline mock)";
  return <section className="timeline" aria-labelledby="ai-scribe-heading">
    <h2 id="ai-scribe-heading">AI Scribe · Synthetic data only</h2>
    <p>Generation mode: {modeLabel}. This form does not select or enable a provider.</p>
    <form className="note-compose" onSubmit={(event) => { event.preventDefault(); void controller.submit(); }} aria-busy={waiting}>
      <label>Interaction type <select value={state.interaction} disabled={waiting}
        onChange={(event) => controller.choose(event.target.value as Interaction)}>
        <option value="doctor_consult">Doctor consult</option>
        <option value="nurse_consult">Nurse consult</option>
        <option value="patient_session">AI-patient session</option>
      </select></label>
      <label>Synthetic transcript
        <textarea value={state.draft} maxLength={50000} rows={5} disabled={waiting}
          autoComplete="off" spellCheck={false}
          placeholder="Synthetic example: Lisinopril remains 10 mg daily. Follow-up is pending."
          onChange={(event) => controller.edit(event.target.value)} />
      </label>
      <p>Draft stays in memory only. Switching patient/identity or closing this page clears it.</p>
      <p role="status" aria-live="polite">{scribeMessages[state.phase]}</p>
      <button type="submit" disabled={!controller.canSubmit()}>
        {waiting ? "Waiting…" : state.phase === "idle" ? "Generate synthetic note" : "Retry manually"}
      </button>
      {state.phase === "success" && <button type="button" onClick={() => controller.newDraft()}>Start new draft</button>}
      {state.phase === "unknown" && <a href="#timeline-heading">Check Timeline before another request</a>}
    </form>
    {state.phase === "success" && state.summary && <div>
      <strong>Created summary · {modeLabel}</strong><p>{state.summary}</p>
    </div>}
  </section>;
}
