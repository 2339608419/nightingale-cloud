import type { Highlight, Patient, TimelineEntry } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_URL ?? "/api";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const getPatient = (patientId: string) =>
  getJson<Patient>(`/patients/${patientId}`);

export const getPatientEntries = (patientId: string) =>
  getJson<TimelineEntry[]>(`/patients/${patientId}/entries`);

export const getPatientHighlights = (patientId: string) =>
  getJson<Highlight[]>(`/patients/${patientId}/highlights`);
