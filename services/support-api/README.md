# Nexova Support API

API privada para el backoffice de soporte. Sigue el patrón de autenticación del proyecto `monorepo-auth`, adaptado al esquema y las restricciones de `CONTEXT.md`.

## Alcance

- Autenticación JWT con `OAuth2PasswordBearer`, `python-jose` y `libpass[bcrypt]`; el alta mediante `POST /users` requiere una sesión válida y el backoffice no incorpora una pantalla pública de registro.
- `User` y `Profile` se guardan únicamente en TinyDB. Los roles válidos son `admin`, `manager` y `user`; el alta asigna `user` por defecto.
- `scripts/create_user.py` continúa disponible para provisionar cuentas directamente en TinyDB, asignar un rol controlado y crear su perfil inicial.
- Gestión de inventario con SQLModel y Supabase/PostgreSQL; TinyDB también almacena tickets y proveedores.
- Directorio de proveedores Nexova persistido en la tabla TinyDB `suppliers`.
- Tickets con categorías `TECHNICAL`, `BILLING`, `ACCESS`, `HR_QUERY` y `COMPLAINT`.
- Estados `OPEN`, `CLOSED` y `DISCARDED`; un ticket `CLOSED` requiere puntuación de satisfacción entre 1 y 5.
- `customer_email` se valida y persiste, pero se excluye de las respuestas y no se registra en logs.
- No se carga un CSV de muestra: el dataset real no está presente en el repositorio.

## Ejecución con Docker

Desde la raiz del repositorio, crea `.env` a partir de la plantilla si todavia no existe y define un `JWT_SECRET` local largo:

```bash
cp .env.example .env
docker compose up
```

La API queda disponible en `http://localhost:8001` con recarga en caliente. El backoffice se comunica mediante el proxy de Next y el host Docker `backend`, no mediante `localhost` dentro de la red de contenedores.

## Ejecución sin Docker

Desde esta carpeta:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../../.env.example .env
```

Reemplaza `JWT_SECRET` en `.env` con un secreto aleatorio largo. Luego crea una cuenta interna y arranca la API:

Añade también estas variables a `.env`; usa una clave de Resend recién generada y nunca la subas a Git:

```env
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
FRONTEND_URL=http://127.0.0.1:3001
BACKOFFICE_ORIGIN=http://127.0.0.1:3001
RESEND_API_KEY=re_replace_with_your_new_resend_key
EMAIL_FROM=Nexova Ops <onboarding@resend.dev>
SUPABASE_DATABASE_URL=postgresql://postgres.radocsbpprqanytbupmo:<URL_ENCODED_PASSWORD>@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

`onboarding@resend.dev` sirve para pruebas limitadas de Resend. Para el uso normal, configura un remitente de un dominio verificado en Resend. Reinicia Uvicorn después de editar `.env`.

Para Docker, define también `SUPABASE_DATABASE_URL` en el `.env` de la raíz. El ejemplo usa el shared pooler en modo transaccional (puerto `6543`); reemplaza `<URL_ENCODED_PASSWORD>` con la contraseña real, codificando caracteres reservados como `%40` para `@`. No guardes la URI en Git. Psycopg desactiva prepared statements para compatibilidad con el pooler. Sin esta variable la API y la autenticación siguen disponibles, pero los endpoints de inventario responden `503`. Al iniciar con la URI configurada, la API crea las tablas y carga las semillas de desarrollo mediante `SQLModel.metadata.create_all()`.

```bash
python -m scripts.create_user
uvicorn app.main:app --reload --port 8001
```

Swagger local: `http://127.0.0.1:8001/docs`.

## API

- `POST /users` (requiere JWT; rol predeterminado `user`)
- `GET /users` (requiere rol `admin`)
- `GET /users/{user_id}`, `PUT /users/{user_id}`, `DELETE /users/{user_id}` (propietario o admin; el rol/estado solo lo cambia un admin)
- `GET /profiles/me`, `PUT /profiles/me` (JWT)
- `POST /auth/login`
- `GET /auth/me` (email, rol y perfil)
- `POST /auth/change-password` (requiere JWT y contraseña actual)
- `POST /auth/forgot-password`
- `POST /auth/reset-password`
- `POST /api/incidents`
- `GET /api/incidents?status=OPEN&category=TECHNICAL`
- `GET /api/incidents/summary`
- `GET /api/incidents/{ticket_id}`
- `PATCH /api/incidents/{ticket_id}/status`
- `POST /suppliers`
- `GET /suppliers?country=Spain&category=ats_software`
- `GET /suppliers/{id}`
- `PATCH /suppliers/{id}/rate`
- `PATCH /suppliers/{id}/status`
- `DELETE /suppliers/{id}`

Todos los endpoints de `/users`, `/profiles`, `/suppliers`, `/inventory` e incidencias requieren autenticación. Las excepciones públicas son `/health`, `/auth/login`, `/auth/forgot-password` y `/auth/reset-password`.

La clave de firma se lee desde `JWT_SECRET`; la expiración se configura con `ACCESS_TOKEN_EXPIRE_MINUTES` (se conserva `ACCESS_TOKEN_MINUTES` como alias compatible). Los JWT llevan el ID de documento TinyDB en `sub`. Las cuentas legacy se migran al autenticarse: `password_hash` pasa a `hashed_password` y `name` se mueve a su perfil. Las credenciales y perfiles no se guardan en PostgreSQL/Supabase.

Se puede filtrar productos u órdenes por `office=Valencia` o `office=Miami`. El stock se calcula como entradas menos salidas y nunca se almacena en `Asset`. Las salidas no pueden dejar stock negativo.

El router incluye productos, entradas y salidas con `user_uuid` del usuario TinyDB autenticado. Las cuentas existentes reciben su UUID cuando registran su primer movimiento; las nuevas lo reciben al crearse. Los movimientos de muestra usan un UUID reservado de sistema. Las semillas incluyen seis assets, cinco entradas y tres salidas y se mantienen idempotentes entre reinicios.

Las tablas SQLModel y las schemas Pydantic están separadas en `app/models.py` y `app/schemas.py`; la sesión PostgreSQL se inyecta por request desde `app/database.py`. `create_all()` es adecuado para este hito de desarrollo; producción requiere migraciones.

### Directorio de proveedores

El directorio implementa `Supplier` con los campos y valores de `CONTEXT-nexova`: país `Spain`/`USA`, categorías válidas, tarifa positiva, moneda obligatoria por país, estado `active`/`suspended`, fecha opcional de renovación, email de contacto y notas. `updated_at` se genera en el alta y se actualiza automáticamente al cambiar `monthly_rate`.

Para cargar los 15 proveedores iniciales, desde `services/support-api/` ejecuta:

```bash
uv run seed
```

El seeder usa la misma tabla TinyDB `suppliers`, evita duplicados por nombre e informa cuántos insertó y cuántos ya existían. La tabla persiste en `db.json`, que permanece ignorado por Git.

La recuperación devuelve la misma respuesta tanto si la cuenta existe como si no. Los tokens se guardan hasheados, vencen en 30 minutos y solo se aceptan una vez. El correo se envía a la cuenta interna; no se usa `customer_email` para recuperación.

## Pruebas

```bash
python -m unittest discover -s tests
```
