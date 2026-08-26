import { useEffect, useState } from "react";
import {
  acceptHighlight,
  completeAssignment,
  createComment,
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
  getImportancePreferences,
  setCommentResolution,
  revertEntry,
  rejectHighlight,
  resolveConflict,
  updateNote,
} from "./api";
import type {
  ApiIdentity,
  Comment,
  ConflictRecord,
  DataDecayPreview,
  DemoRole,
  EntryVersion,
  Highlight,
  ImportancePreference,
  Patient,
  TaskAssignment,
  TimelineEntry,
} from "./types";

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
  entry.type.startsWith("ai_") || entry.author_id.startsWith("ai-scribe:");

const canRevertEntry = (role: DemoRole, entry: TimelineEntry) =>
  (role === "staff" && entry.author_role === "staff" && entry.type === "staff_note") ||
  (role === "clinician" && entry.author_role === "clinician" &&
    ["clinician_note", "instruction"].includes(entry.type));

const formatLabel = (value: string) =>
  value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

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
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    const identity = DEMO_IDENTITIES[demoRole];
    let cancelled = false;
    setPatient(null);
    setError(null);
    setCommentsByEntry({});
    setVersionsByEntry({});
    setAssignments([]);
    setCompletedAssignments([]);
    setPreferences([]);
    setConflicts([]);

    const load = async () => {
      try {
        const [patientData, entryData, highlightData, decayData] = await Promise.all([
          getPatient(DEMO_PATIENT_ID, identity),
          getPatientEntries(DEMO_PATIENT_ID, identity),
          getPatientHighlights(DEMO_PATIENT_ID, identity),
          getDataDecayPreview(DEMO_PATIENT_ID, identity),
        ]);
        if (cancelled) return;
        // Render the patient and Glance View as soon as their core requests finish.
        // Collaboration/history data is intentionally loaded afterward so an N-entry
        // request fan-out cannot delay the clinically important top card.
        setPatient(patientData);
        setEntries(entryData);
        setHighlights(highlightData);
        setDecayByEntry(Object.fromEntries(decayData.map((item) => [item.entry_id, item])));
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
        }
        if (cancelled) return;
        setCommentsByEntry(commentData);
        setAssignments(assignmentData);
        setCompletedAssignments(completedAssignmentData);
        setPreferences(preferenceData);
        setConflicts(conflictData);
      } catch (reason: unknown) {
        if (cancelled) return;
        setError(reason instanceof Error ? reason.message : "Unable to load patient");
      }
    };
    void load();
    return () => { cancelled = true; };
  }, [demoRole, reloadToken]);

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

  const addDemoNote = async (content: string) => {
    const type = demoRole === "staff" ? "staff_note" : "clinician_note";
    await createNote(DEMO_PATIENT_ID, type, content, DEMO_IDENTITIES[demoRole]);
    setReloadToken((value) => value + 1);
  };

  const editDemoNote = async (entry: TimelineEntry, content: string) => {
    await updateNote(entry, content, DEMO_IDENTITIES[demoRole]);
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
          <p>Highest-priority current items</p>
        </div>
        <div className="glance-content">
          <ol className="highlight-list">
            {highlights.map((highlight) => (
              <li key={highlight.id} className="highlight-item">
                <button className="highlight-source" type="button" onClick={() => navigateToSource(highlight.provenance_pointer)}>
                  <span className="highlight-topline">
                    <strong>{highlight.text}</strong>
                    <span className={`risk risk-${highlight.risk_level}`}>{formatLabel(highlight.risk_level)}</span>
                  </span>
                  <span className="risk-reason">{highlight.risk_reason}</span>
                  <span className="highlight-state">
                    {highlight.unresolved_action && <span className="state-open">Action unresolved</span>}
                    {highlight.clinician_confirmed && <span className="state-confirmed">Clinician confirmed</span>}
                    <span className={`highlight-status status-${highlight.status}`}>{formatLabel(highlight.status)}</span>
                    <span className="provenance">Open exact source ↓</span>
                  </span>
                </button>
                {demoRole === "clinician" && highlight.status === "suggested" && (
                  <div className="highlight-decisions" aria-label={`Review ${highlight.text}`}>
                    <button type="button" onClick={() => void decideHighlight(highlight, "accept")}>Accept</button>
                    <button type="button" onClick={() => void decideHighlight(highlight, "reject")}>Reject</button>
                  </div>
                )}
              </li>
            ))}
          </ol>
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
          {demoRole !== "patient" && completedAssignments.length > 0 && (
            <section className="completed-actions" aria-label="Recently completed actions">
              <strong>Recently completed</strong>
              <span>✓ {completedAssignments[0].title}</span>
            </section>
          )}
        </div>
      </section>

      {(demoRole === "clinician" || demoRole === "admin") && conflicts.length > 0 && (
        <section className="conflict-panel" aria-labelledby="conflict-heading">
          <div className="conflict-heading">
            <div><p className="eyebrow">Internal review</p><h2 id="conflict-heading">Clinical conflicts</h2></div>
            <span>{conflicts.length} open</span>
          </div>
          <p>Clinician-authored information takes precedence. Prior AI/patient sources remain available for review.</p>
          <ul>
            {conflicts.map((conflict) => (
              <li key={conflict.id}>
                <div className="conflict-values">
                  <span><b>Prior {formatLabel(conflict.entity_type)}</b>{formatLabel(conflict.entity_name)}: {conflict.prior_value}</span>
                  <span className="authoritative-value"><b>Authoritative clinician value</b>{formatLabel(conflict.entity_name)}: {conflict.authoritative_value}</span>
                </div>
                <div className="conflict-actions">
                  <button type="button" onClick={() => navigateToSource(conflict.conflicting_provenance_pointer)}>Prior source</button>
                  <button type="button" onClick={() => navigateToSource(conflict.authoritative_provenance_pointer)}>Clinician source</button>
                  {demoRole === "clinician" && <button type="button" onClick={() => void closeConflict(conflict)}>Mark resolved</button>}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

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
                    {conflicts.some((item) => item.authoritative_entry_id === entry.id) && <span className="authoritative-badge">Clinician authoritative</span>}
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
  const submit = async () => {
    const value = content.trim();
    if (!value || value === entry.content) return;
    setSaving(true);
    try {
      await onSave(value);
    } finally {
      setSaving(false);
    }
  };
  return (
    <details className="edit-note">
      <summary>Edit note <span>expected v{entry.version}</span></summary>
      <textarea value={content} onChange={(event) => setContent(event.target.value)} />
      <button type="button" disabled={saving || content.trim() === entry.content} onClick={() => void submit()}>
        {saving ? "Saving…" : "Save new version"}
      </button>
    </details>
  );
}

function RevisionHistory({
  entry,
  versions,
  canRevert,
  onRevert,
}: {
  entry: TimelineEntry;
  versions: EntryVersion[];
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
