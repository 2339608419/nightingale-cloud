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

