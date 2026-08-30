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
- Backend: no se creó nuevo servicio en esta tarea (se respeta `services/` para futuros servicios).
- Lenguajes detectados en el repo:
  - TypeScript (tipos compartidos)
  - Python (skills/scripts de ejemplo)
  - HTML/CSS/JS (UI implementada en esta tarea)

## Arquitectura y organización

- Regla de separación principal:
  - Interfaces de usuario en `uis/`
  - Servicios/API en `services/`
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
- No reemplazar stack existente ni introducir dependencias innecesarias.

## Comandos importantes

Como no hay runner global en raíz, los comandos se ejecutan por proyecto o mediante utilidades del sistema:

- Inspección de estructura:
  - `find . -maxdepth 4 -print | sort`
- Levantar website estático:
  - `cd uis/website && python3 -m http.server 4173`
- Levantar backoffice estático:
  - `cd uis/backoffice && python3 -m http.server 4174`
- Validación de ruta `/`:
  - `curl -I http://127.0.0.1:4173/`
  - `curl -I http://127.0.0.1:4174/`

## Decisiones técnicas vigentes de esta iteración

- Se implementan UIs sin framework adicional para no imponer un stack no definido por el template.
- Se evita crear `services/` adicionales al no ser necesarios para cumplir el objetivo actual.
- Se incorpora `memory-bank/` y configuración `.agents/` para continuidad operativa entre sesiones.
