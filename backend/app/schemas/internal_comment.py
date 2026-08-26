from pydantic import BaseModel


class InternalCommentRead(BaseModel):
    """Permission-boundary placeholder; comment persistence is intentionally deferred."""

    id: str
    content: str

