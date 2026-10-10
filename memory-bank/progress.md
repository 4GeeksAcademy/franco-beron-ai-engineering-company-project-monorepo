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

## Rediseño UI/UX del backoffice (2026-10-01)

- Se aplicó la guía `ui-ux-pro-max` al backoffice estático, manteniendo intactos los flujos de autenticación, recuperación, tickets, filtros y cambios de estado.
- Se implementó una consola operativa responsive con sistema de color semántico, iconos Lucide, navegación compacta, KPIs, barras de distribución y estados vacíos/carga/error.
- Se mejoraron accesibilidad y ergonomía con foco visible, labels persistentes, targets de al menos 44 px, toggle de contraseña, navegación activa y soporte para `prefers-reduced-motion`.
- Playwright validó vistas de 1440 x 1000 y 375 x 812 sin overflow horizontal, controles pequeños, errores de consola ni excepciones de página.
- `node --check`, diagnósticos del editor y carga HTTP de HTML, CSS y JavaScript: aprobados.

## Contenedorización del monorepo (2026-10-06)

- Se adaptaron website y backoffice a wrappers Next.js conservando sus módulos, estilos y comportamiento existentes.
- `uis/Dockerfile` usa Node Alpine, instala dependencias por aplicación y ejecuta ambos procesos mediante `uis/start.sh` en los puertos 3000 y 3001.
- `services/Dockerfile` usa Python slim, instala `uv` y carga las dependencias FastAPI con `uv pip install`.
- `docker-compose.yml` orquesta `interfaces` y `backend` con bind mounts, recarga en caliente y la red explícita `nexova-dev-network`.
- El backoffice solicita `/backend/*` y Next reenvía a `http://backend:8001`; no hay URLs `localhost` en el código cliente.
- Se añadieron `.dockerignore` para `uis/` y `services/`, una plantilla `.env.example` sin secretos y exclusiones raíz para `.env`, Node y Next.

### Validaciones de contenedores

- `docker compose up -d --build`: ambos servicios construidos e iniciados correctamente.
- `docker compose ps`: backend saludable e interfaces en ejecución.
- Website `:3000`, backoffice `:3001`, API `:8001` y proxy `/backend/health`: respuestas correctas.
- Resolución interna desde `interfaces` hacia `http://backend:8001/health`: `200 OK`.
- Suite backend dentro del contenedor: 15 pruebas aprobadas.
- Builds Next de website y backoffice: aprobados; auditorías npm sin vulnerabilidades.
- `docker compose config --quiet`, `sh -n`, `node --check`, diagnósticos y `git diff --check`: aprobados.
- Bind mount `uis/` hacia `/app` confirmado para recarga en caliente.
- `.env` ignorado, no rastreado y ausente del historial Git.

## Gestión de inventario con SQLModel (2026-10-09)

- Se creó la rama local `feature/gestion-inventario` desde `feature/containerization`.
- Se añadió SQLModel con `psycopg` y una conexión opcional a PostgreSQL/Supabase mediante `SUPABASE_DATABASE_URL`; TinyDB sigue siendo la persistencia de autenticación y tickets.
- Se añadieron modelos separados `Asset`, `AssetEntry` y `AssetExit`, con claves foráneas, sesiones SQLModel por request y creación de esquema al iniciar cuando existe configuración.
- Se añadió el router `/inventory` con seis operaciones: listado/creación/detalle de assets y creación/listado de entradas y salidas. Las escrituras requieren JWT; los GET son públicos.
- El stock se calcula como entradas menos salidas; las salidas excesivas responden HTTP 400 antes de persistir. `office` filtra lecturas y queda en modelos/respuestas.
- Se agregaron seis assets, cinco entradas y tres salidas semilla idempotentes. Las cuentas nuevas reciben UUID al crearse y las existentes al efectuar su primer movimiento.
- Se documentó la variable Supabase y el funcionamiento local. No se pudo actualizar `.env.example` porque el workspace lo protege; no contiene credenciales y `.env` continúa ignorado por Git.

### Validaciones

- Instalación/resolución de dependencias con `uv pip install --system -r services/support-api/requirements.txt`: aprobada.
- Suite existente del backend: 15 pruebas aprobadas.
- Smoke test de inventario en SQLite: stock semilla correcto, salida excesiva HTTP 400 y sin escritura parcial.
- OpenAPI: seis operaciones registradas, POST autenticados y GET públicos.
- `compileall`, Compose `config --quiet`, `git diff --check` y diagnósticos del editor: aprobados.
- En la verificación inicial no se probó la conexión real por falta de `SUPABASE_DATABASE_URL`; se configuró después y se validó con `SELECT 1` el 2026-10-10.

### Configuración del shared pooler y Agent Skills (2026-10-09)

- Se documentó la URI de Supabase suministrada para `aws-0-us-east-1.pooler.supabase.com:6543`, con el usuario y una marca explícita para completar la contraseña codificada localmente; no se escribió ni solicitó ningún secreto.
- Se configuró Psycopg con `prepare_threshold=None`, requerido por el modo transaction pooling del puerto 6543 según la documentación oficial actual de Supabase.
- Se instalaron las skills oficiales `supabase` y `supabase-postgres-best-practices` mediante `npx skills add supabase/agent-skills`; el instalador también generó `.claude/` y `skills-lock.json`.
- El `.env` local ya existía y no se sobrescribió; la contraseña se mantuvo fuera del chat y no se guardó en archivos rastreados. La conexión se verificó en la etapa siguiente.

### Inicialización real en Supabase (2026-10-10)

- Con autorización del desarrollador se ejecutó `docker compose up --build -d backend`; el contenedor quedó `healthy` y el lifespan creó las tablas SQLModel y cargó semillas.
- `GET /inventory/products` devolvió seis assets con stock neto verificado: `NXV-IT-001=13`, `NXV-IT-002=0`, `NXV-PER-002=11` y `NXV-OFF-001=97`.
- Consulta de solo lectura a `information_schema` y conteos confirmó `asset=6`, `assetentry=5`, `assetexit=3`.
- No se guardaron credenciales en archivos rastreados ni se registraron en esta bitácora.

## Backoffice de inventario (2026-10-10)

- Se implementó en `feature/interfaz-visual` la sección `/backoffice/inventory` dentro del backoffice Next.js existente.
- Se añadió `lib/inventory.js` para centralizar llamadas, enviar JWT, extraer errores HTTP y redirigir sesiones ausentes o expiradas al login conservando la ruta de retorno.
- Se añadieron las vistas protegidas de productos, entrada, salida e historial de solo lectura; el formulario de salida consulta stock reactivo, previene cantidades excesivas y presenta el HTTP 400 junto al campo.
- La tabla muestra asset, SKU, categoría, oficina y `current_stock`; stock bajo se define como menos de cinco unidades y agotado como cero. La navegación existente enlaza al inventario.
- Se documentó ejecución en Docker mediante proxy `/backend` y configuración opcional `NEXT_PUBLIC_INVENTORY_API_URL`; `.env.local` está ignorado por Git.
- Build de Next aprobado; las cuatro rutas devolvieron HTTP 200 y el proxy `/backend/health` devolvió estado `ok`.
- El backend de inventario real está disponible y sus endpoints de lectura devolvieron los datos semilla previamente verificados.
- No se completó prueba visual Playwright: el instalador de Chromium no soporta Ubuntu 20.04 en este entorno. No se añadieron dependencias de navegador al proyecto.
