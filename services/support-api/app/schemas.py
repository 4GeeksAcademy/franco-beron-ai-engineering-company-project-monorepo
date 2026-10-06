from datetime import date
import re
from typing import Literal

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


IncidentCategory = Literal[
    "TECHNICAL",
    "BILLING",
    "ACCESS",
    "HR_QUERY",
    "COMPLAINT",
]
IncidentStatus = Literal[
    "OPEN",
    "CLOSED",
    "DISCARDED",
]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña supera el límite permitido")
        return value


class UserPublic(BaseModel):
    id: int
    email: EmailStr
    name: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserPublic


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña supera el límite permitido")
        return value


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña supera el límite permitido")
        return value


class MessageResponse(BaseModel):
    message: str


class IncidentCreate(BaseModel):
    date: date
    client_company: str = Field(min_length=1)
    category: IncidentCategory
    description: str = Field(min_length=5)
    agent_id: str = Field(pattern=r"^AGT-\d{2}$")
    status: IncidentStatus = "OPEN"
    customer_email: EmailStr
    satisfaction_score: int | None = Field(default=None, ge=1, le=5)

    @field_validator("date", mode="before")
    @classmethod
    def require_iso_date(cls, value):
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("date debe usar formato YYYY-MM-DD")
        return value

    @field_validator("client_company")
    @classmethod
    def clean_company(cls, value: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise ValueError("client_company es obligatorio")
        return clean_value

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        clean_value = value.strip()
        if len(clean_value) < 5:
            raise ValueError("description debe tener al menos 5 caracteres")
        return clean_value

    @field_validator("agent_id")
    @classmethod
    def clean_agent_id(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def closed_ticket_has_score(self):
        if self.status == "CLOSED" and self.satisfaction_score is None:
            raise ValueError("CLOSED requiere satisfaction_score")
        return self


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    satisfaction_score: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def closed_ticket_has_score(self):
        if self.status == "CLOSED" and self.satisfaction_score is None:
            raise ValueError("CLOSED requiere satisfaction_score")
        return self


class IncidentPublic(BaseModel):
    id: int
    ticket_id: str
    date: date
    client_company: str
    category: IncidentCategory
    description: str
    agent_id: str
    status: IncidentStatus
    satisfaction_score: int | None
    reported_by_user_id: int
    created_at: str
    updated_at: str


class IncidentSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    closed_scored: int
    average_satisfaction: float | None
