import { useEffect, useState } from "react";
import { getPatient, getPatientEntries } from "./api";
import type { Patient, TimelineEntry } from "./types";

const DEMO_PATIENT_ID = "patient-demo-001";

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
              <article className="entry-card">
                <div className="entry-meta">
                  <span className={`role role-${entry.author_role}`}>{entry.author_role}</span>
                  <time dateTime={entry.timestamp}>{new Date(entry.timestamp).toLocaleString()}</time>
                </div>
                <h3>{entry.type.replaceAll("_", " ")}</h3>
                <p>{entry.content}</p>
                {entry.provenance_pointer && <small>Source: {entry.provenance_pointer}</small>}
              </article>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}

