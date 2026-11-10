# Informe técnico: caching

Fecha: 2026-11-10
Rama: `feature/caching-optimisation`

## Alcance y método

Se revisaron las rutas FastAPI y los flujos Next.js existentes antes de elegir candidatos. No hay telemetría de producción disponible; las frecuencias de la matriz son estimaciones derivadas de cómo el backoffice usa las rutas, no conteos observados. El middleware `api.timing` registra `METHOD PATH -> STATUS | ms` por petición y omite query strings para no registrar valores enviados por el cliente.

Para medir el coste repetido se ejecutó `python -m scripts.benchmark_caching` desde `services/support-api/`. El script usó TestClient, por lo que las mediciones atraviesan el middleware y los handlers FastAPI, con siete muestras frías (caché invalidada antes de cada request) y siete calientes después de precalentar la clave.

| Volumen de prueba     |                                            Antes |                                                Después |
| --------------------- | -----------------------------------------------: | -----------------------------------------------------: |
| Inventario SQLModel   | Semilla local: 6 activos, 5 entradas y 3 salidas | 250 activos, 5.000 entradas y 5.000 salidas sintéticas |
| Incidencias centrales |              Sin dataset de rendimiento incluido |                200.000 incidencias sintéticas variadas |

El benchmark usa SQLite `StaticPool` en memoria y datos ficticios sin emails ni descripciones de clientes. No conecta a Supabase, no modifica el inventario real ni fabrica histórico de Nexova. Al importar `app.database` puede inicializarse el esquema vacío del fallback SQLite habitual, pero los registros sintéticos se insertan únicamente en el motor en memoria. La comparación fría/caliente fuerza misses en el mismo handler, no es una comparación entre dos despliegues. Son medianas locales de una ejecución; no representan latencia de producción ni garantizan el mismo resultado en otra máquina.

| Endpoint                     | Mediana fría | Mediana caliente | Reducción observada |
| ---------------------------- | -----------: | ---------------: | ------------------: |
| `GET /inventory/products`    |    136,74 ms |          5,93 ms |              95,7 % |
| `GET /api/incidents/summary` |     92,46 ms |          4,98 ms |              94,6 % |

## Decisiones en el frontend

- `SupplierForm` se carga con `next/dynamic` solo al abrir el alta de proveedor. Es un formulario extenso y opcional; usuarios que solo consultan el directorio no descargan su módulo al entrar a la ruta.
- `InventoryOrdersTable` se carga de forma dinámica cuando termina la consulta y existe al menos un movimiento. Su tabla y formato de fechas no se necesitan durante la carga, ante un error ni en el estado vacío.
- En el catálogo, `useMemo` agrega `totalUnits`, `lowStock` y `outOfStock` recorriendo una vez todos los activos. Las métricas se recalculan solo cuando cambia la referencia de `products`, no en los renders causados por otros estados de la página. El beneficio se estima como evitar recorridos O(n) redundantes cuando el catálogo crezca; no se afirma una mejora medida con React Profiler porque no se dispone de una captura de profiling.

## Inventario y evaluación de endpoints

La frecuencia es una estimación funcional, no telemetría. `O(n)` representa recorridos de tablas o listas y `O(1)` una lectura por ID/documento.

| Endpoint                                    | Coste de operación                          | Frecuencia estimada                            | Cambio de datos / decisión                                                                                                         |
| ------------------------------------------- | ------------------------------------------- | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `GET /health`                               | O(1)                                        | Alta, health checks                            | Constante; no cachear, el handler ya es trivial.                                                                                   |
| `POST /auth/login`                          | Alto, verificación bcrypt                   | Media                                          | Dependiente de credenciales y estado de cuenta; no cachear respuestas de autenticación.                                            |
| `GET /auth/me`                              | O(1), usuario y perfil                      | Alta, navegación protegida                     | Perfil y rol pueden cambiar; respuesta privada, no cachear.                                                                        |
| `POST /auth/change-password`                | Alto, bcrypt y escrituras                   | Baja                                           | Mutación y secreto por petición; no cachear.                                                                                       |
| `POST /auth/forgot-password`                | Lookup y servicio externo de email          | Baja                                           | Genera/invalida tokens; respuesta genérica de seguridad, no cachear.                                                               |
| `POST /auth/reset-password`                 | Verificación, bcrypt y escrituras           | Baja                                           | Token de un uso; no cachear.                                                                                                       |
| `POST /users`                               | Hash bcrypt y escrituras TinyDB             | Baja                                           | Crea una cuenta; mutación, no cachear.                                                                                             |
| `GET /users`                                | O(n), lista de usuarios                     | Baja, administración                           | Cambios poco frecuentes, pero contiene datos de cuentas; no cachear.                                                               |
| `GET /users/{user_id}`                      | O(1), lookup                                | Baja                                           | Datos personales mutables; no cachear.                                                                                             |
| `PUT /users/{user_id}`                      | Lookup y escritura; bcrypt si cambia clave  | Baja                                           | Mutación de cuenta; no cachear.                                                                                                    |
| `DELETE /users/{user_id}`                   | O(1), lookup y escritura                    | Baja                                           | Mutación de cuenta; no cachear.                                                                                                    |
| `GET /profiles/me`                          | O(1), lookup TinyDB                         | Alta, navegación protegida                     | Perfil privado y editable; no cachear.                                                                                             |
| `PUT /profiles/me`                          | O(1) y escritura TinyDB                     | Baja                                           | Mutación del perfil; no cachear.                                                                                                   |
| `POST /api/tickets`                         | O(n) para generar ID y escritura            | Media                                          | Cada ticket cambia el conjunto y contiene email en almacenamiento; no cachear.                                                     |
| `GET /api/tickets`                          | O(n), filtros en memoria                    | Media                                          | Tickets cambian con altas/estados; respuesta interna con datos sensibles de soporte; no cachear.                                   |
| `GET /api/tickets/summary`                  | O(n), agregación                            | Baja, ruta legacy                              | Cambia con tickets y se solapa con el gestor central actual; no cachear hasta confirmar uso y aislamiento.                         |
| `GET /api/tickets/{ticket_id}`              | O(n), búsqueda TinyDB                       | Baja                                           | Ticket mutable y consulta individual; no cachear.                                                                                  |
| `PATCH /api/tickets/{ticket_id}/status`     | O(n) y escritura TinyDB                     | Media                                          | Mutación de ticket; no cachear.                                                                                                    |
| `POST /api/incidents`                       | Validación e inserción TinyDB               | Media                                          | Mutación; invalida el resumen cacheado.                                                                                            |
| `GET /api/incidents`                        | O(n), filtros sobre todos los registros     | Alta en la vista de soporte                    | Los registros cambian y hay muchas combinaciones de filtros; no cachear la lista.                                                  |
| `GET /api/incidents/summary`                | O(n), agrega cuatro dimensiones             | Media-alta, entrada y actualización del gestor | Estable entre escrituras; cacheado 15 s, con clave por usuario e invalidación al crear/cambiar estado.                             |
| `GET /api/incidents/{incident_id}`          | O(1), lookup TinyDB                         | Baja                                           | Una incidencia puede cambiar de estado; no cachear.                                                                                |
| `PATCH /api/incidents/{incident_id}/status` | Lookup y escritura TinyDB                   | Media                                          | Mutación; invalida el resumen cacheado.                                                                                            |
| `POST /suppliers`                           | Inserción TinyDB                            | Baja                                           | Mutación; el listado se refresca tras el alta.                                                                                     |
| `GET /suppliers`                            | O(n), filtros en memoria                    | Media                                          | Cambios poco frecuentes, pero incluye emails de contacto; no cachear.                                                              |
| `GET /suppliers/{supplier_id}`              | O(1), lookup TinyDB                         | Baja                                           | Respuesta con datos comerciales de contacto; no cachear.                                                                           |
| `PATCH /suppliers/{supplier_id}/rate`       | Lookup y escritura TinyDB                   | Baja                                           | Mutación de tarifa; no cachear.                                                                                                    |
| `PATCH /suppliers/{supplier_id}/status`     | Lookup y escritura TinyDB                   | Baja                                           | Mutación de estado; no cachear.                                                                                                    |
| `DELETE /suppliers/{supplier_id}`           | Lookup y eliminación TinyDB                 | Baja                                           | Mutación; no cachear.                                                                                                              |
| `GET /inventory/products`                   | O(a) más dos agregaciones SQL por activo    | Alta: catálogo y formularios de movimiento     | Los movimientos cambian el stock; cacheado 30 s y además invalidado tras alta de activo o movimiento. Clave por usuario y oficina. |
| `POST /inventory/products`                  | Lookup de SKU, inserción y cálculo de stock | Baja                                           | Mutación; invalida el listado de activos.                                                                                          |
| `GET /inventory/products/{asset_id}`        | Lookup y dos agregaciones SQL               | Media, formulario de salida                    | El stock puede cambiar con cada movimiento; no cachear para conservar la validación fresca.                                        |
| `POST /inventory/orders/inbound`            | Validación y escritura SQL                  | Media                                          | Aumenta stock; invalida el listado de activos.                                                                                     |
| `POST /inventory/orders/outbound`           | Lock, agregados de stock y escritura SQL    | Media                                          | Reduce stock; invalida el listado de activos.                                                                                      |
| `GET /inventory/orders`                     | O(e+s+a), unión en memoria y ordenación     | Media, página de historial                     | Cambia con cada movimiento y contiene el responsable; no cachear.                                                                  |

## Decisiones en el backend

Se implementó una caché en proceso sin dependencias externas. Usa `RLock`, copia profunda al leer y escribir para que el consumidor no mute el valor compartido, y limita la memoria a 256 claves con expulsión LRU. La clave incluye namespace y `doc_id` del usuario; el catálogo añade `office`. Si no puede obtenerse una identidad autenticada, el handler omite la caché. Los filtros y usuarios nunca comparten la misma entrada.

| Endpoint cacheado            | Coste y frecuencia                                                              |  TTL | Clave e invalidación                                                                                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------- | ---: | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /inventory/products`    | N+1 agregados SQL; lo consultan catálogo y formularios.                         | 30 s | `(inventory-products, user_id, office)`. Se invalida tras `POST /inventory/products`, `POST /inventory/orders/inbound` y `POST /inventory/orders/outbound`. |
| `GET /api/incidents/summary` | Recorrido y cuatro agregaciones; se carga al abrir el gestor y tras mutaciones. | 15 s | `(central-incident-summary, user_id)`. Se invalida tras `POST /api/incidents` y `PATCH /api/incidents/{incident_id}/status`.                                |

La invalidación ocurre tras confirmar la escritura. Un contador de generación evita que una lectura iniciada antes de esa escritura vuelva a guardar un resultado obsoleto después de la invalidación. Si una petición de lectura ya estaba en curso cuando se confirmó la escritura, esa respuesta individual puede reflejar su snapshot anterior, pero no queda almacenada para peticiones posteriores.

## Intercambio entre frescura y rendimiento

El stock interno acepta hasta 30 segundos de antigüedad como límite de respaldo porque todas las escrituras locales relevantes invalidan el catálogo inmediatamente; la duración cubre lecturas repetidas sin ocultar movimientos normales. El resumen de incidencias usa 15 segundos por ser una cifra operativa que los supervisores consultan y esperan ver actualizada pronto. En una instancia, la invalidación reduce la ventana real a cero para las siguientes peticiones del mismo proceso; el TTL sigue siendo la protección ante errores de invalidación y el máximo de antigüedad entre procesos.

La caché es por proceso. Si Uvicorn se ejecuta con varios workers o hay varias réplicas, una escritura no invalida las cachés de los otros procesos; estas pueden servir datos antiguos hasta que venza el TTL. Si el despliegue escala de ese modo, la siguiente evolución debería usar Redis o invalidación distribuida. No se añadió infraestructura para el despliegue actual de un único worker.

## Qué no se cacheó y por qué

- `GET /api/tickets` no se cachea: devuelve detalle de soporte, el conjunto puede cambiar con frecuencia y el handler no ofrece un filtro de propietario con el cual reducir el alcance. Que la respuesta pública omita `customer_email` no elimina su sensibilidad operativa.
- `GET /inventory/products/{asset_id}` no se cachea: el formulario de salida necesita validar el stock disponible actual y una entrada de caché podría ocultar movimientos recientes.
- `GET /suppliers` no se cachea aunque el catálogo sea relativamente estable: contiene email de contacto y el coste observado en el dataset actual no justifica mantener otra copia sensible.

## Validación

- `python -m scripts.benchmark_caching`: completado con datos sintéticos en memoria; incluye comprobaciones de aislamiento por usuario, TTL, invalidación y rechazo de escrituras de caché obsoletas.
- `python -m pytest -q tests/test_central_incidents.py tests/test_error_handling.py`: 21 pruebas aprobadas.
- `cd uis/backoffice && npx next build`: compilación de producción aprobada.
- Las medianas de esta sección son evidencia local acotada; los logs de `api.timing` deben observarse bajo tráfico real antes de ajustar TTL o ampliar la lista de candidatos.
