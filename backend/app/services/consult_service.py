import logging
import re
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import (
    AuthorRole, CaptureState, ClinicalCapture, ConsultSession, ConsultState,
    ConsultSummary, PatientFacingStatus, ProvisionalSafetySignal, SegmentState,
    SummaryAudience, TimelineEntry, TimelineEntryType, TranscriptSegment,
)
from app.schemas.consult import TranscriptSegmentCreate, TranscriptSegmentCorrect
from app.services.audit_service import add_trust_action_audit
from app.services.patient_service import create_patient_entry


logger = logging.getLogger(__name__)
MONTELUKAST_AMBIGUITY = re.compile(
    r"(?P<phrase>Montelukast[^.?!]*?(?P<first>\d+\s*mg)[^0-9]+(?P<second>\d+\s*mg))",
    re.IGNORECASE,
)
SUPPORTED_LANGUAGES = {"english", "malay", "hokkien", "mandarin", "tamil"}


def create_session(db: Session, patient_id: str, clinic_id: str, noise_profile: str) -> ConsultSession:
    session = ConsultSession(
        id=str(uuid4()), clinic_id=clinic_id, patient_id=patient_id,
        mode="synthetic_text_stream", state=ConsultState.CREATED, synthetic=True,
        noise_profile=noise_profile, generation_mode="rule_derived", provider_status="not_invoked",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("Synthetic consult created session_id=%s state=%s", session.id, session.state.value)
    return session


def _validate_languages(payload: TranscriptSegmentCreate) -> tuple[bool, list[str]]:
    languages = [span.language.lower() for span in payload.language_spans]
    return all(item in SUPPORTED_LANGUAGES for item in languages), languages


def _derive_from_final_segment(db: Session, session: ConsultSession, segment: TranscriptSegment) -> None:
    lower = segment.original_synthetic_text.lower()
    supported = all(span.get("language", "").lower() in SUPPORTED_LANGUAGES for span in segment.language_spans)
    if "allerg" in lower and segment.state == SegmentState.FINAL:
        status = "needs_confirmation" if supported else "needs_confirmation_unsupported_language"
        db.add(ProvisionalSafetySignal(
            id=str(uuid4()), session_id=session.id, segment_id=segment.id,
            segment_version_number=segment.version_number, entity_type="allergy",
            status=status, risk_level="high", provenance_pointer=segment.provenance_pointer,
            source_offset_ms=segment.start_offset_ms,
        ))
    match = MONTELUKAST_AMBIGUITY.search(segment.original_synthetic_text)
    if match:
        db.add(ClinicalCapture(
            id=str(uuid4()), session_id=session.id, segment_id=segment.id,
            segment_version_number=segment.version_number, captured_term="Montelukast",
            exact_source_phrase=match.group("phrase"),
            candidate_values=[match.group("first"), match.group("second")],
            state=CaptureState.NEEDS_CONFIRMATION,
            reference_title="Nightingale curated prototype medication terminology",
            reference_source_id="prototype-medication-catalog-v1",
            reference_scope="Term and dosage-unit plausibility only; not the patient's actual dose.",
            provenance_pointer=segment.provenance_pointer,
        ))
    elif not supported or ("allerg" in lower and "penicillin" not in lower):
        db.add(ClinicalCapture(
            id=str(uuid4()), session_id=session.id, segment_id=segment.id,
            segment_version_number=segment.version_number,
            captured_term="unresolved_clinical_phrase", exact_source_phrase=segment.original_synthetic_text,
            candidate_values=[], state=CaptureState.NEEDS_CONFIRMATION,
            reference_scope="Unsupported or unrecognized phrasing; human review required.",
            provenance_pointer=segment.provenance_pointer,
        ))


def append_segment(db: Session, session: ConsultSession, payload: TranscriptSegmentCreate) -> TranscriptSegment:
    if session.state in {ConsultState.FINALIZING, ConsultState.COMPLETED, ConsultState.FAILED}:
        raise HTTPException(status_code=409, detail="Session no longer accepts segments")
    max_sequence = db.scalar(select(func.max(TranscriptSegment.sequence_number)).where(
        TranscriptSegment.session_id == session.id,
        TranscriptSegment.is_current.is_(True),
    )) or 0
    if payload.sequence_number != max_sequence + 1:
        raise HTTPException(status_code=409, detail="Segment sequence must be contiguous and unique")
    previous_end = db.scalar(select(func.max(TranscriptSegment.end_offset_ms)).where(
        TranscriptSegment.session_id == session.id,
        TranscriptSegment.is_current.is_(True),
    )) or 0
    if payload.start_offset_ms < previous_end:
        raise HTTPException(status_code=422, detail="Segment offsets must be ordered")
    segment_id = str(uuid4())
    segment = TranscriptSegment(
        id=segment_id, session_id=session.id, sequence_number=payload.sequence_number,
        version_number=1, start_offset_ms=payload.start_offset_ms,
        end_offset_ms=payload.end_offset_ms, speaker=payload.speaker,
        original_synthetic_text=payload.original_synthetic_text,
        language_spans=[item.model_dump() for item in payload.language_spans],
        state=SegmentState(payload.state), capture_uncertainty=payload.capture_uncertainty,
        alternatives=payload.alternatives, correction_status="original", is_current=True,
        provenance_pointer=f"consult-segment-{segment_id}-v1",
    )
    session.state = ConsultState.RECEIVING
    db.add(segment)
    db.flush()
    if segment.state == SegmentState.FINAL:
        _derive_from_final_segment(db, session, segment)
    db.commit()
    db.refresh(segment)
    logger.info(
        "Synthetic segment received session_id=%s segment_id=%s sequence=%d state=%s language_span_count=%d",
        session.id, segment.id, segment.sequence_number, segment.state.value, len(segment.language_spans),
    )
    return segment


def correct_segment(
    db: Session, session: ConsultSession, current: TranscriptSegment,
    payload: TranscriptSegmentCorrect, actor: CurrentUser,
) -> TranscriptSegment:
    if current.state != SegmentState.FINAL or not current.is_current:
        raise HTTPException(status_code=409, detail="Only the current finalized segment can be corrected")
    current.is_current = False
    current.state = SegmentState.SUPERSEDED
    current.correction_status = "superseded_by_correction"
    for signal in db.scalars(select(ProvisionalSafetySignal).where(
        ProvisionalSafetySignal.segment_id == current.id,
        ProvisionalSafetySignal.segment_version_number == current.version_number,
    )):
        signal.status = "superseded"
    for capture in db.scalars(select(ClinicalCapture).where(
        ClinicalCapture.segment_id == current.id,
        ClinicalCapture.segment_version_number == current.version_number,
    )):
        capture.state = CaptureState.SUPERSEDED
    new_version = current.version_number + 1
    replacement_id = str(uuid4())
    replacement = TranscriptSegment(
        id=replacement_id, session_id=session.id, sequence_number=current.sequence_number,
        version_number=new_version, start_offset_ms=current.start_offset_ms,
        end_offset_ms=current.end_offset_ms, speaker=current.speaker,
        original_synthetic_text=payload.original_synthetic_text,
        language_spans=[item.model_dump() for item in payload.language_spans],
        state=SegmentState.FINAL, capture_uncertainty=payload.capture_uncertainty,
        alternatives=payload.alternatives, correction_status="corrected", is_current=True,
        provenance_pointer=f"consult-segment-{replacement_id}-v{new_version}",
    )
    db.add(replacement)
    for summary in db.scalars(select(ConsultSummary).where(ConsultSummary.session_id == session.id)):
        summary.source_status = "stale"
        entry = db.get(TimelineEntry, summary.timeline_entry_id)
        if entry and entry.patient_instruction_approval and entry.patient_instruction_approval.patient_facing_status == PatientFacingStatus.APPROVED:
            from app.services.delivery_service import invalidate_deliveries_after_content_change

            invalidate_deliveries_after_content_change(db, entry, actor)
            approval = entry.patient_instruction_approval
            approval.patient_facing_status = PatientFacingStatus.DRAFT
            approval.approved_by = None
            approval.approved_at = None
            approval.approved_version_number = None
            add_trust_action_audit(
                db, actor=actor, action="patient_instruction.approval_invalidated",
                entity_type="timeline_entry", entity_id=entry.id,
                from_status="approved", to_status="draft",
            )
    db.flush()
    _derive_from_final_segment(db, session, replacement)
    add_trust_action_audit(
        db, actor=actor, action="consult_segment.corrected", entity_type="transcript_segment",
        entity_id=replacement.id, from_status="final", to_status="corrected",
    )
    db.commit()
    db.refresh(replacement)
    return replacement


def finalize_partial_segment(
    db: Session, session: ConsultSession, current: TranscriptSegment,
    payload: TranscriptSegmentCorrect, actor: CurrentUser,
) -> TranscriptSegment:
    if session.state != ConsultState.RECEIVING:
        raise HTTPException(status_code=409, detail="Session no longer accepts segment finalization")
    if current.state != SegmentState.PARTIAL or not current.is_current:
        raise HTTPException(status_code=409, detail="Only the current partial segment can be finalized")
    claimed = db.execute(
        update(TranscriptSegment)
        .where(
            TranscriptSegment.id == current.id,
            TranscriptSegment.session_id == session.id,
            TranscriptSegment.is_current.is_(True),
            TranscriptSegment.state == SegmentState.PARTIAL,
        )
        .values(
            is_current=False,
            state=SegmentState.SUPERSEDED,
            correction_status="superseded_by_final",
        )
    )
    if claimed.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="Partial segment was already finalized")
    new_version = current.version_number + 1
    replacement_id = str(uuid4())
    replacement = TranscriptSegment(
        id=replacement_id, session_id=session.id, sequence_number=current.sequence_number,
        version_number=new_version, start_offset_ms=current.start_offset_ms,
        end_offset_ms=current.end_offset_ms, speaker=current.speaker,
        original_synthetic_text=payload.original_synthetic_text,
        language_spans=[item.model_dump() for item in payload.language_spans],
        state=SegmentState.FINAL, capture_uncertainty=payload.capture_uncertainty,
        alternatives=payload.alternatives, correction_status="finalized_from_partial",
        is_current=True, provenance_pointer=f"consult-segment-{replacement_id}-v{new_version}",
    )
    db.add(replacement)
    db.flush()
    _derive_from_final_segment(db, session, replacement)
    add_trust_action_audit(
        db, actor=actor, action="consult_segment.finalized", entity_type="transcript_segment",
        entity_id=replacement.id, from_status="partial", to_status="final",
    )
    db.commit()
    db.refresh(replacement)
    return replacement


def confirm_capture(
    db: Session, capture: ClinicalCapture, selected_value: str, actor: CurrentUser
) -> ClinicalCapture:
    if capture.state != CaptureState.NEEDS_CONFIRMATION:
        raise HTTPException(status_code=409, detail="Capture is not awaiting confirmation")
    if selected_value not in capture.candidate_values:
        raise HTTPException(status_code=422, detail="Selected value must match a captured candidate")
    capture.state = CaptureState.CONFIRMED
    capture.confirmed_value = selected_value
    capture.confirmed_by = actor.user_id
    capture.confirmed_at = datetime.now(timezone.utc)
    add_trust_action_audit(
        db, actor=actor, action="clinical_capture.confirmed", entity_type="clinical_capture",
        entity_id=capture.id, from_status="needs_confirmation", to_status="confirmed",
    )
    db.commit()
    db.refresh(capture)
    return capture


def _finalize_session_transaction(db: Session, session: ConsultSession, actor: CurrentUser) -> list[ConsultSummary]:
    if session.state != ConsultState.RECEIVING:
        raise HTTPException(status_code=409, detail="Session must be receiving before finalization")
    segments = list(db.scalars(select(TranscriptSegment).where(
        TranscriptSegment.session_id == session.id,
        TranscriptSegment.is_current.is_(True),
        TranscriptSegment.state == SegmentState.FINAL,
    ).order_by(TranscriptSegment.sequence_number)))
    if not segments:
        raise HTTPException(status_code=422, detail="At least one finalized segment is required")
    session.state = ConsultState.FINALIZING
    captures = list(db.scalars(select(ClinicalCapture).where(
        ClinicalCapture.session_id == session.id,
        ClinicalCapture.state != CaptureState.SUPERSEDED,
    )))
    signals = list(db.scalars(select(ProvisionalSafetySignal).where(
        ProvisionalSafetySignal.session_id == session.id,
        ProvisionalSafetySignal.status != "superseded",
    )))
    pointers = [item.provenance_pointer for item in segments]
    confirmed = [f"{item.captured_term}: {item.confirmed_value}" for item in captures if item.state == CaptureState.CONFIRMED]
    unresolved = [f"{item.captured_term}: confirmation required" for item in captures if item.state == CaptureState.NEEDS_CONFIRMATION]
    clinician_content = "Clinician consult summary. " + "; ".join(
        (["Confirmed facts: " + ", ".join(confirmed)] if confirmed else [])
        + (["Unresolved uncertainty: " + ", ".join(unresolved)] if unresolved else [])
        + ([f"Provisional safety signals: {len(signals)} require review"] if signals else [])
    )
    if clinician_content.endswith(". "):
        clinician_content += "No confirmed structured facts; review source segments."
    clinician_entry = create_patient_entry(
        db, patient_id=session.patient_id, author_role=AuthorRole.SYSTEM,
        author_id="consult-rule-engine", entry_type=TimelineEntryType.AI_DOCTOR_CONSULT_SUMMARY,
        content=clinician_content, provenance_pointer=pointers[0], commit=False,
    )
    staff_content = "Staff action summary. Arrange clinician review for unresolved captures and safety signals. Confirm follow-up scheduling."
    staff_entry = create_patient_entry(
        db, patient_id=session.patient_id, author_role=AuthorRole.SYSTEM,
        author_id="consult-rule-engine", entry_type=TimelineEntryType.SYSTEM_EVENT,
        content=staff_content, provenance_pointer=pointers[0], commit=False,
    )
    patient_content = "Your care team reviewed this visit. Please follow up with your clinician before changing any medicine. Unconfirmed doses are not included."
    patient_entry = create_patient_entry(
        db, patient_id=session.patient_id, author_role=AuthorRole.CLINICIAN,
        author_id=actor.user_id, entry_type=TimelineEntryType.INSTRUCTION,
        content=patient_content, provenance_pointer=f"timeline-entry-{clinician_entry.id}",
        ai_derived=True, source_entry_id=clinician_entry.id, commit=False,
    )
    summaries = []
    for audience, entry in (
        (SummaryAudience.CLINICIAN, clinician_entry),
        (SummaryAudience.STAFF, staff_entry),
        (SummaryAudience.PATIENT, patient_entry),
    ):
        summary = ConsultSummary(
            id=str(uuid4()), session_id=session.id, audience=audience,
            generation_mode="rule_derived", timeline_entry_id=entry.id,
            source_provenance=pointers, source_status="current",
        )
        db.add(summary)
        summaries.append(summary)
    add_trust_action_audit(
        db, actor=actor, action="consult.finalized", entity_type="consult_session",
        entity_id=session.id, from_status="receiving", to_status="completed",
    )
    session.state = ConsultState.COMPLETED
    session.finalized_at = datetime.now(timezone.utc)
    db.commit()
    for summary in summaries:
        db.refresh(summary)
    logger.info("Synthetic consult finalized session_id=%s state=completed summary_count=3", session.id)
    return summaries


def finalize_session(db: Session, session: ConsultSession, actor: CurrentUser) -> list[ConsultSummary]:
    """Finalize all three audiences as one unit; failure closes the session safely."""
    try:
        return _finalize_session_transaction(db, session, actor)
    except HTTPException:
        raise
    except Exception:
        session_id = session.id
        db.rollback()
        failed = db.get(ConsultSession, session_id)
        if failed is not None and failed.state != ConsultState.COMPLETED:
            failed.state = ConsultState.FAILED
            failed.finalized_at = None
            db.commit()
        logger.error("Synthetic consult finalization failed safely session_id=%s", session_id)
        raise HTTPException(status_code=503, detail="Consult finalization failed safely")
