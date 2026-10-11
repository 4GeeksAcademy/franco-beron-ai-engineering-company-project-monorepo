# Technical Context — Monorepo Nexova

## Estado técnico real del repositorio

- Repositorio monorepo base de AI Engineering (4Geeks Academy).
- No existe orquestador de workspaces en raíz (sin `package.json` raíz, sin `pnpm-workspace.yaml`, sin `turbo.json`, sin `nx.json`).
- Existe un paquete compartido inicial:
  - `packages/shared/package.json` (`@repo/shared-types`)
  - `packages/shared/types/index.ts`
- Estructura principal ya creada por plantilla:
  - `agents/`, `skills/`, `mcps/`, `workflows/`, `services/`, `uis/`, `data/`, `packages/`, `shared/`, `docs/`, `infra/`, `scripts/`, `internal/`.

## Frameworks y stack actualmente utilizados

- Contexto/automatización: Markdown + estructura de carpetas por dominio.
- Frontend: aplicaciones Next.js en `uis/website` y `uis/backoffice` que conservan los módulos HTML/CSS/JS existentes.
- Backend: `services/support-api`, API FastAPI con TinyDB para autenticación interna y gestión de tickets.
- Contenedores: Docker Compose con un contenedor `interfaces` para ambas UIs y un contenedor `backend` para FastAPI.
- Lenguajes detectados en el repo:
  - TypeScript (tipos compartidos)
  - Python (skills/scripts de ejemplo)
  - HTML/CSS/JS (UI implementada en esta tarea)

## Arquitectura y organización

- Regla de separación principal:
  - Interfaces de usuario en `uis/`
  - Servicios/API en `services/`
  - La API central actual para soporte vive en `services/support-api/`.
  - Capacidades de IA y automatización en `agents/`, `skills/`, `mcps/`, `workflows/`
  - Reuso técnico en `packages/` y `shared/`
- Website público y backoffice interno deben vivir como proyectos separados dentro de `uis/`.

## Convenciones importantes observadas

- Leer `README.md` del directorio antes de implementar en ese dominio.
- No volcar entregables en la raíz.
- Mantener `CONTEXT.md` como fuente única de negocio.
- Evitar duplicación de estructuras ya existentes.

## Restricciones técnicas y de negocio

- No inventar información de negocio fuera de `CONTEXT.md`.
- Tratar `customer_email` como dato sensible: nunca mostrar correos individuales.
- El backoffice sigue siendo interno y no incorpora una pantalla pública de alta; `POST /users` también requiere una sesión JWT válida.
- No fabricar tickets históricos si el CSV real no está en el repositorio.
- No reemplazar stack existente ni introducir dependencias innecesarias.

## Comandos importantes

Como no hay runner global en raíz, los comandos se ejecutan por proyecto o mediante utilidades del sistema:

- Inspección de estructura:
  - `find . -maxdepth 4 -print | sort`
- Backend de soporte:
  - `cd services/support-api && python3 -m venv .venv`
  - `pip install -r requirements.txt`
  - Copiar `.env.example` a `.env`, definir `JWT_SECRET` y ejecutar `python -m scripts.create_user`.
  - `uvicorn app.main:app --reload --port 8001`
- Pruebas backend:
  - `cd services/support-api && python -m unittest discover -s tests`
- Plataforma completa:
  - `cp .env.example .env` (solo en la preparación inicial; definir un `JWT_SECRET` local)
  - `docker compose up --build`
  - Website: `http://localhost:3000`
  - Backoffice: `http://localhost:3001`
  - API: `http://localhost:8001`
- Validación de Compose:
  - `docker compose config --quiet`
  - `docker compose ps`

## Decisiones técnicas vigentes de esta iteración

- Las UIs usan wrappers Next.js mínimos para cumplir la ejecución requerida con `next dev` sin reescribir la lógica existente.
- `uis/start.sh` inicia website y backoffice en los puertos 3000 y 3001 dentro de un único contenedor Node Alpine.
- El backoffice consume `/backend/*`; Next reenvía las solicitudes a `http://backend:8001` mediante la red `nexova-dev-network`.
- FastAPI se ejecuta con Uvicorn `--reload` en una imagen Python slim cuyas dependencias se instalan con `uv`.
- Se reutiliza el patrón FastAPI + bcrypt + JWT del proyecto de referencia, adaptado al dominio Nexova.
- `User` y `Profile` viven únicamente en TinyDB; `POST /users` asigna el rol `user` por defecto y `scripts.create_user` continúa disponible para provisionamiento local.
- `get_current_user` usa `OAuth2PasswordBearer` y JWT firmado con `python-jose`; las contraseñas usan `libpass[bcrypt]`. La expiración se configura con `ACCESS_TOKEN_EXPIRE_MINUTES` y conserva `ACCESS_TOKEN_MINUTES` como alias.
- El cambio de contraseña requiere la clave actual; la recuperación usa tokens de un solo uso y Resend. `RESEND_API_KEY` solo se configura en `.env` local.
- TinyDB persiste usuarios y tickets localmente; el correo del cliente se excluye de las respuestas públicas y la UI.
- El backoffice sirve en `http://localhost:3001/`; en Docker usa un proxy del mismo origen hacia la API para evitar exponer nombres internos al navegador.
- La base inicia sin históricos hasta disponer del CSV real de Nexova.
- Se incorpora `memory-bank/` y configuración `.agents/` para continuidad operativa entre sesiones.
