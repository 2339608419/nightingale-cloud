from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import CurrentUser, UserRole, get_current_user
from app.database import get_db
from app.models import SummaryAudience
from app.schemas import (
    ClinicalCaptureConfirm, ClinicalCaptureRead, ConsultSessionCreate,
    ConsultSessionRead, ConsultSummaryRead, SafetySignalRead,
    TranscriptSegmentCorrect, TranscriptSegmentCreate, TranscriptSegmentRead,
)
from app.schemas.timeline_entry import TimelineEntryRead
from app.services.authorization_service import require_patient_access
from app.services.clinic_scope_service import (
    get_consult_capture_in_clinic, get_consult_captures_in_clinic,
    get_consult_segment_in_clinic, get_consult_segments_in_clinic,
    get_consult_session_in_clinic, get_consult_signals_in_clinic,
    get_consult_summaries_in_clinic, get_entry_in_clinic, get_patient_in_clinic,
)
from app.services.consult_service import (
    append_segment, confirm_capture, correct_segment, create_session, finalize_partial_segment,
    finalize_session,
)


router = APIRouter(prefix="/consults", tags=["synthetic-consults"])
DbSession = Annotated[Session, Depends(get_db)]
Identity = Annotated[CurrentUser, Depends(get_current_user)]


def _require_internal(user: CurrentUser) -> None:
    if user.role == UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="Raw synthetic consult data is internal")


def _session(db: Session, session_id: str, user: CurrentUser):
    _require_internal(user)
    session = get_consult_session_in_clinic(db, session_id, user.clinic_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Consult session not found")
    patient = get_patient_in_clinic(db, session.patient_id, user.clinic_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Consult session not found")
    require_patient_access(user, patient)
    return session


def _summary_read(db: Session, item, clinic_id: str) -> ConsultSummaryRead:
    entry = get_entry_in_clinic(db, item.timeline_entry_id, clinic_id)
    if entry is None:
        raise HTTPException(status_code=409, detail="Consult summary source is unavailable")
    return ConsultSummaryRead(
        id=item.id, session_id=item.session_id, audience=item.audience,
        generation_mode=item.generation_mode, source_provenance=item.source_provenance,
        source_status=item.source_status, timeline_entry=TimelineEntryRead.model_validate(entry),
    )


@router.post("", response_model=ConsultSessionRead, status_code=201)
def start_consult(payload: ConsultSessionCreate, db: DbSession, user: Identity):
    _require_internal(user)
    if user.role not in {UserRole.CLINICIAN, UserRole.STAFF}:
        raise HTTPException(status_code=403, detail="Role cannot start a synthetic consult")
    patient = get_patient_in_clinic(db, payload.patient_id, user.clinic_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    require_patient_access(user, patient)
    return create_session(db, patient.id, user.clinic_id, payload.noise_profile)


@router.get("/{session_id}", response_model=ConsultSessionRead)
def read_consult(session_id: str, db: DbSession, user: Identity):
    return _session(db, session_id, user)


@router.post("/{session_id}/segments", response_model=TranscriptSegmentRead, status_code=201)
def add_segment(session_id: str, payload: TranscriptSegmentCreate, db: DbSession, user: Identity):
    session = _session(db, session_id, user)
    if user.role not in {UserRole.CLINICIAN, UserRole.STAFF}:
        raise HTTPException(status_code=403, detail="Role cannot append segments")
    return append_segment(db, session, payload)


@router.get("/{session_id}/segments", response_model=list[TranscriptSegmentRead])
def read_segments(session_id: str, db: DbSession, user: Identity):
    _session(db, session_id, user)
    return get_consult_segments_in_clinic(db, session_id, user.clinic_id)


@router.post("/{session_id}/segments/{segment_id}/correct", response_model=TranscriptSegmentRead)
def amend_segment(session_id: str, segment_id: str, payload: TranscriptSegmentCorrect, db: DbSession, user: Identity):
    session = _session(db, session_id, user)
    if user.role != UserRole.CLINICIAN:
        raise HTTPException(status_code=403, detail="Only clinicians can correct finalized segments")
    segment = get_consult_segment_in_clinic(db, segment_id, user.clinic_id)
    if segment is None or segment.session_id != session.id:
        raise HTTPException(status_code=404, detail="Segment not found")
    return correct_segment(db, session, segment, payload, user)


@router.post("/{session_id}/segments/{segment_id}/finalize", response_model=TranscriptSegmentRead)
def finalize_segment(session_id: str, segment_id: str, payload: TranscriptSegmentCorrect, db: DbSession, user: Identity):
    session = _session(db, session_id, user)
    if user.role not in {UserRole.CLINICIAN, UserRole.STAFF}:
        raise HTTPException(status_code=403, detail="Role cannot finalize transcript segments")
    segment = get_consult_segment_in_clinic(db, segment_id, user.clinic_id)
    if segment is None or segment.session_id != session.id:
        raise HTTPException(status_code=404, detail="Segment not found")
    return finalize_partial_segment(db, session, segment, payload, user)


@router.get("/{session_id}/signals", response_model=list[SafetySignalRead])
def read_signals(session_id: str, db: DbSession, user: Identity):
    _session(db, session_id, user)
    return get_consult_signals_in_clinic(db, session_id, user.clinic_id)


@router.get("/{session_id}/captures", response_model=list[ClinicalCaptureRead])
def read_captures(session_id: str, db: DbSession, user: Identity):
    _session(db, session_id, user)
    return get_consult_captures_in_clinic(db, session_id, user.clinic_id)


@router.post("/{session_id}/captures/{capture_id}/confirm", response_model=ClinicalCaptureRead)
def decide_capture(session_id: str, capture_id: str, payload: ClinicalCaptureConfirm, db: DbSession, user: Identity):
    _session(db, session_id, user)
    if user.role != UserRole.CLINICIAN:
        raise HTTPException(status_code=403, detail="Only clinicians can confirm clinical captures")
    capture = get_consult_capture_in_clinic(db, capture_id, user.clinic_id)
    if capture is None or capture.session_id != session_id:
        raise HTTPException(status_code=404, detail="Capture not found")
    return confirm_capture(db, capture, payload.selected_value, user)


@router.post("/{session_id}/finalize", response_model=list[ConsultSummaryRead])
def complete_consult(session_id: str, db: DbSession, user: Identity):
    session = _session(db, session_id, user)
    if user.role != UserRole.CLINICIAN:
        raise HTTPException(status_code=403, detail="Only clinicians can finalize consult summaries")
    summaries = finalize_session(db, session, user)
    return [_summary_read(db, item, user.clinic_id) for item in summaries]


@router.get("/{session_id}/summaries", response_model=list[ConsultSummaryRead])
def read_summaries(session_id: str, db: DbSession, user: Identity):
    _session(db, session_id, user)
    summaries = get_consult_summaries_in_clinic(db, session_id, user.clinic_id)
    if user.role == UserRole.STAFF:
        summaries = [item for item in summaries if item.audience == SummaryAudience.STAFF]
    return [_summary_read(db, item, user.clinic_id) for item in summaries]
