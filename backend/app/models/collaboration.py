from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class CollaborationRole(str, Enum):
    STAFF = "staff"
    CLINICIAN = "clinician"
    ADMIN = "admin"


class TaskStatus(str, Enum):
    OPEN = "open"
    COMPLETED = "completed"


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_entry_created", "entry_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entry_id: Mapped[str] = mapped_column(
        ForeignKey("timeline_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[str] = mapped_column(String(36), nullable=False)
    author_role: Mapped[CollaborationRole] = mapped_column(
        SqlEnum(
            CollaborationRole,
            values_callable=lambda roles: [role.value for role in roles],
            native_enum=False,
            create_constraint=True,
            name="comment_author_role",
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_comment_id: Mapped[str | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    entry: Mapped["TimelineEntry"] = relationship(back_populates="comments")  # noqa: F821
    parent: Mapped["Comment | None"] = relationship(
        back_populates="replies", remote_side="Comment.id"
    )
    replies: Mapped[list["Comment"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )


class TaskAssignment(Base):
    __tablename__ = "task_assignments"
    __table_args__ = (
        Index("ix_tasks_patient_status_created", "patient_id", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entry_id: Mapped[str | None] = mapped_column(
        ForeignKey("timeline_entries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    assigned_role: Mapped[CollaborationRole] = mapped_column(
        SqlEnum(
            CollaborationRole,
            values_callable=lambda roles: [role.value for role in roles],
            native_enum=False,
            create_constraint=True,
            name="task_assigned_role",
        ),
        nullable=False,
    )
    assigned_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        SqlEnum(
            TaskStatus,
            values_callable=lambda statuses: [task_status.value for task_status in statuses],
            native_enum=False,
            create_constraint=True,
            name="task_status",
        ),
        nullable=False,
        default=TaskStatus.OPEN,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="assignments")  # noqa: F821
    entry: Mapped["TimelineEntry | None"] = relationship(back_populates="assignments")  # noqa: F821

