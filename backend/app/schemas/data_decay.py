from typing import Literal

from pydantic import BaseModel


class DataDecayPreviewRead(BaseModel):
    entry_id: str
    storage_tier: Literal["full_detail", "cold_summary"]
    display_content: str
    original_available: bool
    durable_exempt: bool
    reason: str
    provenance_pointer: str | None
