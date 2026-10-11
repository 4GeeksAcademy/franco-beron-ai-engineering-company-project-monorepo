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

Primero inicia la API siguiendo [`services/support-api/README.md`](../../services/support-api/README.md) y configura un `JWT_SECRET` local. Para entrar, crea una cuenta desde `/register` o provisiónala con `python -m scripts.create_user`.

Después, desde el backoffice:

```bash
cd uis/backoffice
BACKEND_INTERNAL_URL=http://127.0.0.1:8001 npm run dev -- --port 3001
```

Abrir `http://127.0.0.1:3001/`.

## Acceso y tickets

- El panel requiere iniciar sesión; el registro está disponible públicamente en `/register`.
- Las cuentas pueden crearse desde la propia app (`/register`) o provisionarse con `python -m scripts.create_user` desde `services/support-api/`.
- La sesión se guarda en `localStorage` bajo `nexova_support_token` y se envía como `Authorization: Bearer <token>` en cada llamada protegida.
- La pantalla de acceso permite recuperar y restablecer contraseñas con Resend configurado en `.env`.
- Las personas autenticadas pueden cambiar su contraseña validando la actual.
- La recuperación se envía a la cuenta interna; no utiliza ni muestra `customer_email` de tickets.
- Los tickets usan las categorías, estados y campos de `CONTEXT.md`.
- El correo del cliente se captura para el registro, pero no aparece en listados, estadísticas ni mensajes de error.
- El panel comienza sin tickets históricos porque el CSV real no está incluido en este repositorio.

## Autenticación (AUTH-02)

Flujo completo de autenticación en el frontend:

| Ruta               | Uso                                                                                        |
| ------------------ | ------------------------------------------------------------------------------------------ |
| `/login`           | Inicio de sesión; guarda el token en `localStorage` y redirige a la vista de retorno.      |
| `/register`        | Alta de cuenta pública; valida en cliente, crea el usuario y hace login automático.        |
| `/account/profile` | Consulta y edición del perfil propio (nombre, teléfono, dirección) vía `PUT /profiles/me`. |

- La utilidad compartida es `lib/auth.js`: `getToken`, `setToken`, `clearToken`, `isAuthenticated`, `redirectToLogin`, `login`, `register`, `getCurrentUser` y `updateProfile`.
- Todas las rutas del panel (excepto `/login` y `/register`) verifican la sesión con `/auth/me` y redirigen a `/login?next=...` si no hay token válido.
- Un `401` de la API limpia el token y redirige a `/login`.
- El cierre de sesión limpia `localStorage` y vuelve a `/login`.
- El sitio público (`uis/website/`) queda intacto y no requiere autenticación.

El token se almacena en `localStorage` (persiste entre pestañas y sesiones del navegador).

## Alcance actual

- Ruta `/` protegida por login interno.
- Consola operativa responsive con navegacion lateral en escritorio y barra compacta en movil.
- Sistema visual accesible con foco visible, controles tactiles de al menos 44 px y movimiento reducido cuando el sistema lo solicita.
- Indicadores de SLA, resumen de tickets, filtros, estados y feedback de carga/error diferenciados visualmente.
- Resumen operativo, alta y seguimiento de tickets alineados con `CONTEXT.md`.

## Gestión de inventario

La sección de inventario reutiliza la sesión JWT guardada por el login existente y el proxy `/backend` de Next.js. No requiere una segunda aplicación ni almacena tokens en URLs.

| Ruta                                    | Uso                                                                       |
| --------------------------------------- | ------------------------------------------------------------------------- |
| `/backoffice/inventory/products`        | Catálogo de assets, oficina, SKU, stock calculado e indicadores de nivel. |
| `/backoffice/inventory/orders/inbound`  | Formulario para registrar entradas de proveedor.                          |
| `/backoffice/inventory/orders/outbound` | Asignación o consumo, con stock consultado al elegir el asset.            |
| `/backoffice/inventory/orders`          | Historial de solo lectura con tipo, fecha y `user_uuid`.                  |

Las cuatro rutas verifican la sesión con `/auth/me` y redirigen a `/login?next=...` con un destino de retorno si no hay una sesión válida. Las llamadas de inventario están centralizadas en `lib/inventory.js`; los errores HTTP se muestran en la página. Una salida por encima de las existencias avisa antes del envío y los errores `400` de la API aparecen junto al campo de cantidad.

El catálogo marca como bajo el stock menor que cinco unidades y como agotado el stock cero. Estos indicadores son orientativos; el backend calcula el stock real y valida cada salida.

En Docker, el cliente usa `/backend` por defecto y Next reenvía las solicitudes a `backend:8001`. Para desarrollo sin Docker se puede crear `.env.local` en `uis/backoffice` con:

```env
NEXT_PUBLIC_INVENTORY_API_URL=http://127.0.0.1:8001
```

Ese archivo está ignorado por Git. La URL solo configura el endpoint del backend; nunca coloques tokens ni credenciales de Supabase en variables `NEXT_PUBLIC_*`.

## Auditoría de errores

- Los clientes de inventario, proveedores e incidencias capturan fallos de red y JSON inválido y tienen un timeout de 15 segundos. Los mensajes no muestran códigos HTTP ni texto interno del servidor.
- Los listados, resumen, autenticación y stock separan carga, éxito y error. Las transiciones de estado en efectos equivalen a limpiar la carga; los formularios usan `finally` o reemplazan la vista al finalizar.
- Las cargas fallidas permiten reintentar. Los formularios conservan una acción de envío y el stock permite volver a consultar sin recargar la página.
- Los campos opcionales de resúmenes, categorías y activos usan fallbacks para no romper el renderizado ante valores nulos.

Validaciones desde esta carpeta:

```bash
node --experimental-default-type=module --test lib/api-errors.test.mjs
npx next build
```

Las pruebas de clientes simulan desconexión, HTTP 500, JSON inválido y respuestas nulas, sin acceder a datos reales. La prueba visual de los estados carga/error/reintento requiere un navegador; no queda cubierta por el build.
