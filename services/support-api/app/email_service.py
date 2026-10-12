from html import escape
from urllib.parse import quote

import resend

from app.config import EMAIL_FROM, FRONTEND_URL, RESEND_API_KEY


def send_password_reset_email(to_email: str, token: str) -> None:
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY no está configurada")

    resend.api_key = RESEND_API_KEY
    reset_url = (
        f"{FRONTEND_URL}/reset-password?token="
        f"{quote(token, safe='')}"
    )
    safe_reset_url = escape(reset_url, quote=True)

    message = {
        "from": EMAIL_FROM,
        "to": [to_email],
        "subject": "Restablecer contraseña de Nexova Ops",
        # Estilos en línea, layout de tabla y botón de gran tamaño: legible en móvil
        # y en clientes de correo que ignoran CSS externo.
        "html": f"""
        <!doctype html>
        <html lang="es" xmlns="http://www.w3.org/1999/xhtml">
        <body style="margin:0;padding:0;background-color:#eef1f0;font-family:Arial,Helvetica,sans-serif;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                 style="background-color:#eef1f0;padding:24px 12px;box-sizing:border-box;">
            <tr>
              <td align="center">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                       style="max-width:560px;background-color:#ffffff;border-radius:12px;padding:32px 24px;box-sizing:border-box;">
                  <tr>
                    <td>
                      <p style="margin:0 0 20px;font-size:20px;font-weight:bold;color:#17201f;">
                        Nexova Ops
                      </p>
                      <h1 style="margin:0 0 12px;font-size:24px;line-height:1.3;color:#17201f;">
                        Restablecer contraseña
                      </h1>
                      <p style="margin:0 0 16px;font-size:16px;line-height:1.5;color:#33413e;">
                        Recibimos una solicitud para restablecer el acceso a Nexova Ops.
                        Este enlace vence en 30 minutos y solo puede utilizarse una vez.
                      </p>
                      <table role="presentation" cellpadding="0" cellspacing="0" style="margin:24px 0;">
                        <tr>
                          <td align="center" style="border-radius:8px;background-color:#17201f;">
                            <a href="{safe_reset_url}"
                               style="display:inline-block;padding:14px 28px;border-radius:8px;
                                      background-color:#17201f;color:#ffffff;
                                      font-size:16px;font-weight:bold;text-decoration:none;">
                              Crear una nueva contraseña
                            </a>
                          </td>
                        </tr>
                      </table>
                      <p style="margin:16px 0 0;font-size:14px;line-height:1.5;color:#5b6b67;">
                        ¿No puedes pulsar el botón? Copia esta dirección en tu navegador:
                        <br/>
                        <span style="word-break:break-all;color:#17201f;">{safe_reset_url}</span>
                      </p>
                      <hr style="border:none;border-top:1px solid #e3e8e6;margin:24px 0;" />
                      <p style="margin:0;font-size:14px;line-height:1.5;color:#5b6b67;">
                        Si no solicitaste este cambio, ignora este correo y tu contraseña
                        seguirá siendo la misma.
                      </p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </body>
        </html>
        """,
    }
    try:
        resend.Emails.send(message)
    except Exception:
        raise RuntimeError("No se pudo entregar el correo de recuperación. Inténtalo más tarde.") from None
