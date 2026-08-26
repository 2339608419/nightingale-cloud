from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.collaboration import CollaborationRole, TaskStatus


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    parent_comment_id: str | None = None


class CommentResolutionUpdate(BaseModel):
    resolved: bool


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entry_id: str
    author_id: str
    author_role: CollaborationRole
    content: str
    parent_comment_id: str | None
    resolved: bool
    created_at: datetime
    mentions: list[str]


class TaskAssignmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    entry_id: str | None = None
    assigned_role: CollaborationRole
    assigned_user_id: str | None = Field(default=None, max_length=36)


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    entry_id: str | None
    title: str
    assigned_role: CollaborationRole
    assigned_user_id: str | None
    status: TaskStatus
    created_at: datetime
    resolved_at: datetime | None

