export interface Patient {
  id: string;
  clinic_id: string;
  name: string;
  date_of_birth: string;
  created_at: string;
}

export interface TimelineEntry {
  id: string;
  patient_id: string;
  author_role: string;
  author_id: string;
  timestamp: string;
  type: string;
  content: string;
  provenance_pointer: string | null;
}

export interface Highlight {
  id: string;
  patient_id: string;
  entry_id: string;
  source_span: string;
  text: string;
  importance_score: number;
  risk_level: "none" | "low" | "moderate" | "high" | "critical";
  risk_reason: string;
  status: "suggested" | "accepted" | "rejected";
  provenance_pointer: string;
  created_at: string;
  clinician_confirmed: boolean;
  unresolved_action: boolean;
  clinical_entity_type: string;
}
