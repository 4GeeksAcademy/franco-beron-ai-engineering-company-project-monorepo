from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
import logging

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from tinydb import Query as TinyQuery

from app.auth import get_current_user
from app.config import BACKOFFICE_ORIGIN
from app.database import initialize_inventory_database
from app.db import incidents, reset_tokens, users
from app.email_service import send_password_reset_email
from app.incident_rules import (
    VALID_CATEGORIES,
    VALID_STATUSES,
    generate_ticket_id,
    validate_incident_data,
)
from app.schemas import (
    AuthMeResponse,
    ChangePasswordRequest,
    IncidentCreate,
    IncidentPublic,
    IncidentStatusUpdate,
    IncidentSummary,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    ResetPasswordRequest,
)
from app.routers.inventory import router as inventory_router
from app.routers.incidents import router as central_incidents_router
from app.routers.profiles import router as profiles_router
from app.routers.suppliers import router as suppliers_router
from app.routers.users import router as users_router
from app.user_service import (
    ensure_profile,
    get_user_by_email,
    normalize_user_record,
    public_profile,
)
from app.security import (
    create_access_token,
    create_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_inventory_database()
    yield


app = FastAPI(title="Nexova Support API", lifespan=lifespan)
app.include_router(inventory_router)
app.include_router(central_incidents_router)
app.include_router(suppliers_router)
app.include_router(users_router)
app.include_router(profiles_router)
logger = logging.getLogger(__name__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[BACKOFFICE_ORIGIN],
    allow_origin_regex=r"https://[a-zA-Z0-9-]+-4174\.app\.github\.dev",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

UserQuery = TinyQuery()
IncidentQuery = TinyQuery()
ResetQuery = TinyQuery()


@app.exception_handler(RequestValidationError)
async def request_validation_handler(
    request: Request,
    exc: RequestValidationError,
):
    first_error = exc.errors()[0]
    location = first_error.get("loc", [])
    is_central_incident = request.url.path.startswith("/api/incidents")
    validation_status = (
        status.HTTP_422_UNPROCESSABLE_ENTITY
        if request.url.path == "/suppliers"
        or request.url.path.startswith("/suppliers/")
        else status.HTTP_400_BAD_REQUEST
    )
    validation_message = first_error.get("msg", "Dato inválido")
    if is_central_incident:
        validation_message = (
            f"{location[-1]} es obligatorio."
            if first_error.get("type") == "missing" and location
            else "El valor no es válido. Revisa el campo indicado."
        )
    return JSONResponse(
        status_code=validation_status,
        content={
            "error": "validation_error",
            "field": str(location[-1]) if location else "unknown",
            "message": validation_message,
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(
    request: Request,
    exc: Exception,
):
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "Ocurrió un error inesperado.",
        },
    )


def public_user(user) -> dict:
    user = normalize_user_record(user)
    profile = ensure_profile(user.doc_id)
    return {
        "id": user.doc_id,
        "email": user["email"],
        "name": profile.get("name") or "",
        "role": user.get("role", "user"),
    }


def password_hash_for(user) -> str:
    return user.get("hashed_password", user.get("password_hash", ""))


def update_password_hash(user, password: str):
    field = "hashed_password" if "hashed_password" in user else "password_hash"
    users.update({field: hash_password(password)}, doc_ids=[user.doc_id])


def public_incident(incident) -> dict:
    return {
        "id": incident.doc_id,
        "ticket_id": incident["ticket_id"],
        "date": incident["date"],
        "client_company": incident["client_company"],
        "category": incident["category"],
        "description": incident["description"],
        "agent_id": incident["agent_id"],
        "status": incident["status"],
        "satisfaction_score": incident.get("satisfaction_score"),
        "reported_by_user_id": incident["reported_by_user_id"],
        "created_at": incident["created_at"],
        "updated_at": incident["updated_at"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    user = get_user_by_email(str(payload.email))

    if not user or not verify_password(
        payload.password,
        password_hash_for(user),
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
        )
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
        )

    return {
        "access_token": create_access_token(user.doc_id),
        "token_type": "bearer",
        "user": public_user(user),
    }


@app.get("/auth/me", response_model=AuthMeResponse)
def me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.doc_id,
        "email": current_user["email"],
        "role": current_user.get("role", "user"),
        "profile": public_profile(ensure_profile(current_user.doc_id)),
    }


@app.post("/auth/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    current_user=Depends(get_current_user),
):
    if not verify_password(
        payload.current_password,
        password_hash_for(current_user),
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta.",
        )

    update_password_hash(current_user, payload.new_password)
    outstanding_tokens = reset_tokens.search(
        (ResetQuery.user_id == current_user.doc_id)
        & (ResetQuery.used == False)
    )
    for reset_token in outstanding_tokens:
        reset_tokens.update(
            {"used": True},
            doc_ids=[reset_token.doc_id],
        )

    return {"message": "La contraseña se actualizó correctamente."}


@app.post("/auth/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest):
    generic_message = (
        "Si la cuenta está registrada, recibirá un enlace para restablecer la contraseña."
    )
    matches = users.search(
        UserQuery.email == str(payload.email).lower()
    )
    if not matches:
        return {"message": generic_message}

    user = matches[0]
    now = datetime.now(timezone.utc)
    previous_tokens = reset_tokens.search(
        (ResetQuery.user_id == user.doc_id)
        & (ResetQuery.used == False)
    )
    for previous_token in previous_tokens:
        reset_tokens.update(
            {"used": True},
            doc_ids=[previous_token.doc_id],
        )

    raw_token = create_reset_token()
    reset_token_id = reset_tokens.insert(
        {
            "user_id": user.doc_id,
            "token_hash": hash_reset_token(raw_token),
            "expires_at": (now + timedelta(minutes=30)).isoformat(),
            "used": False,
        }
    )

    try:
        send_password_reset_email(
            to_email=user["email"],
            token=raw_token,
        )
    except Exception:
        reset_tokens.update(
            {"used": True},
            doc_ids=[reset_token_id],
        )
        logger.warning("No se pudo entregar un correo de recuperación.")

    return {"message": generic_message}


@app.post("/auth/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest):
    token_hash = hash_reset_token(payload.token)
    matches = reset_tokens.search(
        ResetQuery.token_hash == token_hash
    )
    invalid_message = "El enlace de recuperación no es válido o expiró."
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=invalid_message,
        )

    reset_token = matches[0]
    if reset_token.get("used") is True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=invalid_message,
        )

    expires_at = datetime.fromisoformat(reset_token["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        reset_tokens.update(
            {"used": True},
            doc_ids=[reset_token.doc_id],
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=invalid_message,
        )

    user = users.get(doc_id=reset_token["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=invalid_message,
        )

    update_password_hash(user, payload.new_password)
    outstanding_tokens = reset_tokens.search(
        (ResetQuery.user_id == user.doc_id)
        & (ResetQuery.used == False)
    )
    for outstanding_token in outstanding_tokens:
        reset_tokens.update(
            {"used": True},
            doc_ids=[outstanding_token.doc_id],
        )

    return {"message": "La contraseña se actualizó correctamente."}


@app.post(
    "/api/tickets",
    response_model=IncidentPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_incident(
    payload: IncidentCreate,
    current_user=Depends(get_current_user),
):
    clean_data = validate_incident_data(
        payload.model_dump(),
    )
    now = datetime.now(timezone.utc).isoformat()
    ticket_id = generate_ticket_id(
        [item["ticket_id"] for item in incidents.all()]
    )
    incident_id = incidents.insert(
        {
            **clean_data,
            "ticket_id": ticket_id,
            "customer_email": str(payload.customer_email).lower(),
            "reported_by_user_id": current_user.doc_id,
            "created_at": now,
            "updated_at": now,
        }
    )
    created = incidents.get(doc_id=incident_id)
    return public_incident(created)


@app.get(
    "/api/tickets",
    response_model=list[IncidentPublic],
)
def list_incidents(
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = None,
    current_user=Depends(get_current_user),
):
    if status_filter is not None and status_filter not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail={"error": "validation_error", "field": "status", "message": "status no es válido"},
        )
    if category is not None and category not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail={"error": "validation_error", "field": "category", "message": "category no es válida"},
        )

    records = incidents.all()
    if status_filter:
        records = [item for item in records if item["status"] == status_filter]
    if category:
        records = [item for item in records if item["category"] == category]

    return [public_incident(item) for item in records]


@app.get(
    "/api/tickets/summary",
    response_model=IncidentSummary,
)
def incidents_summary(current_user=Depends(get_current_user)):
    records = incidents.all()
    by_status = {key: 0 for key in VALID_STATUSES}
    by_category = {key: 0 for key in VALID_CATEGORIES}
    closed_scores = []

    for item in records:
        by_status[item["status"]] += 1
        by_category[item["category"]] += 1
        if item["status"] == "CLOSED" and item.get("satisfaction_score") is not None:
            closed_scores.append(item["satisfaction_score"])

    return {
        "total": len(records),
        "by_status": by_status,
        "by_category": by_category,
        "closed_scored": len(closed_scores),
        "average_satisfaction": (
            round(sum(closed_scores) / len(closed_scores), 2)
            if closed_scores
            else None
        ),
    }


@app.get(
    "/api/tickets/{ticket_id}",
    response_model=IncidentPublic,
)
def get_incident(
    ticket_id: str,
    current_user=Depends(get_current_user),
):
    matches = incidents.search(IncidentQuery.ticket_id == ticket_id)
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Ticket no encontrado."},
        )
    return public_incident(matches[0])


@app.patch(
    "/api/tickets/{ticket_id}/status",
    response_model=IncidentPublic,
)
def update_incident_status(
    ticket_id: str,
    payload: IncidentStatusUpdate,
    current_user=Depends(get_current_user),
):
    matches = incidents.search(IncidentQuery.ticket_id == ticket_id)
    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Ticket no encontrado."},
        )

    incident = matches[0]
    changes = {
        "status": payload.status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if payload.status == "CLOSED":
        changes["satisfaction_score"] = payload.satisfaction_score
    elif payload.satisfaction_score is not None:
        changes["satisfaction_score"] = payload.satisfaction_score

    incidents.update(changes, doc_ids=[incident.doc_id])
    return public_incident(incidents.get(doc_id=incident.doc_id))
