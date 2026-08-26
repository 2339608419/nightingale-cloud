from fastapi import HTTPException, status

from app.auth import CurrentUser, UserRole
from app.models import AuthorRole, Highlight, Patient, TimelineEntry, TimelineEntryType


AI_ENTRY_TYPES = {
    TimelineEntryType.AI_DOCTOR_CONSULT_SUMMARY,
    TimelineEntryType.AI_NURSE_CONSULT_SUMMARY,
    TimelineEntryType.AI_PATIENT_SESSION_SUMMARY,
}
PATIENT_VISIBLE_TYPES = {TimelineEntryType.INSTRUCTION}
STAFF_VISIBLE_TYPES = {
    TimelineEntryType.CLINICIAN_NOTE,
    TimelineEntryType.STAFF_NOTE,
    TimelineEntryType.SYSTEM_EVENT,
    TimelineEntryType.INSTRUCTION,
    TimelineEntryType.ADMIN,
}


def require_patient_access(user: CurrentUser, patient: Patient) -> None:
    if user.clinic_id != patient.clinic_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient is outside the user's clinic scope",
        )
    if user.role == UserRole.PATIENT and user.user_id != patient.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients may access only their own record",
        )


def can_view_entry(user: CurrentUser, entry: TimelineEntry) -> bool:
    if user.role == UserRole.PATIENT:
        return entry.type in PATIENT_VISIBLE_TYPES
    if user.role == UserRole.STAFF:
        return entry.type in STAFF_VISIBLE_TYPES
    return user.role in {UserRole.CLINICIAN, UserRole.ADMIN}


def filter_visible_entries(
    user: CurrentUser, entries: list[TimelineEntry]
) -> list[TimelineEntry]:
    return [entry for entry in entries if can_view_entry(user, entry)]


def filter_visible_highlights(
    user: CurrentUser, highlights: list[Highlight]
) -> list[Highlight]:
    return [highlight for highlight in highlights if can_view_entry(user, highlight.entry)]


def require_internal_comments_access(user: CurrentUser) -> None:
    if user.role == UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Internal comments are not patient-visible",
        )


def require_ai_scribe_access(user: CurrentUser) -> None:
    if user.role not in {UserRole.STAFF, UserRole.CLINICIAN, UserRole.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role cannot ingest AI-scribed notes",
        )


def require_highlight_decision_access(user: CurrentUser) -> None:
    if user.role != UserRole.CLINICIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinicians can accept or reject highlights",
        )


def require_conflict_review_access(user: CurrentUser) -> None:
    if user.role not in {UserRole.CLINICIAN, UserRole.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinical conflicts are internal clinician review data",
        )


def require_conflict_resolution_access(user: CurrentUser) -> None:
    if user.role != UserRole.CLINICIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinicians can resolve clinical conflicts",
        )


def require_entry_collaboration_access(user: CurrentUser, entry: TimelineEntry) -> None:
    require_internal_comments_access(user)
    if not can_view_entry(user, entry):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role cannot collaborate on this entry",
        )


def author_role_for_new_entry(user: CurrentUser, entry_type: TimelineEntryType) -> AuthorRole:
    if user.role == UserRole.STAFF and entry_type == TimelineEntryType.STAFF_NOTE:
        return AuthorRole.STAFF
    if user.role == UserRole.CLINICIAN and entry_type in {
        TimelineEntryType.CLINICIAN_NOTE,
        TimelineEntryType.INSTRUCTION,
    }:
        return AuthorRole.CLINICIAN
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Role cannot create this note type",
    )


def require_entry_edit_access(user: CurrentUser, entry: TimelineEntry) -> None:
    allowed = (
        user.role == UserRole.STAFF
        and entry.author_role == AuthorRole.STAFF
        and entry.type == TimelineEntryType.STAFF_NOTE
    ) or (
        user.role == UserRole.CLINICIAN
        and entry.author_role == AuthorRole.CLINICIAN
        and entry.type in {TimelineEntryType.CLINICIAN_NOTE, TimelineEntryType.INSTRUCTION}
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role cannot edit this entry",
        )
