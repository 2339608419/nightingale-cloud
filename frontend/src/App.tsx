import { useEffect, useState } from "react";
import { getPatient, getPatientEntries } from "./api";
import type { Patient, TimelineEntry } from "./types";

const DEMO_PATIENT_ID = "patient-demo-001";

const isAiGenerated = (entry: TimelineEntry) => entry.type.startsWith("ai_");

const formatLabel = (value: string) =>
  value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

export default function App() {
  const [patient, setPatient] = useState<Patient | null>(null);
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getPatient(DEMO_PATIENT_ID), getPatientEntries(DEMO_PATIENT_ID)])
      .then(([patientData, entryData]) => {
        setPatient(patientData);
        setEntries(entryData);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Unable to load patient");
      });
  }, []);

  if (error) {
    return <main className="page"><div className="error">{error}</div></main>;
  }

  if (!patient) {
    return <main className="page"><p>Loading patient…</p></main>;
  }

  return (
    <main className="page">
      <header className="patient-header">
        <div>
          <p className="eyebrow">Longitudinal care note</p>
          <h1>{patient.name}</h1>
        </div>
        <dl>
          <div><dt>Date of birth</dt><dd>{patient.date_of_birth}</dd></div>
          <div><dt>Clinic</dt><dd>{patient.clinic_id}</dd></div>
        </dl>
      </header>

      <section className="panel glance" aria-labelledby="glance-heading">
        <div>
          <p className="eyebrow">At a glance</p>
          <h2 id="glance-heading">Glance View</h2>
        </div>
        <p className="placeholder">Critical risks, current priorities, and unresolved actions will appear here in a later build step.</p>
      </section>

      <section className="timeline" aria-labelledby="timeline-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Patient history</p><h2 id="timeline-heading">Timeline</h2></div>
          <span>{entries.length} entries</span>
        </div>
        <ol>
          {entries.map((entry) => (
            <li key={entry.id}>
              <article
                className={`entry-card${isAiGenerated(entry) ? " entry-card-ai" : ""}`}
                id={`timeline-entry-${entry.id}`}
              >
                <div className="entry-meta">
                  <div className="entry-badges">
                    <span className={`role role-${entry.author_role}`}>{formatLabel(entry.author_role)}</span>
                    {isAiGenerated(entry) && <span className="ai-badge">AI-generated</span>}
                  </div>
                  <time dateTime={entry.timestamp}>
                    {new Date(entry.timestamp).toLocaleString(undefined, {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </time>
                </div>
                <p className="entry-type">{formatLabel(entry.type)}</p>
                <p>{entry.content}</p>
                {entry.provenance_pointer && (
                  <div className="source"><span>Source</span><code>{entry.provenance_pointer}</code></div>
                )}
              </article>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
