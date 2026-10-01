# Progress Log

## Estado inicial del proyecto

- Monorepo en estado plantilla base.
- `CONTEXT.md` originalmente en placeholder; luego actualizado con contexto real de Nexova.
- No existian `memory-bank/`, `AGENTS.md`, `.agents/`, `uis/website` ni `uis/backoffice`.
- No habia apps frontend ejecutables en `uis/`.

## Trabajo realizado en esta tarea

- Se completo inspeccion inicial de estructura, README y existencia de rutas clave.
- Se actualizo `CONTEXT.md` con briefing real de Nexova desde fuente oficial.
- Se crearon y completaron archivos de `memory-bank/`.
- Se creo `AGENTS.md` con flujo obligatorio pre-commit y reglas de operacion.
- Se creo una regla especifica en `.agents/rules/`.
- Se creo una skill reutilizable en `.agents/skills/`.
- Se implementaron dos UIs separadas:
  - `uis/website` (publica)
  - `uis/backoffice` (interna)

## Archivos y estructuras creadas o modificadas

- Modificados:
  - `CONTEXT.md` (actualizado a contexto real de Nexova)
- Creados:
  - `AGENTS.md`
  - `memory-bank/projectbrief.md`
  - `memory-bank/techContext.md`
  - `memory-bank/progress.md`
  - `.agents/rules/nexova-incident-context-and-privacy.md`
  - `.agents/skills/nexova-memory-bank-update/SKILL.md`
  - `uis/website/index.html`
  - `uis/website/components.js`
  - `uis/website/main.js`
  - `uis/website/styles.css`
  - `uis/website/README.md`
  - `uis/backoffice/index.html`
  - `uis/backoffice/main.js`
  - `uis/backoffice/styles.css`
  - `uis/backoffice/README.md`

## Validaciones realizadas

- Validacion de scripts disponibles:
  - Busqueda de scripts `lint`, `test`, `typecheck`, `build` en `package.json`: no existen comandos definidos actualmente en el repo.
- Validacion manual de frontends:
  - `uis/website` levantado con `python3 -m http.server 4173`.
  - `uis/backoffice` levantado con `python3 -m http.server 4174`.
  - Comprobacion de ruta `/` en ambos con `curl -I`: respuesta `HTTP/1.0 200 OK`.
- Chequeo de errores de workspace:
  - `get_errors`: sin errores reportados.
- Verificacion de estructura:
  - Confirmada existencia de `memory-bank/`, `AGENTS.md`, `.agents/rules/`, `.agents/skills/`, `uis/website`, `uis/backoffice` y `services/`.
  - No se detectaron duplicaciones innecesarias de esas rutas.

## Problemas encontrados

- Bloqueo inicial: falta de contexto real en `CONTEXT.md`.
- Resolucion: carga de contexto oficial Nexova solicitada por el desarrollador.

## Estado final

- Repositorio actualizado con contexto real de Nexova para esta iteracion.
- `memory-bank` inicializado y documentado con contexto de negocio, tecnico y bitacora de avance.
- `AGENTS.md` creado con flujo obligatorio pre-commit y reglas de seguridad/operacion.
- Configuracion `.agents` creada con una regla especifica de privacidad y una skill reutilizable de mantenimiento de memory bank.
- Website publico implementado en `uis/website` con contenido real de Nexova.
- Backoffice interno implementado en `uis/backoffice` con layout propio y datos operativos reales del contexto.

## Actualizacion final de verificacion (2026-08-30)

- Se reviso el estado de git y el alcance staged en rama `main`.
- Se confirmo que no hay scripts de `lint`, `test`, `typecheck` o `build` definidos en `packages/shared/package.json` (scripts vacio).
- Se ejecuto validacion de diagnosticos del workspace: sin errores (`get_errors`).
- Se levanto `uis/website` con `python3 -m http.server 4173` y se verifico `GET /` y `HEAD /` con respuesta `200 OK`.
- Se levanto `uis/backoffice` con `python3 -m http.server 4174` y se verifico `GET /` y `HEAD /` con respuesta `200 OK`.
- Se verifico que website y backoffice mantienen layouts diferenciados y contenido alineado con `CONTEXT.md`.
- Se cerro esta tarea dejando el repositorio listo para commit y apertura de PR.

## Adaptación de autenticación y tickets Nexova (2026-09-30)

- Se usó `FranBeron/monorepo-auth` como referencia técnica; los cambios se realizaron en este monorepo Nexova.
- Se creó `services/support-api/` con FastAPI, bcrypt, JWT y TinyDB.
- Las cuentas son administradas con `python -m scripts.create_user`; no se habilitó registro público.
- Se adaptó el modelo a `CONTEXT.md`: categorías y estados Nexova, fecha ISO, empresa cliente, agente y satisfacción.
- `customer_email` se valida y persiste, pero no aparece en schemas públicos, listados, resúmenes, errores ni logs.
- Se conectó `uis/backoffice` al login interno y al flujo de tickets, conservando el panel operativo previo.
- El backoffice ofrece creación, filtros, resumen, actualización de estado y reversión visual ante error.
- No se generaron históricos ficticios: `incidents-nexova.csv` no está incluido en este repositorio.

### Validaciones

- `python -m unittest discover -s tests` en `services/support-api`: 6 pruebas aprobadas.
- Importación de FastAPI y carga de rutas: aprobadas.
- `TestClient`: `/health` devuelve 200; lista y resumen requieren token; `/auth/register` no existe.
- `python -m compileall` para `app/` y `scripts/`: aprobado.
- `node --check uis/backoffice/main.js`: aprobado.
- `get_errors`: sin errores en archivos Python y UI modificados.
- Búsqueda de direcciones email en servicio y backoffice: sin coincidencias.
- `git diff --check`: aprobado.

### Puesta en marcha

- API: crear `.venv`, instalar `services/support-api/requirements.txt`, copiar `.env.example` a `.env`, configurar `JWT_SECRET`, provisionar una cuenta y ejecutar Uvicorn en el puerto 8001.
- Backoffice: servir `uis/backoffice` en el puerto 4174 y abrir `http://127.0.0.1:4174/`.
- Falta incorporar el CSV real para importar registros históricos.
- En esta sesión se iniciaron API y backoffice en `8001` y `4174`; no se creó ninguna cuenta ni se dejó un secreto persistente.

## Recuperación de contraseña por email (2026-10-01)

- Se añadió el flujo `forgot-password` / `reset-password` para cuentas internas administradas, usando Resend.
- Se añadió cambio de contraseña autenticado, con verificación de clave actual e invalidación de enlaces pendientes.
- Las solicitudes de recuperación responden de forma genérica para no revelar si una cuenta existe.
- Los tokens de recuperación se guardan hasheados, vencen en 30 minutos, son de un solo uso y se invalidan si se solicita otro enlace.
- El backoffice recibe el token por query string, lo retira enseguida de la barra de direcciones y permite establecer una nueva contraseña.
- Se añadió `resend` a las dependencias y se documentaron `RESEND_API_KEY`, `EMAIL_FROM`, `FRONTEND_URL`, `JWT_ALGORITHM` y `ACCESS_TOKEN_MINUTES` en el README del servicio.
- No se escribió ninguna clave real. No existe `services/support-api/.env` local; el envío efectivo requiere cargar una clave nueva y un remitente permitido/verificado por Resend.

### Validaciones de recuperación

- Suite backend: 14 pruebas aprobadas, incluidos cambio de contraseña, envío simulado, expiración, hash y rechazo de reutilización del token.
- TestClient: health público, tickets protegidos, endpoints auth y recuperación registrados, token inválido rechazado y autorregistro ausente.
- `python -m compileall`, `node --check`, diagnósticos de archivos modificados y `git diff --check`: aprobados.
- El envío no se probó contra Resend real porque no se usa ni se guarda la clave proporcionada en el chat.

## Aislamiento de incidencias Nexova (2026-10-01)

- Se corrigieron respuestas `500` en el listado y resumen autenticados causadas por 12 incidencias heredadas de `monorepo-auth` con un esquema incompatible.
- La API usa ahora la tabla TinyDB `nexova_incidents`; la tabla heredada `incidents` permanece intacta y no se presenta como información real de Nexova.
- La validación autenticada devuelve lista vacía y resumen con total 0 hasta que se creen tickets Nexova o se incorpore el CSV real.
