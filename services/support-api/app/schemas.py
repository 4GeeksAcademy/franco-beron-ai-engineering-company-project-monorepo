from datetime import date, datetime, timezone
from enum import Enum
import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
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
CentralIncidentCategory = Literal[
    "technical_failure",
    "process_error",
    "client_complaint",
    "candidate_issue",
    "staff_issue",
    "sla_breach",
    "data_quality",
    "other",
]
CentralIncidentStatus = Literal[
    "open",
    "in_progress",
    "resolved",
    "discarded",
]
CentralIncidentOrigin = Literal["customer", "branch", "internal"]
CentralIncidentBranch = Literal[
    "central",
    "valencia_operations",
    "miami_office",
    "remote",
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


class UserRole(str, Enum):
    admin = "admin"
    manager = "manager"
    user = "user"


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=80)
    address: str | None = Field(default=None, max_length=300)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña supera el límite permitido")
        return value

    @field_validator("name", "phone", "address")
    @classmethod
    def strip_profile_values(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean_value = value.strip()
        return clean_value or None


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str | None) -> str | None:
        if value is not None and len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña supera el límite permitido")
        return value

    @model_validator(mode="after")
    def has_changes(self):
        if not self.model_fields_set:
            raise ValueError("Se requiere al menos un campo para actualizar")
        return self


class ManagedUserPublic(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    role: UserRole
    created_at: datetime


class LoginUserPublic(BaseModel):
    id: int
    email: EmailStr
    name: str
    role: UserRole


class ProfilePublic(BaseModel):
    id: int
    user_id: int
    name: str | None = None
    phone: str | None = None
    address: str | None = None


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=80)
    address: str | None = Field(default=None, max_length=300)

    @field_validator("name", "phone", "address")
    @classmethod
    def strip_profile_values(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean_value = value.strip()
        return clean_value or None

    @model_validator(mode="after")
    def has_changes(self):
        if not self.model_fields_set:
            raise ValueError("Se requiere al menos un campo para actualizar")
        return self


class AuthMeResponse(BaseModel):
    id: int
    email: EmailStr
    role: UserRole
    profile: ProfilePublic


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: LoginUserPublic


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


class CentralIncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1)
    category: CentralIncidentCategory
    status: CentralIncidentStatus
    origin: CentralIncidentOrigin
    branch: CentralIncidentBranch

    @field_validator("title", "description")
    @classmethod
    def clean_required_text(cls, value: str, info) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise ValueError(f"{info.field_name} es obligatorio.")
        if info.field_name == "title" and len(clean_value) > 120:
            raise ValueError("El título admite hasta 120 caracteres.")
        return clean_value


class CentralIncidentStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: CentralIncidentStatus


class CentralIncidentPublic(BaseModel):
    id: int
    title: str
    description: str
    category: CentralIncidentCategory
    status: CentralIncidentStatus
    origin: CentralIncidentOrigin
    branch: CentralIncidentBranch
    created_at: datetime
    updated_at: datetime


class CentralIncidentSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    by_origin: dict[str, int]
    by_branch: dict[str, int]


Office = Literal["Valencia", "Miami"]
AssetCategory = Literal[
    "hardware",
    "peripherals",
    "office_supplies",
    "training_materials",
]


class AssetCreate(BaseModel):
    name: str = Field(min_length=1)
    sku: str = Field(min_length=1)
    category: AssetCategory
    office: Office

    @field_validator("name", "sku")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise ValueError("El campo es obligatorio")
        return clean_value


class AssetPublic(BaseModel):
    id: int
    name: str
    sku: str
    category: AssetCategory
    office: Office
    current_stock: int


class AssetEntryCreate(BaseModel):
    asset_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    supplier: str = Field(min_length=1)
    office: Office

    @field_validator("supplier")
    @classmethod
    def clean_supplier(cls, value: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise ValueError("supplier es obligatorio")
        return clean_value


class AssetEntryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    quantity: int
    supplier: str
    office: Office
    created_at: datetime
    user_uuid: str


class AssetExitCreate(BaseModel):
    asset_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    exit_type: Literal["allocation", "consumption"]
    assigned_to: str | None = None
    office: Office

    @model_validator(mode="after")
    def assigned_to_matches_exit_type(self):
        if self.exit_type == "allocation":
            if self.assigned_to is None or not self.assigned_to.strip():
                raise ValueError("assigned_to es obligatorio para allocation")
            self.assigned_to = self.assigned_to.strip()
        elif self.assigned_to is not None:
            raise ValueError("assigned_to debe ser null para consumption")
        return self


class AssetExitPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    quantity: int
    exit_type: Literal["allocation", "consumption"]
    assigned_to: str | None
    office: Office
    created_at: datetime
    user_uuid: str


class InventoryOrderPublic(BaseModel):
    id: int
    order_type: Literal["inbound", "outbound"]
    asset_id: int
    asset_name: str
    asset_sku: str
    quantity: int
    office: Office
    created_at: datetime
    user_uuid: str
    supplier: str | None = None
    exit_type: Literal["allocation", "consumption"] | None = None
    assigned_to: str | None = None


SupplierCountry = Literal["Spain", "USA"]
SupplierCurrency = Literal["EUR", "USD"]
SupplierStatus = Literal["active", "suspended"]
SupplierCategory = Literal[
    "job_boards",
    "ats_software",
    "assessment_tools",
    "training_platforms",
    "payroll_and_hr_software",
    "video_interview",
    "background_check",
    "office_and_facilities",
    "it_and_software_licenses",
]


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    country: SupplierCountry
    categories: list[SupplierCategory] = Field(min_length=1)
    monthly_rate: float = Field(gt=0, allow_inf_nan=False)
    currency: SupplierCurrency
    status: SupplierStatus
    contract_renewal_date: str | None = None
    contact_email: EmailStr | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def clean_supplier_name(cls, value: str) -> str:
        clean_value = value.strip()
        if not clean_value:
            raise ValueError("name es obligatorio")
        return clean_value

    @field_validator("contract_renewal_date")
    @classmethod
    def validate_renewal_date(cls, value: str | None) -> str | None:
        if value is not None:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError("contract_renewal_date debe usar YYYY-MM-DD")
            date.fromisoformat(value)
        return value

    @model_validator(mode="after")
    def currency_matches_country(self):
        expected_currency = "EUR" if self.country == "Spain" else "USD"
        if self.currency != expected_currency:
            raise ValueError(
                f"currency debe ser {expected_currency} para {self.country}"
            )
        return self


class SupplierRateUpdate(BaseModel):
    monthly_rate: float = Field(gt=0, allow_inf_nan=False)


class SupplierStatusUpdate(BaseModel):
    status: SupplierStatus


class SupplierPublic(BaseModel):
    id: int
    name: str
    country: SupplierCountry
    categories: list[SupplierCategory]
    monthly_rate: float
    currency: SupplierCurrency
    updated_at: datetime
    status: SupplierStatus
    contract_renewal_date: str | None = None
    contact_email: EmailStr | None = None
    notes: str | None = None
