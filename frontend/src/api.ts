import type {
  ApiIdentity,
  Comment,
  Highlight,
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

export const completeAssignment = (assignmentId: string, identity: ApiIdentity) =>
  requestJson<TaskAssignment>(`/assignments/${assignmentId}`, identity, {
    method: "PATCH",
    body: JSON.stringify({ status: "completed" }),
  });
