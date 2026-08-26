from datetime import datetime, timezone

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class ImportancePreference(Base):
    __tablename__ = "importance_preferences"
    __table_args__ = (UniqueConstraint("clinic_id", "category_type", "category_value"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    clinic_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category_type: Mapped[str] = mapped_column(String(30), nullable=False)
    category_value: Mapped[str] = mapped_column(String(50), nullable=False)
    accepted_count: Mapped[int] = mapped_column(nullable=False, default=0)
    rejected_count: Mapped[int] = mapped_column(nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
