# Backoffice — Nexova Ops

Aplicacion interna para supervisores y operaciones de soporte de Nexova.

## Objetivo

Entregar una vista inicial con contexto operativo relevante: SLA, tamano del equipo, alcance del analisis y lineamientos de privacidad.

## Stack

- HTML
- CSS
- JavaScript (modulos ES)
- API central FastAPI en `services/support-api`

## Ejecutar local

Primero inicia la API siguiendo [`services/support-api/README.md`](../../services/support-api/README.md). Crea una cuenta interna desde el backend y configura un `JWT_SECRET` local.

Después, desde el backoffice:

```bash
cd uis/backoffice
python3 -m http.server 4174
```

Abrir `http://127.0.0.1:4174/`.

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
- Layout propio (sidebar + content), distinto al website publico.
- Resumen operativo, alta y seguimiento de tickets alineados con `CONTEXT.md`.
