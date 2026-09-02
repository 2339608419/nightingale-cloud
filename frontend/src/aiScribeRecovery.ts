import type { ApiIdentity, TimelineEntry } from "./types.ts";

export type Interaction = "doctor_consult" | "nurse_consult" | "patient_session";
export type GenerationMode = "rule_derived_mock" | "external_model" | "test_double";
export type ScribeOutcome = "success" | "redaction_withheld" | "provider_timeout"
  | "provider_unavailable" | "invalid_provider_response";
export interface ScribePayload {
  patient_id: string;
  interaction_type: Interaction;
  source_id: string;
  transcript: string;
  synthetic: true;
}
export interface ScribeResult {
  outcome: ScribeOutcome;
  generation_mode: GenerationMode;
  generated_summary: string | null;
  timeline_entry: TimelineEntry | null;
}
export type ScribePhase = "idle" | "waiting" | ScribeOutcome | "unknown" | "request_rejected";
export interface ScribeState {
  draft: string;
  interaction: Interaction;
  phase: ScribePhase;
  mode: GenerationMode | null;
  summary: string | null;
}
export const scribeMessages: Record<ScribePhase, string> = {
  idle: "Synthetic transcript only. Redaction and validation run before the provider.",
  waiting: "Waiting for AI Scribe. Do not submit again. No automatic retries.",
  success: "AI-scribed entry created. Review it in Timeline; this is not patient approval.",
  redaction_withheld: "AI scribe withheld pending redaction review. Edit the synthetic draft before retrying.",
  provider_timeout: "Provider timed out. No entry created. Draft kept; retry only when you choose.",
  provider_unavailable: "Provider unavailable. No entry created. Draft kept; retry only when you choose.",
  invalid_provider_response: "Provider returned an invalid response. No entry created. Draft kept for review.",
  unknown: "Result unknown — refresh and check Timeline first. Do not resend: the server may have created an entry. Copy your draft before a full page refresh; it is memory-only.",
  request_rejected: "Request rejected. Check permissions and synthetic input. Draft kept; no server error text is displayed.",
};
export class ScribeRejected extends Error {}

// Do not trust an HTTP status alone: proxies can return 502/503/504 after a commit.
// Only the backend's complete, consistent abstention contract permits a retry.
export function parseScribeResponse(status: number, body: unknown, patientId: string): ScribeResult {
  const value = body as Record<string, unknown> | null;
  if (!value || typeof value !== "object") throw new Error("Unknown result");
  const mode = value.generation_mode;
  if (!["rule_derived_mock", "external_model", "test_double"].includes(String(mode))) {
    if ([401, 403, 404, 422].includes(status)) throw new ScribeRejected();
    throw new Error("Unknown result");
  }
  const failures: Record<string, number> = {
    redaction_withheld: 200, provider_timeout: 504,
    provider_unavailable: 503, invalid_provider_response: 502,
  };
  const outcome = String(value.outcome);
  if (failures[outcome] === status && value.status === "withheld"
      && value.safe_abstention === true && value.timeline_entry === null
      && value.generated_summary === null && value.provenance_pointer === null) {
    return { outcome: outcome as ScribeOutcome, generation_mode: mode as GenerationMode,
      generated_summary: null, timeline_entry: null };
  }
  const entry = value.timeline_entry as TimelineEntry | null;
  if (status === 201 && outcome === "success" && value.status === "created"
      && value.safe_abstention === false && entry?.patient_id === patientId
      && typeof entry.id === "string" && entry.id.length > 0
      && entry.author_role === "system" && entry.type.startsWith("ai_")
      && typeof value.generated_summary === "string" && value.generated_summary.trim()
      && entry.content === value.generated_summary
      && typeof value.provenance_pointer === "string" && value.provenance_pointer.length > 0) {
    return { outcome: "success", generation_mode: mode as GenerationMode,
      generated_summary: value.generated_summary, timeline_entry: entry };
  }
  throw new Error("Unknown result");
}

export function createScribeController(
  patientId: string,
  identity: ApiIdentity,
  send: (payload: ScribePayload, identity: ApiIdentity) => Promise<ScribeResult>,
  onCreated: (entry: TimelineEntry) => void,
) {
  let state: ScribeState = { draft: "", interaction: "doctor_consult", phase: "idle", mode: null, summary: null };
  let active = true;
  let epoch = 0;
  let sourceId = `scribe-${crypto.randomUUID()}`;
  const listeners = new Set<() => void>();
  const publish = (next: ScribeState) => { state = next; listeners.forEach((listener) => listener()); };
  const canSubmit = () => active && !["waiting", "unknown", "success"].includes(state.phase) && !!state.draft.trim();
  return {
    getSnapshot: () => state,
    subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    // React StrictMode can reattach the same instance; the epoch still invalidates old work.
    activate() { active = true; },
    dispose() {
      active = false; epoch += 1;
      state = { draft: "", interaction: "doctor_consult", phase: "idle", mode: null, summary: null };
      listeners.clear();
    },
    edit(draft: string) { if (active && state.phase !== "waiting") publish({ ...state, draft }); },
    choose(interaction: Interaction) { if (active && state.phase !== "waiting") publish({ ...state, interaction }); },
    canSubmit,
    newDraft() {
      if (!active || state.phase !== "success") return;
      sourceId = `scribe-${crypto.randomUUID()}`;
      publish({ draft: "", interaction: "doctor_consult", phase: "idle", mode: null, summary: null });
    },
    async submit() {
      if (!canSubmit()) return;
      const requestEpoch = ++epoch;
      const payload: ScribePayload = { patient_id: patientId, interaction_type: state.interaction,
        source_id: sourceId, transcript: state.draft, synthetic: true };
      publish({ ...state, phase: "waiting", mode: null, summary: null });
      let result: ScribeResult;
      try { result = await send(payload, identity); }
      catch (error) {
        if (active && requestEpoch === epoch) publish({ ...state,
          phase: error instanceof ScribeRejected ? "request_rejected" : "unknown", mode: null, summary: null });
        return;
      }
      if (!active || requestEpoch !== epoch) return;
      publish({ ...state, phase: result.outcome, mode: result.generation_mode, summary: result.generated_summary });
      if (result.outcome === "success" && result.timeline_entry) onCreated(result.timeline_entry);
    },
  };
}
