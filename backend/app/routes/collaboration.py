from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models import TaskStatus
from app.schemas import (
    CommentCreate,
    CommentRead,
    CommentResolutionUpdate,
    TaskAssignmentCreate,
    TaskAssignmentRead,
    TaskStatusUpdate,
)
from app.services.authorization_service import (
    require_entry_collaboration_access,
    require_internal_comments_access,
    require_patient_access,
)
from app.services.collaboration_service import (
    create_assignment,
    create_comment,
    extract_mentions,
    get_assignment,
    get_comment,
    get_entry_comments,
    get_patient_assignments,
    set_assignment_status,
    set_comment_resolved,
)
from app.services.patient_service import get_entry, get_patient

router = APIRouter(tags=["collaboration"])
DbSession = Annotated[Session, Depends(get_db)]
Identity = Annotated[CurrentUser, Depends(get_current_user)]


def _comment_read(comment) -> CommentRead:
    return CommentRead.model_validate(
        {**comment.__dict__, "mentions": extract_mentions(comment.content)}
    )


def _authorized_entry(entry_id: str, db: Session, user: CurrentUser):
    entry = get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    patient = get_patient(db, entry.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    require_entry_collaboration_access(user, entry)
    return entry


@router.get("/entries/{entry_id}/comments", response_model=list[CommentRead])
def read_comments(entry_id: str, db: DbSession, user: Identity) -> list[CommentRead]:
    _authorized_entry(entry_id, db, user)
    return [_comment_read(comment) for comment in get_entry_comments(db, entry_id)]


@router.post("/entries/{entry_id}/comments", response_model=CommentRead, status_code=201)
def add_comment(
    entry_id: str, payload: CommentCreate, db: DbSession, user: Identity
) -> CommentRead:
    entry = _authorized_entry(entry_id, db, user)
    try:
        comment = create_comment(
            db,
            entry=entry,
            user=user,
            content=payload.content,
            parent_comment_id=payload.parent_comment_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    return _comment_read(comment)


@router.patch("/comments/{comment_id}/resolution", response_model=CommentRead)
def update_comment_resolution(
    comment_id: str,
    payload: CommentResolutionUpdate,
    db: DbSession,
    user: Identity,
) -> CommentRead:
    comment = get_comment(db, comment_id)
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    _authorized_entry(comment.entry_id, db, user)
    return _comment_read(set_comment_resolved(db, comment, payload.resolved))


@router.get("/patients/{patient_id}/assignments", response_model=list[TaskAssignmentRead])
def read_assignments(
    patient_id: str,
    db: DbSession,
    user: Identity,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = TaskStatus.OPEN,
) -> list[TaskAssignmentRead]:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    require_internal_comments_access(user)
    return [
        TaskAssignmentRead.model_validate(assignment)
        for assignment in get_patient_assignments(db, patient_id, task_status)
    ]


@router.post(
    "/patients/{patient_id}/assignments",
    response_model=TaskAssignmentRead,
    status_code=201,
)
def add_assignment(
    patient_id: str,
    payload: TaskAssignmentCreate,
    db: DbSession,
    user: Identity,
) -> TaskAssignmentRead:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    require_internal_comments_access(user)
    if payload.entry_id is not None:
        entry = get_entry(db, payload.entry_id)
        if entry is None or entry.patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignment entry must belong to the patient",
            )
        require_entry_collaboration_access(user, entry)
    assignment = create_assignment(
        db,
        patient_id=patient_id,
        title=payload.title,
        entry_id=payload.entry_id,
        assigned_role=payload.assigned_role,
        assigned_user_id=payload.assigned_user_id,
    )
    return TaskAssignmentRead.model_validate(assignment)


@router.patch("/assignments/{assignment_id}", response_model=TaskAssignmentRead)
def update_assignment(
    assignment_id: str,
    payload: TaskStatusUpdate,
    db: DbSession,
    user: Identity,
) -> TaskAssignmentRead:
    assignment = get_assignment(db, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    patient = get_patient(db, assignment.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    require_internal_comments_access(user)
    return TaskAssignmentRead.model_validate(
        set_assignment_status(db, assignment, payload.status)
    )
