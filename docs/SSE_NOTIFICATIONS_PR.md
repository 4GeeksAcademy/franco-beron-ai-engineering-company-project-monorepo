# Pull Request: Sistema de Notificaciones SSE en Tiempo Real

## Descripción

Implementación del sistema de notificaciones en tiempo real mediante **Server-Sent Events (SSE)** para Nexova. Cuando se registra un nuevo ticket de RFP, el dashboard del backoffice lo muestra automáticamente sin necesidad de recargar la página. Se incluye también un sistema opcional de **alertas de umbral KPI** para monitoreo de SLA, satisfacción y backlog.

---

## ✅ Checklist de Criterios de Aceptación

### Backend

- [x] Endpoint SSE `GET /api/events/stream` que emite eventos cuando se registra un nuevo ticket RFP
- [x] Nombre de evento explícito: `rfp_ticket_created` (no un genérico "message")
- [x] Payload estructurado con `ticket_id`, `rfp_id`, `client_name`, `client_hq`, `services_requested`, `status`, `created_at`
- [x] Headers SSE correctos: `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`
- [x] Keep-alive cada 15s (comentario SSE `: keepalive`)
- [x] Protegido con el **mismo JWT** que usa la API del backoffice (`OAuth2PasswordBearer`)
- [x] Integración con el pipeline RFP: broadcast SSE en upload (`status=analizando`) y al completar (enriquecido con metadatos)
- [x] **Bonus**: `POST /api/events/kpi-alert` + `run_background_kpi_monitor` para alertas de umbral KPI

### Frontend

- [x] Dashboard recibe notificaciones en tiempo real sin acción manual
- [x] Consume SSE con `fetch()` + `ReadableStream` (NO `EventSource` a pelo)
- [x] Envía JWT via `Authorization: Bearer` header
- [x] Reconexión con **backoff exponencial progresivo**: 1s → 2s → 4s → ... → 30s máximo + jitter 20%
- [x] **Estrategia de recuperación**: `Last-Event-ID` / ring buffer replay (100 eventos en servidor)
- [x] **Deduplicación**: `Set<string>` de `ticket_id` ya recibidos — el mismo ticket no aparece dos veces
- [x] Notificación visualmente distinguible: toast animado con ícono `zap`, color teal, pulso, sombra, nombre del cliente, metadatos
- [x] No requiere recargar página ni refetch completo

### Pruebas

- [x] Test del endpoint SSE verifica: headers `text/event-stream`, evento nombrado `rfp_ticket_created`, JSON en `data:` con los campos requeridos
- [x] Test de serialización SSE wire format
- [x] Test de broadcast pub/sub con múltiples suscriptores
- [x] Test de ring buffer replay (`Last-Event-ID`)
- [x] Test de keep-alive
- [x] Test de reconexión y recuperación (background monitor)
- [x] **17 tests KPI**: compute_kpis, breach_alerts, broadcast, endpoint, background lifecycle
- [x] **Total**: 161 tests, 0 failures

### Generales

- [x] No hay llamadas a modelos o agentes (es solo capa de comunicación)
- [x] Nombres de campos y entidades coinciden con el BRIEFING.md de Nexova
- [x] Feature branch: `feature/sse-notifications`

---

## 🤔 Preguntas de Diseño

### 1. Conexiones SSE independientes vs capa intermedia compartida

> Si dos personas del equipo comercial abren el dashboard al mismo tiempo, ¿cada conexión SSE debería ser independiente o deberían compartir alguna capa intermedia? ¿Qué pasaría si 50 personas lo abren a la vez?

**Respuesta: cada conexión es independiente.**

**Arquitectura actual:** cada cliente obtiene su propia `asyncio.Queue` dentro del `SSEManager`. Cuando hay un broadcast, el manager itera sobre todas las colas y encola el evento en cada una. Esto es un patrón **pub/sub en memoria** con un canal único.

**¿Por qué esta decisión?**

1. **Simplicidad**: no hay Redis, RabbitMQ ni otra infraestructura externa. Para el alcance actual (equipo comercial de ~10 personas, todos en la misma red local o VPN), el overhead de 50 conexiones abiertas con una queue cada una es insignificante (~KB por cola).

2. **Latencia mínima**: el broadcast es directo desde el manager a cada suscriptor, sin hops intermedios.

3. **Aislamiento natural**: si un cliente es lento (queue full), solo él se desconecta — los demás no se ven afectados.

**¿Qué pasaría con 50 usuarios concurrentes?** Cada broadcast haría 50 `put_nowait()` — eso es O(n) en el broadcast, pero cada put es O(1). Incluso con 50 usuarios, un broadcast tarda microsegundos. El cuello de botella real sería el **ancho de banda de red** si todos están en la misma conexión compartida, no la CPU del servidor.

**¿Cuándo necesitaríamos una capa compartida (Redis Pub/Sub)?** Si la aplicación escala horizontalmente a múltiples workers de Uvicorn o múltiples servidores. En ese caso, el `SSEManager` en memoria no funciona porque los eventos broadcast desde worker A no llegan a los clientes conectados a worker B. Ahí se necesitaría Redis Pub/Sub (o similar) como capa intermedia. Pero para un solo proceso, el patrón actual es correcto.

**¿Cuándo es mejor una capa externa?** Si se necesita:
- Múltiples workers/máquinas
- Persistencia de eventos (más allá del ring buffer de 100)
- Agregación cross-cliente (contar cuántos vieron un evento, etc.)

### 2. Estrategia de recuperación y deduplicación

> ¿Qué estrategia de recuperación elegiste para tickets registrados mientras estabas desconectado (`Last-Event-ID` / replay corto, refetch-luego-SSE, o equivalente), y cómo evitas duplicados tras reconectar?

**Estrategia elegida: `Last-Event-ID` + ring buffer en servidor.**

**Cómo funciona:**

1. Cada evento SSE que se emite lleva un `id:` numérico secuencial (auto-incrementado por `SSEManager.broadcast()`)
2. El cliente (`sse.js` / `main.js`) guarda el último `id:` recibido en la variable `sseLastEventId`
3. Al reconectar, envía `Last-Event-ID=<número>` como query parameter
4. El servidor, al crear la nueva suscripción, revisa el ring buffer (`_recent_events`) y **reproduce (replay)** todos los eventos con `event_id > last_event_id`
5. Si `last_event_id` es anterior al evento más antiguo del buffer (ya fue evictado), el cliente no recibe replay — confía en que el refetch de la lista de tickets (trigger por `loadRFPTickets()`) recuperará el estado completo

**Deduplicación:** El frontend mantiene un `Set<string>` llamado `sseSeenTicketIds` con todos los `ticket_id` ya recibidos. Antes de procesar cualquier evento, verifica si `data.ticket_id` ya está en el set. Si está, lo salta silenciosamente. Esto evita duplicados en dos escenarios:
- Replay de eventos que el cliente ya había recibido antes de desconectarse
- La doble notificación (SSE + refetch) alrededor de la reconexión

**Refuerzo adicional:** tras cada evento SSE que crea un ticket nuevo, `handleRfpTicketCreated()` programa un `loadRFPTickets()` con 500ms de delay para sincronizar la lista completa del dashboard con el backend.

### 3. ¿Por qué SSE y no WebSockets?

> ¿Por qué SSE es la herramienta correcta para notificar la llegada de un ticket y no WebSockets? ¿En qué momento dejaría de serlo — por ejemplo, si quisieras que alguien pudiera reaccionar al ticket desde el mismo canal?

**Por qué SSE es la herramienta correcta:**

| Aspecto | SSE | WebSockets |
|---|---|---|
| **Dirección** | Unidireccional (servidor → cliente) | Bidireccional |
| **Caso de uso** | Notificaciones, streams de eventos | Chat, juegos, colaboración en tiempo real |
| **Protocolo** | HTTP estándar (funciona con proxies, load balancers) | Upgrade de protocolo (ws://) |
| **Reconexión automática** | Nativa (`EventSource`) + manual con `fetch` | Hay que implementarla |
| **Auth** | Headers HTTP estándar | Hay que negociarla en el handshake |
| **Complejidad** | Baja | Media/alta |
| **Mensajes** | Solo texto (UTF-8) | Texto y binario |

**Para la notificación de tickets RFP, SSE es ideal porque:**

- **Solo es unidireccional**: el servidor empuja eventos al dashboard. El usuario no necesita enviar datos por el mismo canal. Cuando quiere subir un RFP, usa `POST /api/rfp/upload` (REST normal).
- **Es HTTP puro**: funciona con proxies, nginx, CDNs, load balancers y firewalls sin configuración especial.
- **Reconexión más simple**: con `Last-Event-ID` tenemos un mecanismo estándar para no perder eventos, sin tener que implementar un protocolo de acknowledgments.
- **Menos recursos**: una conexión SSE es más ligera que un WebSocket (no tiene frames de control, no hace ping/pong a nivel protocolo).

**¿Cuándo dejaría de ser suficiente SSE?** Si quisiéramos que alguien pudiera **reaccionar al ticket desde el mismo canal** (por ejemplo, asignarlo, cambiarlo de prioridad, o discutirlo en un chat), entonces necesitaríamos bidireccionalidad — ahí WebSockets es la herramienta correcta. El proyecto menciona esto explícitamente: "la Parte 2 (chat WebSocket) vive en `real-time-communication/`".

También dejaría de ser suficiente SSE si:
- Necesitamos enviar datos binarios al servidor en tiempo real (ej. audio/video)
- El volumen de mensajes es muy alto (>1000 msg/s) donde el overhead de SSE (reconexión HTTP) se vuelve significativo
- Necesitamos entrega ordenada y garantizada con acknowledgments individuales

---

## 🔧 Cambios por Archivo

### Backend

| Archivo | Cambio |
|---|---|
| `services/support-api/app/notifications.py` | **NUEVO** — `SSEManager`, `SSEEvent`, ring buffer, pub/sub |
| `services/support-api/app/routers/events.py` | **NUEVO** — `GET /api/events/stream`, `POST /api/events/kpi-alert` |
| `services/support-api/app/routers/rfp.py` | **MODIFICADO** — broadcast SSE en upload + pipeline completion |
| `services/support-api/app/kpi_monitor.py` | **NUEVO** — `compute_kpis()`, `broadcast_kpi_alerts()`, `run_background_kpi_monitor()` |
| `services/support-api/app/main.py` | **MODIFICADO** — lifespan inicia/limpia KPI monitor, registra `events_router` |

### Frontend

| Archivo | Cambio |
|---|---|
| `uis/backoffice/lib/sse.js` | **NUEVO** — Cliente SSE reutilizable (fetch + ReadableStream) |
| `uis/backoffice/main.js` | **MODIFICADO** — SSE inline client, toast notifications, dedup, reconexión |
| `uis/backoffice/styles.css` | **MODIFICADO** — `sse-toast` animado, `system-status` indicator |

### Testing

| Archivo | Cambio |
|---|---|
| `tests/test_sse_notifications.py` | **NUEVO** — 24 tests SSE |
| `tests/test_kpi_monitor.py` | **NUEVO** — 17 tests KPI |

---

## 🧪 Resultados de Tests

```text
161 passed in 25.41s
```

---

## 📦 Dependencias Nuevas

Ninguna. Todo el sistema SSE usa la biblioteca estándar (`asyncio`) y FastAPI (`StreamingResponse`). TinyDB y SQLModel ya estaban en el proyecto.

---

## 🚀 Cómo Probar Manualmente

### 1. Iniciar servicios

```bash
docker compose up --build
```

O sin Docker:

```bash
cd services/support-api
uvicorn app.main:app --reload --port 8001
```

### 2. Iniciar sesión en el backoffice

Abrir `http://localhost:3001`, registrarse e iniciar sesión. El indicator `system-status` en el sidebar debe mostrar "Tiempo real conectado" en verde.

### 3. Probar notificación RFP

```bash
# Subir un PDF de RFP (desde el backoffice o con curl)
curl -X POST http://localhost:8001/api/rfp/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@nexova-request-1.pdf"
```

El dashboard debe mostrar un toast animado en la esquina inferior derecha con el nombre del cliente y ticket_id.

### 4. Probar reconexión

1. Conectar y verificar el status "Tiempo real conectado"
2. Detener el backend (Ctrl+C en el terminal de uvicorn)
3. El status indicator cambia a "Tiempo real: reconectando..." en ámbar
4. Reiniciar el backend
5. La conexión se restablece automáticamente con backoff — el indicator vuelve a verde

### 5. (Bonus) Probar alerta KPI

```bash
curl -X POST http://localhost:8001/api/events/kpi-alert \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"kpi_name":"sla_compliance_rate","metric":45,"threshold":"80%","severity":"critical","description":"SLA compliance dropped to 45%"}'
```

---

## 🔜 Siguientes Pasos

- [ ] **Parte 2**: Chat WebSocket en `real-time-communication/` (según el roadmap del proyecto)
- [ ] Agregar tests de integración E2E con navegador (Playwright/Cypress) para verificar el flujo SSE completo
- [ ] Considerar migración a Redis Pub/Sub si se escala a múltiples workers
