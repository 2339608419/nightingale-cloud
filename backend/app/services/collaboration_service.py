import re
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import (
    CollaborationRole,
    Comment,
    TaskAssignment,
    TaskStatus,
    TimelineEntry,
)


MENTION_PATTERN = re.compile(
    r"(?<![\w@])@([A-Za-z0-9_](?:[A-Za-z0-9_.-]{0,62}[A-Za-z0-9_])?)"
)


def extract_mentions(content: str) -> list[str]:
    return list(dict.fromkeys(match.group(1) for match in MENTION_PATTERN.finditer(content)))


def get_entry_comments(db: Session, entry_id: str) -> list[Comment]:
    statement = (
        select(Comment)
        .where(Comment.entry_id == entry_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
    )
    return list(db.scalars(statement))


def get_comment(db: Session, comment_id: str) -> Comment | None:
    return db.get(Comment, comment_id)


def create_comment(
    db: Session,
    *,
    entry: TimelineEntry,
    user: CurrentUser,
    content: str,
    parent_comment_id: str | None,
) -> Comment:
    if parent_comment_id is not None:
        parent = db.get(Comment, parent_comment_id)
        if parent is None or parent.entry_id != entry.id:
            raise ValueError("Parent comment must belong to the same entry")
    comment = Comment(
        id=str(uuid4()),
        entry_id=entry.id,
        author_id=user.user_id,
        author_role=CollaborationRole(user.role.value),
        content=content,
        parent_comment_id=parent_comment_id,
        resolved=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def set_comment_resolved(db: Session, comment: Comment, resolved: bool) -> Comment:
    comment.resolved = resolved
    db.commit()
    db.refresh(comment)
    return comment


def get_patient_assignments(
    db: Session, patient_id: str, task_status: TaskStatus | None = None
) -> list[TaskAssignment]:
    statement = select(TaskAssignment).where(TaskAssignment.patient_id == patient_id)
    if task_status is not None:
        statement = statement.where(TaskAssignment.status == task_status)
    statement = statement.order_by(TaskAssignment.created_at.asc(), TaskAssignment.id.asc())
    return list(db.scalars(statement))


def get_assignment(db: Session, assignment_id: str) -> TaskAssignment | None:
    return db.get(TaskAssignment, assignment_id)


def create_assignment(
    db: Session,
    *,
    patient_id: str,
    title: str,
    entry_id: str | None,
    assigned_role: CollaborationRole,
    assigned_user_id: str | None,
) -> TaskAssignment:
    assignment = TaskAssignment(
        id=str(uuid4()),
        patient_id=patient_id,
        entry_id=entry_id,
        title=title,
        assigned_role=assigned_role,
        assigned_user_id=assigned_user_id,
        status=TaskStatus.OPEN,
        created_at=datetime.now(timezone.utc),
        resolved_at=None,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def set_assignment_status(
    db: Session, assignment: TaskAssignment, task_status: TaskStatus
) -> TaskAssignment:
    assignment.status = task_status
    assignment.resolved_at = (
        datetime.now(timezone.utc) if task_status == TaskStatus.COMPLETED else None
    )
    db.commit()
    db.refresh(assignment)
    return assignment
