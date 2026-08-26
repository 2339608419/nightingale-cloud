import { useEffect, useState } from "react";
import {
  acceptHighlight,
  completeAssignment,
  createComment,
  getEntryComments,
  getEntryVersions,
  getOpenAssignments,
  getPatient,
  getPatientEntries,
  getPatientHighlights,
  setCommentResolution,
  revertEntry,
  rejectHighlight,
} from "./api";
import type {
  ApiIdentity,
  Comment,
  DemoRole,
  EntryVersion,
  Highlight,
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

const isAiGenerated = (entry: TimelineEntry) => entry.type.startsWith("ai_");

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

    const load = async () => {
      try {
        const [patientData, entryData, highlightData] = await Promise.all([
          getPatient(DEMO_PATIENT_ID, identity),
          getPatientEntries(DEMO_PATIENT_ID, identity),
          getPatientHighlights(DEMO_PATIENT_ID, identity),
        ]);
        let commentData: Record<string, Comment[]> = {};
        let assignmentData: TaskAssignment[] = [];
        if (demoRole !== "patient") {
          const [openAssignments, entryComments, entryVersions] = await Promise.all([
            getOpenAssignments(DEMO_PATIENT_ID, identity),
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
          commentData = Object.fromEntries(entryComments);
          if (!cancelled) setVersionsByEntry(Object.fromEntries(entryVersions));
        }
        if (cancelled) return;
        setPatient(patientData);
        setEntries(entryData);
        setHighlights(highlightData);
        setCommentsByEntry(commentData);
        setAssignments(assignmentData);
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

  const navigateToSource = (highlight: Highlight) => {
    const source = document.getElementById(highlight.provenance_pointer);
    if (!source) return;
    window.history.replaceState(null, "", `#${highlight.provenance_pointer}`);
    source.scrollIntoView({ behavior: "smooth", block: "center" });
    source.classList.remove("source-focus");
    requestAnimationFrame(() => source.classList.add("source-focus"));
    window.setTimeout(() => source.classList.remove("source-focus"), 2200);
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
    await completeAssignment(assignment.id, DEMO_IDENTITIES[demoRole]);
    setAssignments((current) => current.filter((item) => item.id !== assignment.id));
  };

  const decideHighlight = async (highlight: Highlight, decision: "accept" | "reject") => {
    try {
      const updated = decision === "accept"
        ? await acceptHighlight(highlight.id, DEMO_IDENTITIES[demoRole])
        : await rejectHighlight(highlight.id, DEMO_IDENTITIES[demoRole]);
      setHighlights((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Unable to update highlight");
    }
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
                <button className="highlight-source" type="button" onClick={() => navigateToSource(highlight)}>
                  <span className="highlight-topline">
                    <strong>{highlight.text}</strong>
                    <span className={`risk risk-${highlight.risk_level}`}>{formatLabel(highlight.risk_level)}</span>
                  </span>
                  <span className="risk-reason">{highlight.risk_reason}</span>
                  <span className="highlight-state">
                    {highlight.unresolved_action && <span className="state-open">Action unresolved</span>}
                    {highlight.clinician_confirmed && <span className="state-confirmed">Clinician confirmed</span>}
                    <span className={`highlight-status status-${highlight.status}`}>{formatLabel(highlight.status)}</span>
                    <span className="provenance">View source ↓</span>
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
        </div>
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
                {demoRole !== "patient" && (
                  <RevisionHistory
                    entry={entry}
                    versions={versionsByEntry[entry.id] ?? []}
                    canRevert={canRevertEntry(demoRole, entry)}
                    onRevert={(versionNumber) => revertVersion(entry, versionNumber)}
                  />
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
