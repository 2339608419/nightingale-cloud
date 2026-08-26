import type {
  ApiIdentity,
  Comment,
  ConflictRecord,
  DataDecayPreview,
  EntryVersion,
  Highlight,
  ImportancePreference,
  Patient,
  TaskAssignment,
  TimelineEntry,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

const identityHeaders = (identity: ApiIdentity) => ({
  "X-User-Id": identity.userId,
  "X-Role": identity.role,
  "X-Clinic-Id": identity.clinicId,
});

async function requestJson<T>(
  path: string,
  identity: ApiIdentity,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...identityHeaders(identity),
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const getPatient = (patientId: string, identity: ApiIdentity) =>
  requestJson<Patient>(`/patients/${patientId}`, identity);

export const getPatientEntries = (patientId: string, identity: ApiIdentity) =>
  requestJson<TimelineEntry[]>(`/patients/${patientId}/entries`, identity);

export const getPatientHighlights = (patientId: string, identity: ApiIdentity) =>
  requestJson<Highlight[]>(`/patients/${patientId}/highlights`, identity);

export const acceptHighlight = (highlightId: string, identity: ApiIdentity) =>
  requestJson<Highlight>(`/highlights/${highlightId}/accept`, identity, { method: "POST" });

export const rejectHighlight = (highlightId: string, identity: ApiIdentity) =>
  requestJson<Highlight>(`/highlights/${highlightId}/reject`, identity, { method: "POST" });

export const getDataDecayPreview = (patientId: string, identity: ApiIdentity) =>
  requestJson<DataDecayPreview[]>(`/patients/${patientId}/decay-preview`, identity);

export const getImportancePreferences = (identity: ApiIdentity) =>
  requestJson<ImportancePreference[]>("/importance-preferences", identity);

export const getOpenConflicts = (patientId: string, identity: ApiIdentity) =>
  requestJson<ConflictRecord[]>(`/patients/${patientId}/conflicts?status=open`, identity);

export const resolveConflict = (conflictId: string, identity: ApiIdentity) =>
  requestJson<ConflictRecord>(`/conflicts/${conflictId}/resolve`, identity, { method: "POST" });

export const createNote = (
  patientId: string,
  type: "staff_note" | "clinician_note",
  content: string,
  identity: ApiIdentity,
) => requestJson<TimelineEntry>(`/patients/${patientId}/entries`, identity, {
  method: "POST",
  body: JSON.stringify({ type, content }),
});

export const updateNote = (
  entry: TimelineEntry,
  content: string,
  identity: ApiIdentity,
) => requestJson<TimelineEntry>(`/entries/${entry.id}`, identity, {
  method: "PATCH",
  body: JSON.stringify({ content, expected_version: entry.version }),
});

export const getEntryComments = (entryId: string, identity: ApiIdentity) =>
  requestJson<Comment[]>(`/entries/${entryId}/comments`, identity);

export const createComment = (
  entryId: string,
  content: string,
  parentCommentId: string | null,
  identity: ApiIdentity,
) =>
  requestJson<Comment>(`/entries/${entryId}/comments`, identity, {
    method: "POST",
    body: JSON.stringify({ content, parent_comment_id: parentCommentId }),
  });

export const setCommentResolution = (
  commentId: string,
  resolved: boolean,
  identity: ApiIdentity,
) =>
  requestJson<Comment>(`/comments/${commentId}/resolution`, identity, {
    method: "PATCH",
    body: JSON.stringify({ resolved }),
  });

export const getOpenAssignments = (patientId: string, identity: ApiIdentity) =>
  requestJson<TaskAssignment[]>(`/patients/${patientId}/assignments?status=open`, identity);

export const getCompletedAssignments = (patientId: string, identity: ApiIdentity) =>
  requestJson<TaskAssignment[]>(`/patients/${patientId}/assignments?status=completed`, identity);

export const completeAssignment = (assignmentId: string, identity: ApiIdentity) =>
  requestJson<TaskAssignment>(`/assignments/${assignmentId}`, identity, {
    method: "PATCH",
    body: JSON.stringify({ status: "completed" }),
  });

export const getEntryVersions = (entryId: string, identity: ApiIdentity) =>
  requestJson<EntryVersion[]>(`/entries/${entryId}/versions`, identity);

export const revertEntry = (
  entryId: string,
  versionNumber: number,
  expectedVersion: number,
  identity: ApiIdentity,
) =>
  requestJson<TimelineEntry>(`/entries/${entryId}/revert/${versionNumber}`, identity, {
    method: "POST",
    body: JSON.stringify({ expected_version: expectedVersion }),
  });
