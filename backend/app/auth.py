from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from fastapi import Header, HTTPException, status


class UserRole(str, Enum):
    PATIENT = "patient"
    STAFF = "staff"
    CLINICIAN = "clinician"
    ADMIN = "admin"


@dataclass(frozen=True)
class CurrentUser:
    user_id: str
    role: UserRole
    clinic_id: str


def get_current_user(
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    x_role: Annotated[str | None, Header(alias="X-Role")] = None,
    x_clinic_id: Annotated[str | None, Header(alias="X-Clinic-Id")] = None,
) -> CurrentUser:
    if not x_user_id or not x_role or not x_clinic_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Development identity headers are required",
        )
    try:
        role = UserRole(x_role.lower())
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unsupported role",
        ) from error
    return CurrentUser(user_id=x_user_id, role=role, clinic_id=x_clinic_id)

