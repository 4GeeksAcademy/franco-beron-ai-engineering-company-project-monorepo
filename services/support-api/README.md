# Nexova Support API

API privada para el backoffice de soporte. Sigue el patrón de autenticación del proyecto `monorepo-auth`, adaptado al esquema y las restricciones de `CONTEXT.md`.

## Alcance

- Login interno con bcrypt y JWT. No existe registro público.
- Las cuentas se crean de forma administrada con `scripts/create_user.py`.
- Tickets con categorías `TECHNICAL`, `BILLING`, `ACCESS`, `HR_QUERY` y `COMPLAINT`.
- Estados `OPEN`, `CLOSED` y `DISCARDED`; un ticket `CLOSED` requiere puntuación de satisfacción entre 1 y 5.
- `customer_email` se valida y persiste, pero se excluye de las respuestas y no se registra en logs.
- No se carga un CSV de muestra: el dataset real no está presente en el repositorio.

## Ejecución

Desde esta carpeta:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Reemplaza `JWT_SECRET` en `.env` con un secreto aleatorio largo. Luego crea una cuenta interna y arranca la API:

Añade también estas variables a `.env`; usa una clave de Resend recién generada y nunca la subas a Git:

```env
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=120
FRONTEND_URL=http://127.0.0.1:4174
BACKOFFICE_ORIGIN=http://127.0.0.1:4174
RESEND_API_KEY=re_replace_with_your_new_resend_key
EMAIL_FROM=Nexova Ops <onboarding@resend.dev>
```

`onboarding@resend.dev` sirve para pruebas limitadas de Resend. Para el uso normal, configura un remitente de un dominio verificado en Resend. Reinicia Uvicorn después de editar `.env`.

```bash
python -m scripts.create_user
uvicorn app.main:app --reload --port 8001
```

Swagger local: `http://127.0.0.1:8001/docs`.

## API

- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/change-password` (requiere JWT y contraseña actual)
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `POST /api/incidents`
- `GET /api/incidents?status=OPEN&category=TECHNICAL`
- `GET /api/incidents/summary`
- `GET /api/incidents/{ticket_id}`
- `PATCH /api/incidents/{ticket_id}/status`

Todos los endpoints salvo `/health`, `/auth/login`, `/auth/forgot-password` y `/auth/reset-password` requieren `Authorization: Bearer <JWT>`.

La recuperación devuelve la misma respuesta tanto si la cuenta existe como si no. Los tokens se guardan hasheados, vencen en 30 minutos y solo se aceptan una vez. El correo se envía a la cuenta interna; no se usa `customer_email` para recuperación.

## Pruebas

```bash
python -m unittest discover -s tests
```
