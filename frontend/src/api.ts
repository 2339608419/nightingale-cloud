import type { ApiIdentity, Highlight, Patient, TimelineEntry } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

const identityHeaders = (identity: ApiIdentity) => ({
  "X-User-Id": identity.userId,
  "X-Role": identity.role,
  "X-Clinic-Id": identity.clinicId,
});

async function getJson<T>(path: string, identity: ApiIdentity): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: identityHeaders(identity),
  });
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const getPatient = (patientId: string, identity: ApiIdentity) =>
  getJson<Patient>(`/patients/${patientId}`, identity);

export const getPatientEntries = (patientId: string, identity: ApiIdentity) =>
  getJson<TimelineEntry[]>(`/patients/${patientId}/entries`, identity);

export const getPatientHighlights = (patientId: string, identity: ApiIdentity) =>
  getJson<Highlight[]>(`/patients/${patientId}/highlights`, identity);
