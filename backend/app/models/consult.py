from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class ConsultMode(str, Enum):
    SYNTHETIC_TEXT_STREAM = "synthetic_text_stream"


class ConsultState(str, Enum):
    CREATED = "created"
    RECEIVING = "receiving"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"


class SegmentState(str, Enum):
    PARTIAL = "partial"
    FINAL = "final"
    SUPERSEDED = "superseded"


class CaptureState(str, Enum):
    CAPTURED = "captured"
    NEEDS_CONFIRMATION = "needs_confirmation"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class SummaryAudience(str, Enum):
    CLINICIAN = "clinician"
    STAFF = "staff"
    PATIENT = "patient"


class ConsultSession(Base):
    __tablename__ = "consult_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    clinic_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    mode: Mapped[ConsultMode] = mapped_column(SqlEnum(ConsultMode, values_callable=lambda x: [v.value for v in x], native_enum=False), nullable=False)
    state: Mapped[ConsultState] = mapped_column(SqlEnum(ConsultState, values_callable=lambda x: [v.value for v in x], native_enum=False), nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    noise_profile: Mapped[str] = mapped_column(String(40), nullable=False, default="simulated_clinic_noise")
    generation_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="rule_derived")
    provider_status: Mapped[str] = mapped_column(String(30), nullable=False, default="not_invoked")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    __table_args__ = (UniqueConstraint("session_id", "sequence_number", "version_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("consult_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(nullable=False)
    version_number: Mapped[int] = mapped_column(nullable=False, default=1)
    start_offset_ms: Mapped[int] = mapped_column(nullable=False)
    end_offset_ms: Mapped[int] = mapped_column(nullable=False)
    speaker: Mapped[str] = mapped_column(String(20), nullable=False)
    original_synthetic_text: Mapped[str] = mapped_column(Text, nullable=False)
    language_spans: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    state: Mapped[SegmentState] = mapped_column(SqlEnum(SegmentState, values_callable=lambda x: [v.value for v in x], native_enum=False), nullable=False)
    capture_uncertainty: Mapped[str | None] = mapped_column(String(60), nullable=True)
    alternatives: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    correction_status: Mapped[str] = mapped_column(String(30), nullable=False, default="original")
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    provenance_pointer: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ProvisionalSafetySignal(Base):
    __tablename__ = "provisional_safety_signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("consult_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_id: Mapped[str] = mapped_column(ForeignKey("transcript_segments.id", ondelete="RESTRICT"), nullable=False)
    segment_version_number: Mapped[int] = mapped_column(nullable=False)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="needs_confirmation")
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="high")
    provenance_pointer: Mapped[str] = mapped_column(String(100), nullable=False)
    source_offset_ms: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ClinicalCapture(Base):
    __tablename__ = "clinical_captures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("consult_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_id: Mapped[str] = mapped_column(ForeignKey("transcript_segments.id", ondelete="RESTRICT"), nullable=False)
    segment_version_number: Mapped[int] = mapped_column(nullable=False)
    captured_term: Mapped[str] = mapped_column(String(80), nullable=False)
    exact_source_phrase: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_values: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    state: Mapped[CaptureState] = mapped_column(SqlEnum(CaptureState, values_callable=lambda x: [v.value for v in x], native_enum=False), nullable=False)
    reference_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_source_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_scope: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confirmed_value: Mapped[str | None] = mapped_column(String(80), nullable=True)
    confirmed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provenance_pointer: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ConsultSummary(Base):
    __tablename__ = "consult_summaries"
    __table_args__ = (UniqueConstraint("session_id", "audience"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("consult_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    audience: Mapped[SummaryAudience] = mapped_column(SqlEnum(SummaryAudience, values_callable=lambda x: [v.value for v in x], native_enum=False), nullable=False)
    generation_mode: Mapped[str] = mapped_column(String(40), nullable=False, default="rule_derived")
    timeline_entry_id: Mapped[str] = mapped_column(ForeignKey("timeline_entries.id", ondelete="RESTRICT"), nullable=False)
    source_provenance: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_status: Mapped[str] = mapped_column(String(20), nullable=False, default="current")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
