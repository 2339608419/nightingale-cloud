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
  version: number;
}

export interface EntryVersion {
  id: string;
  entry_id: string;
  version_number: number;
  content: string;
  provenance_pointer: string | null;
  changed_by: string;
  changed_by_role: string;
  created_at: string;
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
  evidence_confidence_level: "high" | "medium" | "low" | "abstain";
  confidence_reason: string;
  requires_review: boolean;
  abstained: boolean;
  provenance_resolved: boolean;
  source_span_verified: boolean;
  structured_fact_match: boolean;
  open_conflict: boolean;
}

export type DemoRole = "patient" | "staff" | "clinician" | "admin";

export interface ApiIdentity {
  userId: string;
  role: DemoRole;
  clinicId: string;
}

export interface Comment {
  id: string;
  entry_id: string;
  author_id: string;
  author_role: "staff" | "clinician" | "admin";
  content: string;
  parent_comment_id: string | null;
  resolved: boolean;
  created_at: string;
  mentions: string[];
}

export interface TaskAssignment {
  id: string;
  patient_id: string;
  entry_id: string | null;
  title: string;
  assigned_role: "staff" | "clinician" | "admin";
  assigned_user_id: string | null;
  status: "open" | "completed";
  created_at: string;
  resolved_at: string | null;
}

export interface DataDecayPreview {
  entry_id: string;
  storage_tier: "full_detail" | "cold_summary";
  display_content: string;
  original_available: boolean;
  durable_exempt: boolean;
  reason: string;
  provenance_pointer: string | null;
}

export interface ImportancePreference {
  category_type: string;
  category_value: string;
  accepted_count: number;
  rejected_count: number;
  weight: number;
  explanation: string;
}

export interface ConflictRecord {
  id: string;
  patient_id: string;
  authoritative_entry_id: string;
  conflicting_entry_id: string;
  entity_type: "medication" | "allergy" | "follow_up";
  entity_name: string;
  prior_value: string;
  authoritative_value: string;
  status: "open" | "resolved";
  created_at: string;
  resolved_at: string | null;
  authoritative_provenance_pointer: string;
  conflicting_provenance_pointer: string;
}
