# Backoffice — Nexova Ops

Aplicacion interna para supervisores y operaciones de soporte de Nexova.

## Objetivo

Entregar una vista inicial con contexto operativo relevante: SLA, tamano del equipo, alcance del analisis y lineamientos de privacidad.

## Stack

- Next.js
- React
- HTML
- CSS
- JavaScript (modulos ES)
- Lucide Icons (carga fija desde CDN)
- API central FastAPI en `services/support-api`

## Ejecutar con Docker

Desde la raiz del repositorio:

```bash
docker compose up
```

Abrir `http://localhost:3001/`. Las solicitudes a `/backend/*` se envian desde Next al servicio `backend` dentro de la red Docker.

## Ejecutar sin Docker

Primero inicia la API siguiendo [`services/support-api/README.md`](../../services/support-api/README.md). Crea una cuenta interna desde el backend y configura un `JWT_SECRET` local.

Después, desde el backoffice:

```bash
cd uis/backoffice
BACKEND_INTERNAL_URL=http://127.0.0.1:8001 npm run dev -- --port 3001
```

Abrir `http://127.0.0.1:3001/`.

## Acceso y tickets

- El panel requiere iniciar sesión; no hay autorregistro público.
- Las cuentas se provisionan con `python -m scripts.create_user` desde `services/support-api/`.
- La pantalla de acceso permite recuperar y restablecer contraseñas con Resend configurado en `.env`.
- Las personas autenticadas pueden cambiar su contraseña validando la actual.
- La recuperación se envía a la cuenta interna; no utiliza ni muestra `customer_email` de tickets.
- Los tickets usan las categorías, estados y campos de `CONTEXT.md`.
- El correo del cliente se captura para el registro, pero no aparece en listados, estadísticas ni mensajes de error.
- El panel comienza sin tickets históricos porque el CSV real no está incluido en este repositorio.

## Alcance actual

- Ruta `/` protegida por login interno.
- Consola operativa responsive con navegacion lateral en escritorio y barra compacta en movil.
- Sistema visual accesible con foco visible, controles tactiles de al menos 44 px y movimiento reducido cuando el sistema lo solicita.
- Indicadores de SLA, resumen de tickets, filtros, estados y feedback de carga/error diferenciados visualmente.
- Resumen operativo, alta y seguimiento de tickets alineados con `CONTEXT.md`.
