import type {
  ApiIdentity,
  Comment,
  ConflictRecord,
  DataDecayPreview,
  EntryVersion,
  Highlight,
  HighlightSourceSnapshot,
  ImportancePreference,
  Patient,
  PatientDelivery,
  TaskAssignment,
  TimelineEntry,
  TrustMetrics,
} from "./types.ts";

const API_BASE_URL = import.meta.env?.VITE_API_URL ?? "/api";

const identityHeaders = (identity: ApiIdentity) => ({
  "X-User-Id": identity.userId,
  "X-Role": identity.role,
  "X-Clinic-Id": identity.clinicId,
});

export class ApiError<TDetail = unknown> extends Error {
  readonly status: number;
  readonly detail: TDetail;

  constructor(
    status: number,
    detail: TDetail,
  ) {
    super(`Request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

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
    let detail: unknown = null;
    try {
      const body = await response.json() as { detail?: unknown };
      detail = body.detail ?? null;
    } catch {
      detail = null;
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export const getPatient = (patientId: string, identity: ApiIdentity) =>
  requestJson<Patient>(`/patients/${patientId}`, identity);

export const getPatientEntries = (patientId: string, identity: ApiIdentity) =>
  requestJson<TimelineEntry[]>(`/patients/${patientId}/entries`, identity);

export const getPatientHighlights = (patientId: string, identity: ApiIdentity) =>
  requestJson<Highlight[]>(`/patients/${patientId}/highlights`, identity);

export const getHighlightSource = (highlightId: string, identity: ApiIdentity) =>
  requestJson<HighlightSourceSnapshot>(`/highlights/${highlightId}/source`, identity);

export const getPatientDeliveries = (patientId: string, identity: ApiIdentity) =>
  requestJson<PatientDelivery[]>(`/patients/${patientId}/deliveries`, identity);

export const createMockDelivery = (
  entryId: string,
  identity: ApiIdentity,
  purpose: "instruction" | "appointment_link" | "correction" = "instruction",
  replacesDeliveryId: string | null = null,
) => requestJson<PatientDelivery>(`/entries/${entryId}/deliveries`, identity, {
  method: "POST",
  body: JSON.stringify({
    channel: "whatsapp_mock",
    purpose,
    replaces_delivery_id: replacesDeliveryId,
  }),
});

export const setMockDeliveryStatus = (
  deliveryId: string,
  status: "queued" | "simulated_sent" | "simulated_delivered" | "failed",
  identity: ApiIdentity,
) => requestJson<PatientDelivery>(`/deliveries/${deliveryId}/status`, identity, {
  method: "PATCH",
  body: JSON.stringify({
    status,
    failure_reason_code: status === "failed" ? "channel_unavailable" : null,
  }),
});

export const acceptHighlight = (highlightId: string, identity: ApiIdentity) =>
  requestJson<Highlight>(`/highlights/${highlightId}/accept`, identity, { method: "POST" });

export const rejectHighlight = (highlightId: string, identity: ApiIdentity) =>
  requestJson<Highlight>(`/highlights/${highlightId}/reject`, identity, { method: "POST" });

export const undoHighlightFeedback = (highlightId: string, identity: ApiIdentity) =>
  requestJson<Highlight>(`/highlights/${highlightId}/feedback/undo`, identity, { method: "POST" });

export const recordHighlightExposure = (
  highlightId: string, displayReference: string, identity: ApiIdentity,
) => requestJson<{ recorded: boolean }>(`/highlights/${highlightId}/exposures`, identity, {
  method: "POST",
  body: JSON.stringify({ display_reference: displayReference }),
});

export const getHighlightReviewQueue = (patientId: string, identity: ApiIdentity) =>
  requestJson<Highlight[]>(`/patients/${patientId}/highlight-review-queue`, identity);

export const getHighlightTrustMetrics = (patientId: string, identity: ApiIdentity) =>
  requestJson<TrustMetrics>(`/patients/${patientId}/highlight-trust-metrics`, identity);

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

export const approvePatientInstruction = (entryId: string, identity: ApiIdentity) =>
  requestJson<TimelineEntry>(`/entries/${entryId}/patient-facing/approve`, identity, {
    method: "POST",
  });

export const rejectPatientInstruction = (entryId: string, identity: ApiIdentity) =>
  requestJson<TimelineEntry>(`/entries/${entryId}/patient-facing/reject`, identity, {
    method: "POST",
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
