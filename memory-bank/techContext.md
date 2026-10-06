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
- Frontend (en esta iteración): aplicaciones estáticas HTML/CSS/JS en `uis/website` y `uis/backoffice`.
- Backend: `services/support-api`, API FastAPI con TinyDB para autenticación interna y gestión de tickets.
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
- El backoffice usa cuentas internas administradas; no habilitar registro público.
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
- Levantar website estático:
  - `cd uis/website && python3 -m http.server 4173`
- Levantar backoffice estático:
  - `cd uis/backoffice && python3 -m http.server 4174`
- Validación de ruta `/`:
  - `curl -I http://127.0.0.1:4173/`
  - `curl -I http://127.0.0.1:4174/`

## Decisiones técnicas vigentes de esta iteración

- Se implementan UIs sin framework adicional para no imponer un stack no definido por el template.
- Se reutiliza el patrón FastAPI + bcrypt + JWT del proyecto de referencia, adaptado al dominio Nexova.
- Las cuentas se provisionan con un script local; no existe endpoint de registro.
- El cambio de contraseña requiere la clave actual; la recuperación usa tokens de un solo uso y Resend. `RESEND_API_KEY` solo se configura en `.env` local.
- TinyDB persiste usuarios y tickets localmente; el correo del cliente se excluye de las respuestas públicas y la UI.
- El backoffice sirve en `http://127.0.0.1:4174/` y la API Nexova en el puerto 8001 permite ese origen por CORS (8000 puede estar ocupado por el proyecto de referencia).
- La base inicia sin históricos hasta disponer del CSV real de Nexova.
- Se incorpora `memory-bank/` y configuración `.agents/` para continuidad operativa entre sesiones.
