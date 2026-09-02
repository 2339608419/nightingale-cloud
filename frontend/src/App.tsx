import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  acceptHighlight,
  approvePatientInstruction,
  completeAssignment,
  createComment,
  createMockDelivery,
  createNote,
  getCompletedAssignments,
  getOpenConflicts,
  getDataDecayPreview,
  getEntryComments,
  getEntryVersions,
  getOpenAssignments,
  getPatient,
  getPatientEntries,
  getPatientHighlights,
  getHighlightSource,
  getPatientDeliveries,
  getImportancePreferences,
  getHighlightReviewQueue,
  getHighlightTrustMetrics,
  recordHighlightExposure,
  setCommentResolution,
  setMockDeliveryStatus,
  revertEntry,
  rejectHighlight,
  rejectPatientInstruction,
  resolveConflict,
  updateNote,
  undoHighlightFeedback,
  ApiError,
} from "./api";
import type {
  ApiIdentity,
  Comment,
  ConflictRecord,
  DataDecayPreview,
  DemoRole,
  EntryVersion,
  Highlight,
  HighlightSourceSnapshot,
  EntryVersionConflictDetail,
  ImportancePreference,
  Patient,
  PatientDelivery,
  TaskAssignment,
  TimelineEntry,
  TrustMetrics,
} from "./types";
import {
  cancelConflictAndKeepDraft,
  preserveDraftOnConflict,
  reloadCurrentServerVersion,
} from "./conflictRecovery";
import { SyntheticConsultLab } from "./SyntheticConsultLab";
import { AiScribePanel } from "./AiScribePanel";
import { createClinicalRefresh, clinicalSyncMessage } from "./clinicalRefresh";
import type { ClinicalSync } from "./clinicalRefresh";

const DEMO_PATIENT_ID = "patient-demo-001";
const DEMO_IDENTITIES: Record<DemoRole, ApiIdentity> = {
  patient: { userId: DEMO_PATIENT_ID, role: "patient", clinicId: "clinic-demo-001" },
  staff: { userId: "staff-demo-001", role: "staff", clinicId: "clinic-demo-001" },
  clinician: {
    userId: "clinician-demo-001",
    role: "clinician",
    clinicId: "clinic-demo-001",
  },
  admin: { userId: "admin-demo-001", role: "admin", clinicId: "clinic-demo-001" },
};

const isAiGenerated = (entry: TimelineEntry) =>
  entry.ai_derived || entry.type.startsWith("ai_") || entry.author_id.startsWith("ai-scribe:");

const canRevertEntry = (role: DemoRole, entry: TimelineEntry) =>
  (role === "staff" && entry.author_role === "staff" && entry.type === "staff_note") ||
  (role === "clinician" && entry.author_role === "clinician" &&
    ["clinician_note", "instruction"].includes(entry.type));

const formatLabel = (value: string | null | undefined) =>
  (value ?? "unknown").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

export default function App() {
  const [demoRole, setDemoRole] = useState<DemoRole>("clinician");
  const [patient, setPatient] = useState<Patient | null>(null);
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [commentsByEntry, setCommentsByEntry] = useState<Record<string, Comment[]>>({});
  const [versionsByEntry, setVersionsByEntry] = useState<Record<string, EntryVersion[]>>({});
  const [assignments, setAssignments] = useState<TaskAssignment[]>([]);
  const [completedAssignments, setCompletedAssignments] = useState<TaskAssignment[]>([]);
  const [decayByEntry, setDecayByEntry] = useState<Record<string, DataDecayPreview>>({});
  const [preferences, setPreferences] = useState<ImportancePreference[]>([]);
  const [conflicts, setConflicts] = useState<ConflictRecord[]>([]);
  const [deliveries, setDeliveries] = useState<PatientDelivery[]>([]);
  const [highlightSources, setHighlightSources] = useState<Record<string, HighlightSourceSnapshot | null>>({});
  const [highlightSourceErrors, setHighlightSourceErrors] = useState<Record<string, string>>({});
  const [reviewQueue, setReviewQueue] = useState<Highlight[]>([]);
  const [trustMetrics, setTrustMetrics] = useState<TrustMetrics | null>(null);
  const displayReference = useRef(`display_${crypto.randomUUID().replaceAll("-", "")}`);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [clinicalSync, setClinicalSync] = useState<ClinicalSync>("current");
  const [initialLoadComplete, setInitialLoadComplete] = useState(false);
  const clinicalPatientId = patient?.id ?? DEMO_PATIENT_ID;
  const clinicalRefresh = useMemo(() => {
    const identity = DEMO_IDENTITIES[demoRole];
    return createClinicalRefresh(
      () => Promise.all([
        getPatientHighlights(clinicalPatientId, identity),
        demoRole === "clinician" || demoRole === "admin"
          ? getOpenConflicts(clinicalPatientId, identity) : Promise.resolve([]),
        demoRole === "clinician" ? getHighlightReviewQueue(clinicalPatientId, identity) : Promise.resolve([]),
        demoRole === "clinician" ? getHighlightTrustMetrics(clinicalPatientId, identity) : Promise.resolve(null),
      ]),
      ([freshHighlights, freshConflicts, freshQueue, freshMetrics]) => {
        setHighlights(freshHighlights); setConflicts(freshConflicts);
        setReviewQueue(freshQueue); setTrustMetrics(freshMetrics);
        setHighlightSources({}); setHighlightSourceErrors({});
      },
      setClinicalSync,
    );
  }, [clinicalPatientId, demoRole, reloadToken]);
  useLayoutEffect(() => {
    clinicalRefresh.activate(); setClinicalSync("current");
    return () => clinicalRefresh.dispose();
  }, [clinicalRefresh]);

  useEffect(() => {
    const identity = DEMO_IDENTITIES[demoRole];
    let cancelled = false;
    setPatient(null);
    setInitialLoadComplete(false);
    setError(null);
    setCommentsByEntry({});
    setVersionsByEntry({});
    setAssignments([]);
    setCompletedAssignments([]);
    setPreferences([]);
    setConflicts([]);
    setDeliveries([]);
    setHighlightSources({});
    setHighlightSourceErrors({});
    setReviewQueue([]);
    setTrustMetrics(null);

    const load = async () => {
      try {
        const [patientData, entryData, highlightData, decayData, deliveryData] = await Promise.all([
          getPatient(DEMO_PATIENT_ID, identity),
          getPatientEntries(DEMO_PATIENT_ID, identity),
          getPatientHighlights(DEMO_PATIENT_ID, identity),
          getDataDecayPreview(DEMO_PATIENT_ID, identity),
          getPatientDeliveries(DEMO_PATIENT_ID, identity),
        ]);
        if (cancelled) return;
        // Render the patient and Glance View as soon as their core requests finish.
        // Collaboration/history data is intentionally loaded afterward so an N-entry
        // request fan-out cannot delay the clinically important top card.
        setPatient(patientData);
        setEntries(entryData);
        setHighlights(highlightData);
        setDecayByEntry(Object.fromEntries(decayData.map((item) => [item.entry_id, item])));
        setDeliveries(deliveryData);
        let commentData: Record<string, Comment[]> = {};
        let assignmentData: TaskAssignment[] = [];
        let completedAssignmentData: TaskAssignment[] = [];
        let preferenceData: ImportancePreference[] = [];
        let conflictData: ConflictRecord[] = [];
        if (demoRole !== "patient") {
          const [openAssignments, completed, learnedPreferences, openConflicts, entryComments, entryVersions] = await Promise.all([
            getOpenAssignments(DEMO_PATIENT_ID, identity),
            getCompletedAssignments(DEMO_PATIENT_ID, identity),
            getImportancePreferences(identity),
            demoRole === "clinician" || demoRole === "admin"
              ? getOpenConflicts(DEMO_PATIENT_ID, identity)
              : Promise.resolve([]),
            Promise.all(
              entryData.map(async (entry) => [
                entry.id,
                await getEntryComments(entry.id, identity),
              ] as const),
            ),
            Promise.all(
              entryData.map(async (entry) => [
                entry.id,
                await getEntryVersions(entry.id, identity),
              ] as const),
            ),
          ]);
          assignmentData = openAssignments;
          completedAssignmentData = completed;
          preferenceData = learnedPreferences;
          conflictData = openConflicts;
          commentData = Object.fromEntries(entryComments);
          if (!cancelled) setVersionsByEntry(Object.fromEntries(entryVersions));
          if (demoRole === "clinician") {
            const [queue, metrics] = await Promise.all([
              getHighlightReviewQueue(DEMO_PATIENT_ID, identity),
              getHighlightTrustMetrics(DEMO_PATIENT_ID, identity),
            ]);
            if (!cancelled) {
              setReviewQueue(queue);
              setTrustMetrics(metrics);
            }
          }
        }
        if (cancelled) return;
        setCommentsByEntry(commentData);
        setAssignments(assignmentData);
        setCompletedAssignments(completedAssignmentData);
        setPreferences(preferenceData);
        setConflicts(conflictData);
        setInitialLoadComplete(true);
      } catch (reason: unknown) {
        if (cancelled) return;
        setError(reason instanceof Error ? reason.message : "Unable to load patient");
      }
    };
    void load();
    return () => { cancelled = true; };
  }, [demoRole, reloadToken]);

  useEffect(() => {
    if (demoRole !== "clinician" || highlights.length === 0) return;
    // This effect runs after the Glance list has rendered; GET alone is not an impression.
    void Promise.all(highlights.map((highlight) =>
      recordHighlightExposure(
        highlight.id, displayReference.current, DEMO_IDENTITIES.clinician,
      )
    )).catch(() => undefined);
  }, [demoRole, highlights]);

  if (error) {
    return <main className="page"><DemoIdentity role={demoRole} onChange={setDemoRole} /><div className="error">{error}</div></main>;
  }

  if (!patient) {
    return <main className="page"><DemoIdentity role={demoRole} onChange={setDemoRole} /><p>Loading patient…</p></main>;
  }

  const navigateToSource = (provenancePointer: string) => {
    const source = document.getElementById(provenancePointer);
    if (!source) return;
    window.history.replaceState(null, "", `#${provenancePointer}`);
    source.scrollIntoView({ behavior: "smooth", block: "center" });
    source.classList.remove("source-focus");
    requestAnimationFrame(() => source.classList.add("source-focus"));
    window.setTimeout(() => source.classList.remove("source-focus"), 2200);
  };

  const openHighlightSource = async (highlight: Highlight) => {
    if (highlight.provenance_status === "broken") {
      setHighlightSourceErrors((current) => ({
        ...current,
        [highlight.id]: "Needs review · Immutable cited evidence cannot be resolved.",
      }));
      return;
    }
    try {
      const snapshot = await getHighlightSource(highlight.id, DEMO_IDENTITIES[demoRole]);
      setHighlightSources((current) => ({ ...current, [highlight.id]: snapshot }));
      setHighlightSourceErrors((current) => ({ ...current, [highlight.id]: "" }));
      navigateToSource(`timeline-entry-${highlight.entry_id}`);
    } catch (reason: unknown) {
      setHighlightSourceErrors((current) => ({
        ...current,
        [highlight.id]: reason instanceof Error ? reason.message : "Unable to resolve cited source",
      }));
    }
  };

  const closeConflict = async (conflict: ConflictRecord) => {
    await resolveConflict(conflict.id, DEMO_IDENTITIES[demoRole]);
    setConflicts((current) => current.filter((item) => item.id !== conflict.id));
  };

  const addComment = async (entryId: string, content: string, parentId: string | null) => {
    const comment = await createComment(
      entryId,
      content,
      parentId,
      DEMO_IDENTITIES[demoRole],
    );
    setCommentsByEntry((current) => ({
      ...current,
      [entryId]: [...(current[entryId] ?? []), comment],
    }));
  };

  const toggleComment = async (comment: Comment) => {
    const updated = await setCommentResolution(
      comment.id,
      !comment.resolved,
      DEMO_IDENTITIES[demoRole],
    );
    setCommentsByEntry((current) => ({
      ...current,
      [comment.entry_id]: (current[comment.entry_id] ?? []).map((item) =>
        item.id === updated.id ? updated : item,
      ),
    }));
  };

  const finishAssignment = async (assignment: TaskAssignment) => {
    const completed = await completeAssignment(assignment.id, DEMO_IDENTITIES[demoRole]);
    setAssignments((current) => current.filter((item) => item.id !== assignment.id));
    setCompletedAssignments((current) => [completed, ...current]);
  };

  const decideHighlight = async (highlight: Highlight, decision: "accept" | "reject") => {
    try {
      const updated = decision === "accept"
        ? await acceptHighlight(highlight.id, DEMO_IDENTITIES[demoRole])
        : await rejectHighlight(highlight.id, DEMO_IDENTITIES[demoRole]);
      setHighlights((current) => current.map((item) => item.id === updated.id ? updated : item));
      setPreferences(await getImportancePreferences(DEMO_IDENTITIES[demoRole]));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to update highlight");
    }
  };

  const undoFeedback = async (highlight: Highlight) => {
    try {
      const updated = await undoHighlightFeedback(highlight.id, DEMO_IDENTITIES[demoRole]);
      setHighlights((current) => current.map((item) => item.id === updated.id ? updated : item));
      setReviewQueue((current) => current.map((item) => item.id === updated.id ? updated : item));
      setReloadToken((value) => value + 1);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to undo feedback");
    }
  };

  const addDemoNote = async (content: string) => {
    const type = demoRole === "staff" ? "staff_note" : "clinician_note";
    await createNote(DEMO_PATIENT_ID, type, content, DEMO_IDENTITIES[demoRole]);
    setReloadToken((value) => value + 1);
  };

  const editDemoNote = async (entry: TimelineEntry, content: string) => {
    await updateNote(entry, content, DEMO_IDENTITIES[demoRole]);
    setReloadToken((value) => value + 1);
  };

  const decidePatientInstruction = async (
    entry: TimelineEntry,
    decision: "approve" | "reject",
  ) => {
    const identity = DEMO_IDENTITIES[demoRole];
    if (decision === "approve") {
      await approvePatientInstruction(entry.id, identity);
    } else {
      await rejectPatientInstruction(entry.id, identity);
    }
    setReloadToken((value) => value + 1);
  };

  const revertVersion = async (entry: TimelineEntry, versionNumber: number) => {
    try {
      await revertEntry(entry.id, versionNumber, entry.version, DEMO_IDENTITIES[demoRole]);
      setReloadToken((value) => value + 1);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to revert entry");
    }
  };

  const createDelivery = async (
    entryId: string,
    purpose: "instruction" | "appointment_link" | "correction",
    replacesDeliveryId: string | null = null,
  ) => {
    try {
      await createMockDelivery(
        entryId,
        DEMO_IDENTITIES[demoRole],
        purpose,
        replacesDeliveryId,
      );
      setReloadToken((value) => value + 1);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to create mock delivery");
    }
  };

  const advanceDelivery = async (delivery: PatientDelivery) => {
    const next = delivery.status === "created"
      ? "queued"
      : delivery.status === "queued"
        ? "simulated_sent"
        : delivery.status === "simulated_sent"
          ? "simulated_delivered"
          : null;
    if (!next) return;
    await setMockDeliveryStatus(delivery.id, next, DEMO_IDENTITIES[demoRole]);
    setReloadToken((value) => value + 1);
  };

  return (
    <main className="page">
      <DemoIdentity role={demoRole} onChange={setDemoRole} />
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
        <div className="glance-heading">
          <p className="eyebrow">At a glance</p>
          <h2 id="glance-heading">Glance View</h2>
          <p>{clinicalSync === "current" ? "Highest-priority current items" : "Clinical safety views not updated"}</p>
          {clinicalSync !== "current" && <div role="alert">
            <p>{clinicalSyncMessage[clinicalSync]}</p>
            {clinicalSync === "stale" && <button type="button" onClick={() => void clinicalRefresh.refresh()}>Refresh clinical views only</button>}
          </div>}
        </div>
        <div className="glance-content">
          {clinicalSync === "current" && demoRole === "clinician" && conflicts.some((item) => item.entity_type === "allergy") && (
            <div className="glance-conflict-warning" role="alert">
              <strong>High-risk allergy contradiction · Needs clinician review</strong>
              <span>Both sources are retained. Staff-over-AI is a prototype authority policy, not an automatic medical truth.</span>
              <div className="conflict-actions">
                {conflicts.filter((item) => item.entity_type === "allergy").slice(0, 1).map((item) => (
                  <span key={item.id}>
                    <button type="button" onClick={() => navigateToSource(item.authoritative_provenance_pointer)}>Staff source · v{item.authoritative_version_number}</button>
                    <button type="button" onClick={() => navigateToSource(item.conflicting_provenance_pointer)}>AI/patient source · v{item.conflicting_version_number}</button>
                  </span>
                ))}
              </div>
            </div>
          )}
          {clinicalSync === "current" && <ol className="highlight-list">
            {highlights.map((highlight) => (
              <li key={highlight.id} className={`highlight-item${highlight.abstained ? " highlight-needs-review" : ""}`}>
                <button className="highlight-source" type="button" onClick={() => void openHighlightSource(highlight)}>
                  <span className="highlight-topline">
                    <strong>{highlight.text}</strong>
                    <span className={`risk risk-${highlight.risk_level}`}>{formatLabel(highlight.risk_level)}</span>
                  </span>
                  <span className="risk-reason">{highlight.risk_reason}</span>
                  <span className={`evidence-confidence confidence-${highlight.evidence_confidence_level}`}>
                    <strong>{highlight.abstained ? "Needs review" : `Evidence: ${formatLabel(highlight.evidence_confidence_level)}`}</strong>
                    <small>{highlight.confidence_reason}</small>
                    <small>Rule: {formatLabel(highlight.confidence_rule_triggered)} · Action: {formatLabel(highlight.confidence_required_action)}</small>
                  </span>
                  <span className="highlight-state">
                    {highlight.unresolved_action && <span className="state-open">Action unresolved</span>}
                    {highlight.clinician_confirmed && <span className="state-confirmed">Clinician confirmed</span>}
                    <span className={`highlight-status status-${highlight.status}`}>{formatLabel(highlight.status)}</span>
                    <span className={`source-currency currency-${highlight.provenance_status}`}>
                      {highlight.provenance_status === "current" && `Cites version ${highlight.source_version_number}`}
                      {highlight.provenance_status === "stale" && `Cites version ${highlight.source_version_number} · Source has changed`}
                      {highlight.provenance_status === "broken" && "Needs review · Broken provenance"}
                    </span>
                    <span className="provenance">Open immutable cited source ↓</span>
                  </span>
                </button>
                {highlightSourceErrors[highlight.id] && (
                  <div className="source-snapshot source-broken"><strong>Needs review</strong><p>{highlightSourceErrors[highlight.id]}</p></div>
                )}
                {highlightSources[highlight.id] && (
                  <div className={`source-snapshot source-${highlightSources[highlight.id]!.provenance_status}`}>
                    <strong>Viewing immutable cited snapshot · Version {highlightSources[highlight.id]!.source_version_number}</strong>
                    {highlightSources[highlight.id]!.source_changed && <p>Source has changed since this highlight. Review current entry separately.</p>}
                    <blockquote>{highlightSources[highlight.id]!.content}</blockquote>
                  </div>
                )}
                {demoRole === "clinician" && highlight.status === "suggested" && (
                  <div className="highlight-decisions" aria-label={`Review ${highlight.text}`}>
                    <button type="button" onClick={() => void decideHighlight(highlight, "accept")}>Accept</button>
                    <button type="button" onClick={() => void decideHighlight(highlight, "reject")}>Reject</button>
                  </div>
                )}
                {demoRole === "clinician" && highlight.status !== "suggested" && (
                  <div className="highlight-decisions">
                    <button type="button" onClick={() => void undoFeedback(highlight)}>Undo feedback</button>
                  </div>
                )}
              </li>
            ))}
          </ol>}
          {demoRole !== "patient" && (
            <section className="open-actions" aria-labelledby="open-actions-heading">
              <div className="open-actions-heading">
                <h3 id="open-actions-heading">Open actions</h3>
                <span>{assignments.length}</span>
              </div>
              {assignments.length === 0 ? <p>All current actions completed.</p> : (
                <ul>
                  {assignments.map((assignment) => (
                    <li key={assignment.id}>
                      <div><strong>{assignment.title}</strong><span>{formatLabel(assignment.assigned_role)}{assignment.assigned_user_id ? ` · ${assignment.assigned_user_id}` : ""}</span></div>
                      <button type="button" onClick={() => void finishAssignment(assignment)}>Complete</button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
          {demoRole !== "patient" && preferences.length > 0 && (
            <section className="learning-summary" aria-label="Adaptive importance learning">
              <strong>Adaptive learning</strong>
              <span>{preferences.filter((item) => item.weight !== 0).length} active preference signals</span>
              <ul>
                {preferences.filter((item) => item.weight !== 0).slice(0, 3).map((item) => (
                  <li key={`${item.category_type}-${item.category_value}`}>
                    {formatLabel(item.category_value)} future priority <b>{item.weight > 0 ? "+" : ""}{item.weight}</b>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {clinicalSync === "current" && demoRole === "clinician" && trustMetrics && (
            <section className="learning-summary" aria-label="Exposure bias diagnostics">
              <strong>Exposure review · not accuracy</strong>
              <span>{trustMetrics.exposed_count} exposed · {trustMetrics.unexposed_count} not yet surfaced</span>
              <span>{trustMetrics.negative_feedback_suppressed_count} negative categories suppressed · {trustMetrics.negative_feedback_applied_count} applied</span>
            </section>
          )}
          {clinicalSync === "current" && demoRole === "clinician" && reviewQueue.length > 0 && (
            <section className="review-queue" aria-label="Not yet surfaced review candidates">
              <strong>Review candidates · outside Top Glance</strong>
              <ul>{reviewQueue.slice(0, 5).map((item) => (
                <li key={item.id}>
                  <span>{item.text} · {item.status === "rejected" ? "Feedback recorded" : "Not previously surfaced"}</span>
                  {item.status === "rejected" && <button type="button" onClick={() => void undoFeedback(item)}>Undo feedback</button>}
                </li>
              ))}</ul>
            </section>
          )}
          {demoRole !== "patient" && completedAssignments.length > 0 && (
            <section className="completed-actions" aria-label="Recently completed actions">
              <strong>Recently completed</strong>
              <span>✓ {completedAssignments[0].title}</span>
            </section>
          )}
        </div>
      </section>

      {clinicalSync !== "current" && <section className="panel" aria-label="Clinical conflicts not updated" role="alert">
        <h2>Clinical conflicts · Not updated</h2><p>{clinicalSyncMessage[clinicalSync]}</p>
      </section>}
      {clinicalSync === "current" && (demoRole === "clinician" || demoRole === "admin") && conflicts.length > 0 && (
        <section className="conflict-panel" aria-labelledby="conflict-heading">
          <div className="conflict-heading">
            <div><p className="eyebrow">Internal review</p><h2 id="conflict-heading">Clinical conflicts</h2></div>
            <span>{conflicts.length} open</span>
          </div>
          <p>Both sources remain available. Prototype authority policy follows clinician → staff → AI/patient; every unresolved contradiction still requires clinician review and is not an automatic medical truth.</p>
          <ul>
            {conflicts.map((conflict) => (
              <li key={conflict.id}>
                <div className="conflict-values">
                  <span><b>{conflict.requires_clinician_review ? "Source B" : `Conflicting ${formatLabel(conflict.conflicting_role)} value`}</b>{formatLabel(conflict.entity_name)}: {conflict.prior_value}</span>
                  <span className={conflict.requires_clinician_review ? "review-required-value" : "authoritative-value"}><b>{conflict.requires_clinician_review ? "Source A · No authoritative truth" : `Authoritative ${formatLabel(conflict.authoritative_role)} value`}</b>{formatLabel(conflict.entity_name)}: {conflict.authoritative_value}</span>
                </div>
                <div className="conflict-actions">
                  <button type="button" onClick={() => navigateToSource(conflict.conflicting_provenance_pointer)}>{conflict.requires_clinician_review ? "Source B" : "Conflicting source"}</button>
                  <button type="button" onClick={() => navigateToSource(conflict.authoritative_provenance_pointer)}>{conflict.requires_clinician_review ? "Source A" : "Authoritative source"}</button>
                  {demoRole === "clinician" && <button type="button" onClick={() => void closeConflict(conflict)}>Mark resolved</button>}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="delivery-panel" aria-labelledby="delivery-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Synthetic local mock</p>
            <h2 id="delivery-heading">Phone access & delivery trace</h2>
          </div>
          <span>Not real SMS or WhatsApp</span>
        </div>
        <p className="delivery-boundary">
          Phone-first access uses a one-time token and masked destination. Created, queued,
          simulated sent, and simulated delivered are separate states; sent copies cannot be recalled.
        </p>
        {(demoRole === "staff" || demoRole === "clinician") && (
          <button className="delivery-create" type="button" onClick={() => void createDelivery("entry-demo-006", "appointment_link")}>Create mock appointment-link delivery</button>
        )}
        <ul className="delivery-list">
          {deliveries.map((delivery) => {
            const entry = entries.find((item) => item.id === delivery.entry_id);
            const canReplace = delivery.status === "correction_required" && entry?.patient_facing_status === "approved";
            return (
              <li key={delivery.id}>
                <div>
                  <strong>{formatLabel(delivery.purpose)}</strong>
                  <span>{formatLabel(delivery.channel)} · {delivery.masked_destination} · approved v{delivery.approved_version_number}</span>
                  {delivery.replaces_delivery_id && <span>Replacement for {delivery.replaces_delivery_id}</span>}
                  {delivery.status === "correction_required" && <b>Old copy already sent · correction required</b>}
                  {delivery.status === "correction_required" && entry?.patient_facing_status !== "approved" && <span>Corrected copy pending clinician approval</span>}
                </div>
                <span className={`delivery-status delivery-${delivery.status}`}>{formatLabel(delivery.status)}</span>
                {(demoRole === "staff" || demoRole === "clinician") && ["created", "queued", "simulated_sent"].includes(delivery.status) && (
                  <button type="button" onClick={() => void advanceDelivery(delivery)}>Advance mock state</button>
                )}
                {(demoRole === "staff" || demoRole === "clinician") && canReplace && (
                  <button type="button" onClick={() => void createDelivery(delivery.entry_id, "correction", delivery.id)}>Create correction</button>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      {initialLoadComplete && demoRole !== "patient" && <AiScribePanel
        patientId={patient.id}
        identity={DEMO_IDENTITIES[demoRole]}
        onCreated={(entry) => {
          setEntries((current) => [entry, ...current.filter((item) => item.id !== entry.id)]);
          void clinicalRefresh.refresh();
        }}
      />}

      {demoRole === "clinician" && <SyntheticConsultLab
        patientId={DEMO_PATIENT_ID}
        identity={DEMO_IDENTITIES.clinician}
      />}

      <section className="timeline" aria-labelledby="timeline-heading">
        <div className="section-heading">
          <div><p className="eyebrow">Patient history</p><h2 id="timeline-heading">Timeline</h2></div>
          <span>{entries.length} entries</span>
        </div>
        {(demoRole === "staff" || demoRole === "clinician") && (
          <AddNote role={demoRole} onAdd={addDemoNote} />
        )}
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
                    {entry.type === "instruction" && entry.ai_derived && entry.patient_facing_status === "draft" && <span className="approval-badge approval-draft">Patient-facing draft · Needs clinician approval</span>}
                    {entry.type === "instruction" && entry.patient_facing_status === "approved" && <span className="approval-badge approval-approved">Clinician approved</span>}
                    {entry.type === "instruction" && entry.ai_derived && entry.patient_facing_status === "rejected" && <span className="approval-badge approval-rejected">Rejected · Not visible to patient</span>}
                    {clinicalSync === "current" && conflicts.some((item) => item.authoritative_entry_id === entry.id && !item.requires_clinician_review) && <span className="authoritative-badge">Authoritative source</span>}
                    {clinicalSync === "current" && conflicts.some((item) => item.requires_clinician_review && (item.authoritative_entry_id === entry.id || item.conflicting_entry_id === entry.id)) && <span className="review-badge">Conflict · review required</span>}
                    {decayByEntry[entry.id]?.durable_exempt && <span className="decay-badge durable">Durable · full detail</span>}
                    {decayByEntry[entry.id]?.storage_tier === "cold_summary" && <span className="decay-badge">Cold summary preview</span>}
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
                {entry.type === "instruction" && entry.patient_facing_status === "approved" && demoRole !== "patient" && (
                  <p className="approval-detail">Approved by: {entry.approved_by} · {entry.approved_at ? new Date(entry.approved_at).toLocaleString() : "Clinician-authored"} · Version {entry.approved_version_number}</p>
                )}
                {entry.type === "instruction" && entry.ai_derived && demoRole === "clinician" && entry.patient_facing_status !== "approved" && (
                  <div className="approval-actions" aria-label="Review patient-facing instruction">
                    {entry.provenance_pointer && <button type="button" onClick={() => navigateToSource(entry.provenance_pointer!)}>Inspect AI source</button>}
                    <button type="button" onClick={() => void decidePatientInstruction(entry, "approve")}>Approve</button>
                    <button type="button" onClick={() => void decidePatientInstruction(entry, "reject")}>Reject</button>
                  </div>
                )}
                {decayByEntry[entry.id]?.storage_tier === "cold_summary" && (
                  <div className="decay-preview">
                    <strong>Decay preview</strong>
                    <p>{decayByEntry[entry.id].display_content}</p>
                    <span>Original retained · {decayByEntry[entry.id].reason}</span>
                  </div>
                )}
                {entry.provenance_pointer && (
                  <div className="source"><span>Source</span><code>{entry.provenance_pointer}</code></div>
                )}
                {demoRole !== "patient" && (
                  <RevisionHistory
                    entry={entry}
                    versions={versionsByEntry[entry.id] ?? []}
                    citedVersions={highlights.filter((item) => item.entry_id === entry.id && item.source_version_number !== null).map((item) => item.source_version_number!)}
                    canRevert={canRevertEntry(demoRole, entry)}
                    onRevert={(versionNumber) => revertVersion(entry, versionNumber)}
                  />
                )}
                {canRevertEntry(demoRole, entry) && (
                  <EditNote entry={entry} onSave={(content) => editDemoNote(entry, content)} />
                )}
                {demoRole !== "patient" && (
                  <EntryComments
                    comments={commentsByEntry[entry.id] ?? []}
                    onAdd={(content, parentId) => addComment(entry.id, content, parentId)}
                    onToggle={toggleComment}
                  />
                )}
              </article>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}

function AddNote({
  role,
  onAdd,
}: {
  role: "staff" | "clinician";
  onAdd: (content: string) => Promise<void>;
}) {
  const [content, setContent] = useState("");
  const [saving, setSaving] = useState(false);
  const submit = async () => {
    const value = content.trim();
    if (!value) return;
    setSaving(true);
    try {
      await onAdd(value);
      setContent("");
    } finally {
      setSaving(false);
    }
  };
  return (
    <details className="note-compose">
      <summary>+ Add {role === "staff" ? "staff" : "clinician"} note</summary>
      <textarea
        value={content}
        onChange={(event) => setContent(event.target.value)}
        placeholder="Add a concise synthetic care-note update"
        aria-label={`Add ${role} note`}
      />
      <button type="button" disabled={saving || !content.trim()} onClick={() => void submit()}>
        {saving ? "Saving…" : "Add to timeline"}
      </button>
    </details>
  );
}

function EditNote({
  entry,
  onSave,
}: {
  entry: TimelineEntry;
  onSave: (content: string) => Promise<void>;
}) {
  const [content, setContent] = useState(entry.content);
  const [saving, setSaving] = useState(false);
  const [conflict, setConflict] = useState<EntryVersionConflictDetail | null>(null);
  const submit = async () => {
    const value = content.trim();
    if (!value || value === entry.content) return;
    setSaving(true);
    try {
      await onSave(value);
      setConflict(null);
    } catch (reason: unknown) {
      if (
        reason instanceof ApiError
        && reason.status === 409
        && typeof reason.detail === "object"
        && reason.detail !== null
        && (reason.detail as { error_code?: string }).error_code === "entry_version_conflict"
      ) {
        const next = preserveDraftOnConflict(content, reason.detail as EntryVersionConflictDetail);
        setContent(next.draft);
        setConflict(next.conflict);
        return;
      }
      throw reason;
    } finally {
      setSaving(false);
    }
  };
  return (
    <details className="edit-note">
      <summary>Edit note <span>expected v{entry.version}</span></summary>
      <textarea value={content} onChange={(event) => setContent(event.target.value)} />
      {conflict && (
        <section className="edit-conflict" role="alert">
          <strong>Another editor saved first</strong>
          <p>Your unsaved draft is preserved. Clinical text is never merged automatically.</p>
          <div className="conflict-compare">
            <div><b>Your unsaved draft</b><pre>{content}</pre></div>
            <div><b>Current server version {conflict.current_version}</b><pre>{conflict.current_content}</pre></div>
          </div>
          <div className="conflict-recovery-actions">
            <button type="button" onClick={() => void navigator.clipboard.writeText(content)}>Copy local draft</button>
            <button type="button" onClick={() => {
              const next = reloadCurrentServerVersion({ draft: content, conflict });
              setContent(next.draft); setConflict(next.conflict);
            }}>Reload current server version</button>
            <button type="button" onClick={() => {
              const next = cancelConflictAndKeepDraft({ draft: content, conflict });
              setContent(next.draft); setConflict(next.conflict);
            }}>Cancel and keep draft</button>
          </div>
        </section>
      )}
      <button type="button" disabled={saving || content.trim() === entry.content} onClick={() => void submit()}>
        {saving ? "Saving…" : "Save new version"}
      </button>
    </details>
  );
}

function RevisionHistory({
  entry,
  versions,
  citedVersions,
  canRevert,
  onRevert,
}: {
  entry: TimelineEntry;
  versions: EntryVersion[];
  citedVersions: number[];
  canRevert: boolean;
  onRevert: (versionNumber: number) => Promise<void>;
}) {
  return (
    <details className="revision-panel">
      <summary>Revision History <span>v{entry.version}</span></summary>
      <ol>
        {versions.map((version) => (
          <li key={version.id}>
            <div className="revision-meta">
              <strong>Version {version.version_number}</strong>
              {citedVersions.includes(version.version_number) && <span className="cited-version">Cited by highlight</span>}
              <time dateTime={version.created_at}>{new Date(version.created_at).toLocaleString()}</time>
            </div>
            <p>Changed by {version.changed_by} · {formatLabel(version.changed_by_role)}</p>
            <p className="revision-preview">{version.content}</p>
            {canRevert && version.version_number !== entry.version && (
              <button type="button" onClick={() => void onRevert(version.version_number)}>
                Revert to this version
              </button>
            )}
          </li>
        ))}
      </ol>
    </details>
  );
}

function EntryComments({
  comments,
  onAdd,
  onToggle,
}: {
  comments: Comment[];
  onAdd: (content: string, parentId: string | null) => Promise<void>;
  onToggle: (comment: Comment) => Promise<void>;
}) {
  const [content, setContent] = useState("");
  const roots = comments.filter((comment) => comment.parent_comment_id === null);
  const submit = async () => {
    const value = content.trim();
    if (!value) return;
    await onAdd(value, null);
    setContent("");
  };
  return (
    <details className="comments-panel">
      <summary>Comments <span>{comments.length}</span></summary>
      <div className="comment-thread">
        {roots.map((comment) => (
          <CommentNode
            key={comment.id}
            comment={comment}
            comments={comments}
            onAdd={onAdd}
            onToggle={onToggle}
          />
        ))}
        {roots.length === 0 && <p className="empty-comments">No internal comments.</p>}
      </div>
      <div className="comment-compose">
        <input
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder="Add comment or @mention"
          aria-label="Add internal comment"
        />
        <button type="button" onClick={() => void submit()}>Add comment</button>
      </div>
    </details>
  );
}

function CommentNode({
  comment,
  comments,
  onAdd,
  onToggle,
}: {
  comment: Comment;
  comments: Comment[];
  onAdd: (content: string, parentId: string | null) => Promise<void>;
  onToggle: (comment: Comment) => Promise<void>;
}) {
  const [replying, setReplying] = useState(false);
  const [reply, setReply] = useState("");
  const replies = comments.filter((item) => item.parent_comment_id === comment.id);
  const submitReply = async () => {
    const value = reply.trim();
    if (!value) return;
    await onAdd(value, comment.id);
    setReply("");
    setReplying(false);
  };
  return (
    <div className={`comment${comment.resolved ? " comment-resolved" : ""}`}>
      <div className="comment-meta">
        <strong>{formatLabel(comment.author_role)}</strong>
        <time dateTime={comment.created_at}>{new Date(comment.created_at).toLocaleString()}</time>
      </div>
      <p>{comment.content}</p>
      {comment.mentions.length > 0 && (
        <div className="mentions">{comment.mentions.map((mention) => <span key={mention}>@{mention}</span>)}</div>
      )}
      <div className="comment-actions">
        <button type="button" onClick={() => setReplying((value) => !value)}>Reply</button>
        <button type="button" onClick={() => void onToggle(comment)}>{comment.resolved ? "Unresolve" : "Resolve"}</button>
      </div>
      {replying && (
        <div className="comment-compose reply-compose">
          <input value={reply} onChange={(event) => setReply(event.target.value)} placeholder="Reply or @mention" />
          <button type="button" onClick={() => void submitReply()}>Reply</button>
        </div>
      )}
      {replies.length > 0 && (
        <div className="comment-replies">
          {replies.map((item) => (
            <CommentNode key={item.id} comment={item} comments={comments} onAdd={onAdd} onToggle={onToggle} />
          ))}
        </div>
      )}
    </div>
  );
}

function DemoIdentity({
  role,
  onChange,
}: {
  role: DemoRole;
  onChange: (role: DemoRole) => void;
}) {
  return (
    <aside className="demo-identity" aria-label="Demo identity simulation">
      <div>
        <strong>Demo identity simulation</strong>
        <span>Server authorization remains enforced</span>
      </div>
      <label>
        Role
        <select value={role} onChange={(event) => onChange(event.target.value as DemoRole)}>
          <option value="patient">Patient</option>
          <option value="staff">Staff</option>
          <option value="clinician">Clinician</option>
          <option value="admin">Admin</option>
        </select>
      </label>
    </aside>
  );
}
