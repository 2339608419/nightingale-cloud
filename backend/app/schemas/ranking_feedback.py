from pydantic import BaseModel, Field


class ExposureCreate(BaseModel):
    display_reference: str = Field(pattern=r"^[A-Za-z0-9_-]{8,100}$")


class ExposureRead(BaseModel):
    recorded: bool


class FeedbackPolicyRead(BaseModel):
    positive_weight: float
    negative_weight: float
    negative_independent_clinician_threshold: int
    minimum_adjustment: float
    maximum_adjustment: float
    negative_feedback_state: str
    explanation: list[str]


class TrustMetricsRead(BaseModel):
    eligible_candidate_count: int
    exposed_count: int
    unexposed_count: int
    decided_count: int
    undecided_exposed_count: int
    feedback_undone_count: int
    negative_feedback_suppressed_count: int
    negative_feedback_applied_count: int
    safety_floor_protected_count: int
    metric_purpose: str
