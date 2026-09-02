import { useState } from "react";
import {
  addSyntheticSegment, confirmConsultCapture, finalizeSyntheticConsult,
  getConsultCaptures, getConsultSignals, startSyntheticConsult,
} from "./api";
import type { ApiIdentity, ClinicalCapture, ConsultSession, ConsultSummary, SafetySignal } from "./types";

export function SyntheticConsultLab({ patientId, identity }: {
  patientId: string;
  identity: ApiIdentity;
}) {
  const [session, setSession] = useState<ConsultSession | null>(null);
  const [signals, setSignals] = useState<SafetySignal[]>([]);
  const [captures, setCaptures] = useState<ClinicalCapture[]>([]);
  const [summaries, setSummaries] = useState<ConsultSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadFixture = async () => {
    setBusy(true); setError(null);
    try {
      const created = await startSyntheticConsult(patientId, identity);
      const firstText = "I have a Penicillin allergy, saya sakit, wa bo ho.";
      await addSyntheticSegment(created.id, {
        sequence_number: 1, start_offset_ms: 120000, end_offset_ms: 125000,
        speaker: "patient", original_synthetic_text: firstText, state: "final",
        language_spans: [
          { start: 0, end: 28, language: "english" },
          { start: 29, end: 39, language: "malay" },
          { start: 40, end: firstText.length, language: "hokkien" },
        ], alternatives: [],
      }, identity);
      const doseText = "Montelukast — was it 20 mg or 50 mg?";
      await addSyntheticSegment(created.id, {
        sequence_number: 2, start_offset_ms: 180000, end_offset_ms: 184000,
        speaker: "clinician", original_synthetic_text: doseText, state: "final",
        language_spans: [{ start: 0, end: doseText.length, language: "english" }],
        capture_uncertainty: "two dosage candidates", alternatives: ["20 mg", "50 mg"],
      }, identity);
      setSession({ ...created, state: "receiving" });
      setSignals(await getConsultSignals(created.id, identity));
      setCaptures(await getConsultCaptures(created.id, identity));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create synthetic fixture");
    } finally { setBusy(false); }
  };

  const confirm = async (capture: ClinicalCapture, value: string) => {
    if (!session) return;
    const updated = await confirmConsultCapture(session.id, capture.id, value, identity);
    setCaptures((items) => items.map((item) => item.id === updated.id ? updated : item));
  };

  const finalize = async () => {
    if (!session) return;
    setBusy(true);
    try {
      setSummaries(await finalizeSyntheticConsult(session.id, identity));
      setSession({ ...session, state: "completed" });
    } finally { setBusy(false); }
  };

  return <section className="panel consult-lab" aria-labelledby="consult-lab-heading">
    <div className="section-heading">
      <div><p className="eyebrow">Trust boundary demonstration</p><h2 id="consult-lab-heading">Synthetic Consult Lab</h2></div>
      <span>Post-ASR synthetic text stream — not real audio</span>
    </div>
    {!session && <button type="button" disabled={busy} onClick={() => void loadFixture()}>{busy ? "Loading…" : "Load multilingual fixture"}</button>}
    {error && <p className="error">{error}</p>}
    {session && <>
      <p><strong>State:</strong> {session.state} · simulated clinic-noise label only · provider not invoked</p>
      <div className="consult-grid">
        <article><strong>Minute 2 safety signal</strong>{signals.map((item) => <p key={item.id}><span className="risk-high">HIGH</span> Allergy · {item.status}<br/><small>{item.provenance_pointer} · {item.source_offset_ms / 60000} min</small></p>)}</article>
        <article><strong>Medical-term confirmation</strong>{captures.map((item) => <div key={item.id}><p>{item.captured_term}: {item.candidate_values.join(" or ")} · {item.state}</p><small>{item.reference_scope}<br/>{item.provenance_pointer}</small>{item.state === "needs_confirmation" && <div>{item.candidate_values.map((value) => <button type="button" key={value} onClick={() => void confirm(item, value)}>Confirm {value}</button>)}</div>}</div>)}</article>
      </div>
      {session.state !== "completed" && <button type="button" disabled={busy} onClick={() => void finalize()}>Finalize rule-derived summaries</button>}
      {summaries.length > 0 && <><div className="summary-grid">{summaries.map((item) => <article key={item.id}><strong>{item.audience} summary</strong><span>{item.generation_mode} · source {item.source_status}</span><p>{item.timeline_entry.content}</p>{item.audience === "patient" && <small>Draft · clinician approval required before patient visibility</small>}</article>)}</div><p><small>Use the existing page refresh or role switch when you want the new Timeline entries to reload.</small></p></>}
    </>}
  </section>;
}
