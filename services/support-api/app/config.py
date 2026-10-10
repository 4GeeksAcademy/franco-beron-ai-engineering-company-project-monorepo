import os
from pathlib import Path

from dotenv import load_dotenv


SERVICE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(SERVICE_DIR / ".env")

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        os.getenv("ACCESS_TOKEN_MINUTES", os.getenv("JWT_EXPIRE_MINUTES", "120")),
    )
)
ACCESS_TOKEN_MINUTES = ACCESS_TOKEN_EXPIRE_MINUTES
FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://127.0.0.1:4174",
).rstrip("/")
BACKOFFICE_ORIGIN = os.getenv(
    "BACKOFFICE_ORIGIN",
    FRONTEND_URL,
)
SUPABASE_DATABASE_URL = os.getenv("SUPABASE_DATABASE_URL", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv(
    "EMAIL_FROM",
    "Nexova Ops <onboarding@resend.dev>",
)
