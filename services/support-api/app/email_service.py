from html import escape
from urllib.parse import quote

import resend

from app.config import EMAIL_FROM, FRONTEND_URL, RESEND_API_KEY


def send_password_reset_email(to_email: str, token: str) -> None:
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY no está configurada")

    resend.api_key = RESEND_API_KEY
    reset_url = (
        f"{FRONTEND_URL}/?reset_token="
        f"{quote(token, safe='')}"
    )
    safe_reset_url = escape(reset_url, quote=True)

    message = {
            "from": EMAIL_FROM,
            "to": [to_email],
            "subject": "Restablecer contraseña de Nexova Ops",
            "html": f"""
                <h2>Restablecer contraseña</h2>
                <p>Recibimos una solicitud para restablecer el acceso a Nexova Ops.</p>
                <p>El enlace vence en 30 minutos y solo puede utilizarse una vez.</p>
                <p><a href="{safe_reset_url}">Crear una nueva contraseña</a></p>
                <p>Si no solicitaste el cambio, ignora este correo.</p>
            """,
        }
    try:
        resend.Emails.send(message)
    except Exception:
        raise RuntimeError("No se pudo entregar el correo de recuperación. Inténtalo más tarde.") from None
