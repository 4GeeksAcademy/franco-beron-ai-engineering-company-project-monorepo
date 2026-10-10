# Propuesta de arquitectura de backend — Nexova

**Estado:** primer borrador para revisión del CTO, Sergio Molina.

**Fecha:** 2026-10-10.

**Rama:** `feature/arq-proposal`.

**Alcance:** propuesta técnica documental; no implementa ni cambia endpoints.

## 1. Contexto, objetivos y límites

La fuente de verdad del negocio es [CONTEXT.md](../CONTEXT.md). Nexova presta servicios de consultoría y outsourcing de RR. HH., con oficinas en Valencia y Miami. Su operación de soporte cuenta con 30 agentes que atienden a clientes de tecnología, retail y finanzas. Roberto Díaz, Customer Support Lead, necesita comprender el backlog y la satisfacción: el SLA comprometido es de 24 horas y el promedio actual es de 48 horas.

El backend debe ofrecer validaciones consistentes de tickets, consultas operativas y métricas agregadas, sin exponer `customer_email` en respuestas, logs, exportaciones o errores ni enviar los datos del CSV a herramientas de IA externas. Una arquitectura por sí sola no garantiza reducir el tiempo de atención: facilita información fiable para decidir mejoras operativas.

Aunque la consigna plantea diseñar antes de programar, este monorepo ya contiene una API. La propuesta toma esa implementación como punto de partida y distingue el estado real del diseño objetivo. No pretende presentar cambios futuros como funciones entregadas.

El contexto de soporte es el dominio principal. Inventario y proveedores se incluyen porque ya existen como hitos documentados en [memory-bank/projectbrief.md](../memory-bank/projectbrief.md) y [services/support-api/README.md](../services/support-api/README.md), no como nuevos requisitos de negocio inferidos. No se añaden nóminas, selección de candidatos ni otros dominios sin briefing.

Hay dos límites de datos que requieren confirmación de Roberto antes de un futuro importador:

- El contexto menciona 1.000 filas en su introducción y 100 en el detalle del archivo de prueba. No se fija uno como volumen real de producción.
- El CSV real no está disponible en el repositorio. El esquema descrito no incluye timestamps de apertura y cierre; no permite calcular por sí solo duración de resolución ni cumplimiento individual del SLA.

## 2. Patrón elegido y justificación

Se propone un **monolito modular con arquitectura en capas**, dentro de la API FastAPI existente en `services/support-api`. Se conserva un único backend desplegable y una entrada HTTP, pero se separan dominios y responsabilidades.

| Capa                                     | Responsabilidad                                                                                         | No debe hacer                                                     |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Presentación HTTP: routers y schemas     | Recibir solicitudes, validar forma y tipos, aplicar dependencias de acceso, devolver contratos públicos | Consultar tablas directamente o duplicar reglas de negocio        |
| Aplicación y dominio: servicios y reglas | Ejecutar casos de uso, coordinar operaciones y aplicar invariantes                                      | Depender de componentes Next.js o decidir detalles HTTP           |
| Persistencia: repositorios y modelos     | Leer/escribir datos y delimitar transacciones                                                           | Calcular reglas de negocio en la UI o definir respuestas públicas |
| Infraestructura y configuración          | Conexiones, secretos, correo y ciclo de vida de la aplicación                                           | Contener reglas de tickets o datos sensibles en constantes        |

El flujo es `router -> servicio/reglas -> repositorio -> almacenamiento`. Las dependencias de autenticación y sesión se inyectan en la entrada del caso de uso. El router traduce resultados o errores del dominio a HTTP; un servicio no debe lanzar respuestas de FastAPI como contrato interno.

**Por qué encaja con Nexova:** las mismas categorías, estados y reglas de satisfacción deben servir a creación, actualización, análisis y futuras importaciones. Centralizarlas evita que dos flujos interpreten un ticket cerrado de forma diferente. La separación del contrato público también hace verificable la prohibición de exponer correos. El número de agentes conocido no demuestra una necesidad de escalado independiente por dominio; mantener una API reduce despliegues, comunicación distribuida y duplicación de autenticación.

**Alternativas consideradas:**

- **MVC:** resulta útil para sistemas que renderizan vistas en el servidor. Aquí las vistas viven en Next.js y FastAPI entrega JSON; capas y routers expresan mejor esa separación sin crear una segunda capa de vistas en Python.
- **Microservicios:** permitirían escalar dominios por separado, pero no hay evidencia de equipos independientes o cargas que lo requieran. Añadirían contratos de red, fallos parciales y coordinación de datos antes de aportar un beneficio comprobado.
- **Serverless:** puede ser útil para tareas aisladas, pero no resuelve la organización del dominio y exigiría adaptar ejecución, conexiones y despliegue. Se mantiene el stack existente; se reconsideraría solo ante una necesidad medida.

El coste de esta elección es que los módulos comparten despliegue y pueden afectarse mutuamente. Se mitiga con límites de dependencias y pruebas por dominio. No se extrae un worker hasta que una tarea larga o un requisito de aislamiento lo justifique.

## 3. Investigación de FastAPI y decisiones derivadas

Se consultó la documentación oficial el 2026-10-10:

| Fuente                                                                                             | Convención identificada                                                                                                   | Aplicación en esta propuesta                                                                                  |
| -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| [Bigger Applications — Multiple Files](https://fastapi.tiangolo.com/tutorial/bigger-applications/) | Paquete `app`, `__init__.py`, módulos separados, `APIRouter`, `include_router`, prefijos, tags y dependencias compartidas | `main.py` ensambla la aplicación; cada dominio registra un router; autenticación y sesiones usan `Depends`    |
| [Response Model](https://fastapi.tiangolo.com/tutorial/response-model/)                            | Modelos de respuesta explícitos para validar y filtrar la salida                                                          | Schemas públicos separados de modelos almacenados; nunca serializar el ticket completo con su correo          |
| [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/)              | Configuración en un módulo separado, variables de entorno y validación de valores; muestra `pydantic-settings`            | Mantener `config.py`, centralizar y validar configuración; no instalar otra dependencia solo por esta entrega |
| [CORS](https://fastapi.tiangolo.com/tutorial/cors/)                                                | Un origen combina protocolo, host y puerto; `CORSMiddleware` controla orígenes, métodos, headers y preflight              | Documentar el proxy de mismo origen y una allowlist explícita para acceso directo desde otro origen           |

FastAPI no impone un árbol universal ni obliga a usar MVC, repositorios o una carpeta `services`. La documentación fundamenta la composición modular y los contratos; las capas de aplicación y persistencia son una decisión propia para evitar la mezcla de reglas de Nexova con HTTP y almacenamiento.

## 4. Estructura de carpetas y módulos propuesta

Se reutiliza la ruta existente; no se crea otra API ni se duplica el monorepo. Este árbol es **objetivo**, no un inventario de archivos ya presentes:

```text
services/support-api/
  README.md
  requirements.txt
  pyproject.toml
  app/
    __init__.py
    main.py
    config.py
    auth.py
    security.py
    email_service.py
    database.py
    db.py
    models.py
    schemas.py
    incident_rules.py
    routers/
      __init__.py
      auth.py
      incidents.py
      inventory.py
      suppliers.py
    services/
      __init__.py
      auth.py
      incidents.py
      inventory.py
      suppliers.py
    repositories/
      __init__.py
      users.py
      incidents.py
      inventory.py
      suppliers.py
  scripts/
    create_user.py
  tests/
    test_auth_flows.py
    test_email_service.py
    test_incident_rules.py
    (pruebas futuras de contratos y persistencia por dominio)
```

- `main.py`: instancia FastAPI, registra routers y configura middleware, errores comunes y lifespan. Actualmente también contiene autenticación y tickets; extraerlos es trabajo futuro.
- `routers/`: un módulo por dominio, con prefijo y tags. Los routers de inventario y proveedores existentes se conservan y se adelgazan de forma incremental.
- `services/`: casos de uso, como cerrar un ticket con puntuación válida o registrar una salida sin stock negativo. Se separan del transporte para poder probarlos sin servidor HTTP.
- `repositories/`: acceso concreto a TinyDB o al almacenamiento relacional existente. No se crean interfaces genéricas ni otra librería de persistencia por anticipación; se extrae únicamente acceso usado por casos de uso.
- `schemas.py`: contratos Pydantic de entrada y salida. `models.py`: entidades persistidas del inventario. Permanecen separados: una tabla no es automáticamente una respuesta pública. Se dividirían por dominio solo si su tamaño lo justifica.
- `incident_rules.py`: reutiliza reglas de categorías, estados y satisfacción; no se duplican en cada router o en el navegador.
- `auth.py` y `security.py`: identidad autenticada, hashing y tokens; no deben confundirse con el router HTTP de autenticación.
- `database.py` y `db.py`: mantienen por ahora sus responsabilidades actuales de conexión relacional y acceso TinyDB. La convivencia es transitoria y explícita, no dos implementaciones de la misma función.
- `tests/`: mantiene las pruebas existentes y añade cobertura junto al dominio afectado cuando se implemente la separación.

Los dominios no importan routers de otros dominios. Una necesidad compartida se resuelve mediante un caso de uso o una dependencia explícita, evitando importaciones circulares y utilitarios globales sin dueño.

## 5. Endpoints y routers por dominio

Se conservan las rutas actuales para no romper el backoffice. La mezcla histórica de `/api/incidents`, `/inventory` y `/suppliers` se documenta; no se introduce `/v1` ni se renombran rutas sin un plan de compatibilidad.

| Router propuesto                      | Rutas agrupadas                                                                                                               | Criterio y acceso objetivo                                                                                                 |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `auth`, prefijo `/auth`               | `POST /login`, `GET /me`, `POST /change-password`, `POST /forgot-password`, `POST /reset-password`                            | Identidad y ciclo de credenciales. Login y recuperación sin sesión; `/me` y cambio de contraseña con JWT. No autorregistro |
| `incidents`, prefijo `/api/incidents` | `POST /`, `GET /`, `GET /summary`, `GET /{ticket_id}`, `PATCH /{ticket_id}/status`                                            | Tickets y métricas de soporte; acceso interno autenticado; filtros por estado y categoría                                  |
| `inventory`, prefijo `/inventory`     | `GET /products`, `POST /products`, `GET /products/{asset_id}`, `GET /orders`, `POST /orders/inbound`, `POST /orders/outbound` | Activos y movimientos; filtros por oficina; identidad en escrituras y protección de lecturas internas propuesta            |
| `suppliers`, prefijo `/suppliers`     | `GET /`, `POST /`, `GET /{id}`, `PATCH /{id}/rate`, `PATCH /{id}/status`, `DELETE /{id}`                                      | Directorio y cambios de proveedor; filtros por país y categoría; protección interna propuesta                              |
| Aplicación                            | `GET /health`                                                                                                                 | Estado técnico público sin credenciales, datos de negocio ni secretos                                                      |

Cada router se integra con `include_router`. Las rutas estáticas como `/summary` se declaran antes de `/{ticket_id}` para evitar interpretarlas como identificadores. Los paths con `/` en la tabla representan la raíz del prefijo, no una exigencia de cambiar las URLs actuales o sus barras finales.

**Brecha de acceso actual:** proveedores no exige JWT y las lecturas de inventario son públicas, según el README del servicio. Proteger solo la página del backoffice no protege la API. La propuesta exige autenticación para datos internos; los permisos por rol o empresa requieren acuerdo de negocio antes de implementarlos. Estos controles no se han aplicado en esta rama.

El backend mantiene la autoridad: un ticket `CLOSED` requiere satisfacción de 1 a 5 y una salida no puede dejar stock negativo. Validar en la UI mejora la experiencia, pero no sustituye esa validación del servidor.

Se propone un contrato de errores consistente con código, campo cuando proceda y mensaje sanitizado: `401` para autenticación, `403` para permiso insuficiente cuando exista política, `404` para recurso inexistente, `422` para formato inválido y `400` para una operación incompatible con el estado del negocio. Actualmente tickets y proveedores difieren entre `400` y `422`; cualquier unificación requiere actualizar consumidores y pruebas, no modificarla silenciosamente.

## 6. Frontend y backend como sistemas separados

Se conserva el **monorepo**: permite revisar conjuntamente API y consumidores y respeta la separación existente entre `uis/website` (público), `uis/backoffice` (interno) y `services/support-api` (backend). Compartir repositorio no significa compartir proceso, secretos o reglas de ejecución. Repositorios separados podrían facilitar ciclos de equipos independientes, pero esa necesidad no está documentada y añadiría coordinación de versiones.

Next.js presenta pantallas; FastAPI expone contratos HTTP/JSON y valida reglas. El frontend no accede directamente a archivos TinyDB ni a la base relacional. Los contratos se describen con schemas Pydantic y OpenAPI; un cambio incompatible requiere coordinar la API y su consumidor. No se modifica el paquete de tipos compartidos en esta entrega.

### Comunicación por API

La configuración vigente en [uis/backoffice/next.config.mjs](../uis/backoffice/next.config.mjs) usa rewrites:

```text
Navegador -> Next.js backoffice :3001 /backend/*
          -> FastAPI backend:8001 /*
          -> almacenamiento del dominio
```

El navegador utiliza una ruta relativa de su propio origen. El proxy Next.js se comunica por la red Docker; `backend` es un nombre interno y no una URL que pueda resolver el navegador. `localhost` dentro de un contenedor apunta a ese contenedor, no al backend vecino. En ejecución sin Docker, `BACKEND_INTERNAL_URL` debe apuntar a la dirección accesible desde el proceso Next.js.

El JWT viaja en `Authorization: Bearer ...` hacia la API. No se añade una sesión pública al website ni se presupone que las cuentas internas representen a clientes finales. Producción requiere HTTPS y un despliegue separado de los ajustes de desarrollo con recarga automática.

### Variables de entorno y secretos

| Configuración                                           | Dónde se consume                          | Decisión                                                                                                        |
| ------------------------------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `BACKEND_INTERNAL_URL`                                  | Servidor Next.js                          | Destino del proxy; distinto según Docker o ejecución local; no necesita exposición al navegador                 |
| `NEXT_PUBLIC_INVENTORY_API_URL`                         | Navegador, si se configura acceso directo | Es pública; nunca incluir secretos. Preferir `/backend` y configurar CORS si cambia el origen                   |
| `BACKOFFICE_ORIGIN`                                     | FastAPI                                   | Origen permitido para acceso directo; comprobar protocolo, host y puerto exactos                                |
| `FRONTEND_URL`                                          | Backend, recuperación de contraseña       | Base del enlace hacia el backoffice del entorno correcto                                                        |
| `JWT_SECRET`, credenciales de correo y conexión de base | Solo backend                              | Variables privadas inyectadas por entorno; nunca en código cliente, capturas, ejemplos con valores reales o Git |

La documentación oficial recomienda configuración centralizada y validada. Se aplica ese criterio a `config.py`; adoptar `pydantic-settings` sería una decisión de implementación posterior, no un requisito de esta propuesta. Las plantillas solo deben contener nombres y placeholders; no se sobrescribe ningún `.env` local.

### CORS

Con `/backend` el navegador llama al mismo origen del backoffice: ese recorrido no necesita abrir CORS entre navegador y API. Si se llama directamente a `:8001` desde `:3001`, cambia el puerto y por tanto el origen; hace falta `CORSMiddleware` con allowlist por entorno, métodos necesarios (`GET`, `POST`, `PATCH`, `DELETE`, `OPTIONS`) y headers `Authorization` y `Content-Type`.

El middleware actual no declara `DELETE`: habría que revisarlo antes de ofrecer eliminación de proveedores desde acceso directo cross-origin. Se evita `*` como política indiscriminada. El flujo Bearer actual no necesita cookies cross-origin; si se adopta autenticación con cookies deberán revisarse `allow_credentials`, orígenes explícitos y protección CSRF. CORS es una restricción del navegador, no autenticación ni autorización: un cliente no navegador puede llamar a la API igualmente.

## 7. Decisiones técnicas iniciales y evolución

1. **Reusar FastAPI y el backend central.** No añadir otro framework ni servicio por dominio: el stack y despliegue ya existen y son suficientes para separar responsabilidades.
2. **Conservar persistencia actual al reorganizar.** TinyDB guarda autenticación, tickets y proveedores; inventario usa almacenamiento relacional. La división de capas no exige migrar datos. Antes de producción deben evaluarse concurrencia, copias de seguridad, restauración y migraciones; no se presenta TinyDB como garantía de escalabilidad o aislamiento.
3. **Separar entradas y salidas públicas.** `customer_email` puede validarse y persistirse según el flujo vigente, pero no devolverlo ni incluirlo en mensajes de validación, exportaciones o logs. No pasar dumps o CSV sensibles a herramientas externas.
4. **Mantener cuentas administradas.** Reutilizar JWT, hashing y recuperación con tokens de un solo uso. No añadir registro público; acordar permisos explícitos antes de introducir roles.
5. **Preferir extracción incremental.** Primero routers de auth y tickets, luego casos de uso y acceso a datos cuando haya lógica mezclada. No reescribir todos los módulos ni introducir una abstracción genérica sin necesidad.
6. **Probar límites observables.** Al implementar: preservar contratos HTTP existentes; comprobar rechazo de cierre sin satisfacción, anonimización de respuestas y errores, sesión inválida y stock insuficiente. Las pruebas deben usar datos sintéticos no sensibles y almacenamiento aislado, nunca los datos reales de clientes.

No se propone una implementación de IA, una infraestructura nueva ni un cronograma con esfuerzo inventado. La aprobación del CTO y las aclaraciones de Roberto preceden al siguiente cambio funcional.

## 8. Riesgos y puntos de atención

| Riesgo                                                                  | Consecuencia                                                         | Mitigación propuesta                                                                                                       |
| ----------------------------------------------------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Mantener toda la lógica en `main.py` o duplicarla por router            | Reglas divergentes de satisfacción y cambios con efectos inesperados | Routers por dominio, casos de uso y pruebas de invariantes compartidas                                                     |
| Usar modelos almacenados como respuesta o registrar el payload completo | Exposición de correos, contraseñas o tokens                          | Schemas públicos explícitos, errores sanitizados y pruebas de ausencia de campos sensibles                                 |
| Confiar en la protección de la UI o en CORS como control de acceso      | Lectura o modificación directa de datos internos                     | Dependencias de autenticación en la API y definición posterior de permisos; cerrar brechas públicas con aprobación         |
| Validar stock solo antes de escribir sin garantizar atomicidad          | Dos salidas concurrentes pueden aceptar el mismo stock               | Caso de uso y operación de persistencia atómica; prueba de concurrencia antes de declarar la solución apta para producción |
| Confundir URL del navegador, host Docker y origen permitido             | Fallos de conexión, preflight o exposición de configuración privada  | Separar variables cliente/servidor y probar proxy y acceso directo por entorno                                             |
| Extraer capas cambiando URLs o códigos de error sin coordinación        | Ruptura del backoffice aun cuando el backend arranque                | Conservar contratos y validar consumidores antes de renombrar o unificar errores                                           |
| Tratar inicialización de desarrollo como gestión de datos de producción | Pérdida de información o cambios de esquema no controlados           | Copias verificadas, migraciones revisadas y semillas separadas de datos reales                                             |
| Prometer métricas de SLA sin datos temporales suficientes               | Decisiones operativas basadas en cifras no calculables               | Confirmar dataset, timestamps y definición de métricas con Roberto; no fabricar históricos                                 |

## 9. Matriz de cumplimiento y entrega

| Requisito de la consigna                            | Evidencia en este documento                                                                               |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Markdown dentro de `/docs`                          | `docs/ARCHITECTURE_PROPOSAL.md` en el monorepo existente                                                  |
| Patrón justificado por negocio                      | Secciones 1 y 2: soporte, reglas comunes, privacidad y ausencia de necesidad demostrada de microservicios |
| Estructura y responsabilidades                      | Sección 4: árbol objetivo y límites de cada módulo                                                        |
| Routers y endpoints FastAPI por dominio             | Sección 5: prefijos, operaciones, acceso y composición                                                    |
| Investigación real sobre FastAPI y origen explícito | Sección 3: documentación oficial y decisiones derivadas                                                   |
| Separación frontend/backend, API, entorno y CORS    | Sección 6: monorepo, proxy, variables privadas/públicas y orígenes                                        |
| Al menos dos riesgos                                | Sección 8: ocho riesgos con consecuencias y mitigaciones                                                  |
| Decisiones concretas, no código funcional           | Sección 7; esta rama no implementa el árbol ni cambia el stack                                            |

Fuente de la consigna: [Propuesta de Arquitectura de Backend — 4Geeks Academy](https://github.com/4GeeksAcademy/ai-engineering-syllabus/blob/main/content/projects/ai-eng-architectural-proposal/README.es.md).

La entrega exige subir el repositorio a GitHub y compartir el enlace según las instrucciones del instructor. Este borrador no equivale a un commit, un push o una aprobación arquitectónica. Antes de publicarlo se revisará el diff, la ausencia de secretos y el cumplimiento del flujo de commit del repositorio.
