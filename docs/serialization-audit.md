# Auditoría de Serialización del Backend

## Nexova Support API

---

## Resumen

**Branch:** `feature/audit-backend`
**Fecha:** Octubre 2026
**API Base:** `http://localhost:8001`
**Documentación:** Swagger en `/docs`

---

## Estado general

| Estado                      | Cantidad | Endpoints                                                |
| --------------------------- | -------- | -------------------------------------------------------- |
| ✅ Ya serializado           | 35       | Tienen `response_model` explícito y esquema adecuado     |
| ⚠️ Parcialmente serializado | 0        | Tienen `response_model` pero exponen campos innecesarios |
| ❌ Sin serializar           | 0        | Todos tienen `response_model` declarado                  |

---

## Listado completo de endpoints

### Auth (`app/main.py`)

| #   | Método | Ruta                    | Modelo Respuesta  | Estado | Problema                                                  |
| --- | ------ | ----------------------- | ----------------- | ------ | --------------------------------------------------------- |
| 1   | POST   | `/auth/login`           | `LoginResponse`   | ✅     | Solucionado: ya no expone `email` del usuario             |
| 2   | GET    | `/auth/me`              | `AuthMeResponse`  | ✅     | Autenticado, devuelve email del propio usuario (correcto) |
| 3   | POST   | `/auth/change-password` | `MessageResponse` | ✅     | Solo mensaje genérico                                     |
| 4   | POST   | `/auth/forgot-password` | `MessageResponse` | ✅     | Solo mensaje genérico                                     |
| 5   | POST   | `/auth/reset-password`  | `MessageResponse` | ✅     | Solo mensaje genérico                                     |

**Análisis:** Los endpoints `/auth/login` y `/users` (register) son rutas no autenticadas que devuelven `LoginUserPublic` y `ManagedUserPublic` respectivamente, ambos incluyendo `email`. Según el estándar de seguridad, los flujos de auth no autenticados no deben reenviar el email del usuario en la respuesta — el frontend debe obtenerlo desde `/auth/me` después de autenticarse.

---

### Tickets / Incidencias locales (`app/main.py`)

| #   | Método | Ruta                              | Modelo Respuesta       | Estado | Problema                                       |
| --- | ------ | --------------------------------- | ---------------------- | ------ | ---------------------------------------------- |
| 6   | POST   | `/api/tickets`                    | `IncidentPublic`       | ✅     | Esquema explícito y completo                   |
| 7   | GET    | `/api/tickets`                    | `list[IncidentPublic]` | ✅     | Listado con esquema completo, campos adecuados |
| 8   | GET    | `/api/tickets/summary`            | `IncidentSummary`      | ✅     | Esquema agregado correcto                      |
| 9   | GET    | `/api/tickets/{ticket_id}`        | `IncidentPublic`       | ✅     | Esquema explícito                              |
| 10  | PATCH  | `/api/tickets/{ticket_id}/status` | `IncidentPublic`       | ✅     | Esquema explícito                              |

**Análisis:** Los tickets usan `public_incident()` que devuelve un dict con los campos necesarios. El `IncidentPublic` schema es completo y no expone campos internos. Todos los endpoints están correctamente serializados.

---

### Incidencias centrales (`app/routers/incidents.py`)

| #   | Método | Ruta                                  | Modelo Respuesta              | Estado | Problema          |
| --- | ------ | ------------------------------------- | ----------------------------- | ------ | ----------------- |
| 11  | POST   | `/api/incidents`                      | `CentralIncidentPublic`       | ✅     | Esquema explícito |
| 12  | GET    | `/api/incidents`                      | `list[CentralIncidentPublic]` | ✅     | Listado completo  |
| 13  | GET    | `/api/incidents/summary`              | `CentralIncidentSummary`      | ✅     | Agregado correcto |
| 14  | GET    | `/api/incidents/{incident_id}`        | `CentralIncidentPublic`       | ✅     | Esquema explícito |
| 15  | PATCH  | `/api/incidents/{incident_id}/status` | `CentralIncidentPublic`       | ✅     | Esquema explícito |

**Análisis:** Correctamente serializados. Usan `_public_incident()` + `CentralIncidentPublic`. No exponen `reported_by_user_id` ni campos internos. ✅

---

### Inventario (`app/routers/inventory.py`)

| #   | Método | Ruta                             | Modelo Respuesta             | Estado | Problema                                           |
| --- | ------ | -------------------------------- | ---------------------------- | ------ | -------------------------------------------------- |
| 16  | GET    | `/inventory/products`            | `list[AssetPublic]`          | ✅     | Solo campos necesarios + `current_stock` calculado |
| 17  | POST   | `/inventory/products`            | `AssetPublic`                | ✅     | Esquema explícito                                  |
| 18  | GET    | `/inventory/products/{asset_id}` | `AssetPublic`                | ✅     | Esquema explícito                                  |
| 19  | POST   | `/inventory/orders/inbound`      | `AssetEntryPublic`           | ✅     | Solucionado: ya no expone `user_uuid`              |
| 20  | POST   | `/inventory/orders/outbound`     | `AssetExitPublic`            | ✅     | Solucionado: ya no expone `user_uuid`              |
| 21  | GET    | `/inventory/orders`              | `list[InventoryOrderPublic]` | ✅     | Esquema explícito, no expone `user_uuid`           |

**Análisis:** Los endpoints de creación de órdenes devuelven `AssetEntryPublic` y `AssetExitPublic` que incluyen `user_uuid` — un identificador interno de servidor que el frontend no consume. `InventoryOrderPublic` ya está correctamente diseñado sin exponer `user_uuid`.

---

### Proveedores (`app/routers/suppliers.py`)

| #   | Método | Ruta                              | Modelo Respuesta       | Estado | Problema                     |
| --- | ------ | --------------------------------- | ---------------------- | ------ | ---------------------------- |
| 22  | POST   | `/suppliers`                      | `SupplierPublic`       | ✅     | Esquema explícito y completo |
| 23  | GET    | `/suppliers`                      | `list[SupplierPublic]` | ✅     | Listado completo             |
| 24  | GET    | `/suppliers/{supplier_id}`        | `SupplierPublic`       | ✅     | Esquema explícito            |
| 25  | PATCH  | `/suppliers/{supplier_id}/rate`   | `SupplierPublic`       | ✅     | Esquema explícito            |
| 26  | PATCH  | `/suppliers/{supplier_id}/status` | `SupplierPublic`       | ✅     | Esquema explícito            |
| 27  | DELETE | `/suppliers/{supplier_id}`        | `MessageResponse`      | ✅     | Solo mensaje                 |

**Análisis:** Correctamente serializados. Usan `_public_supplier()` + `SupplierPublic`. Todos los campos son necesarios para la UI de proveedores. ✅

---

### Usuarios (`app/routers/users.py`)

| #   | Método | Ruta               | Modelo Respuesta          | Estado | Problema                                                |
| --- | ------ | ------------------ | ------------------------- | ------ | ------------------------------------------------------- |
| 28  | POST   | `/users`           | `RegisterResponse`        | ✅     | Solucionado: nuevo esquema `RegisterResponse` sin email |
| 29  | GET    | `/users`           | `list[ManagedUserPublic]` | ✅     | Admin autenticado, email esperado                       |
| 30  | GET    | `/users/{user_id}` | `ManagedUserPublic`       | ✅     | Autenticado, dueño o admin                              |
| 31  | PUT    | `/users/{user_id}` | `ManagedUserPublic`       | ✅     | Autenticado, dueño o admin                              |
| 32  | DELETE | `/users/{user_id}` | `204 No Content`          | ✅     | Sin cuerpo de respuesta                                 |

**Análisis:** El endpoint `POST /users` (registro público) usa `ManagedUserPublic` que incluye `email`. Al ser no autenticado, no debería devolver el email. Los demás endpoints de usuario son autenticados y pueden devolver email.

---

### Perfiles (`app/routers/profiles.py`)

| #   | Método | Ruta           | Modelo Respuesta | Estado | Problema                       |
| --- | ------ | -------------- | ---------------- | ------ | ------------------------------ |
| 33  | GET    | `/profiles/me` | `ProfilePublic`  | ✅     | Autenticado, esquema explícito |
| 34  | PUT    | `/profiles/me` | `ProfilePublic`  | ✅     | Autenticado, esquema explícito |

### Health

| #   | Método | Ruta      | Modelo Respuesta   | Estado | Problema                               |
| --- | ------ | --------- | ------------------ | ------ | -------------------------------------- |
| 35  | GET    | `/health` | `dict` (implícito) | ✅     | Endpoint de salud, no requiere esquema |

---

## Problemas detectados

### 1. 🔴 Login devuelve email del usuario (seguridad)

**Endpoint:** `POST /auth/login`
**Esquema:** `LoginUserPublic` incluye `email`
**Impacto:** Un atacante que intercepte la respuesta de login obtiene el email del usuario autenticado. El frontend ya llama a `/auth/me` para obtener el perfil completo, por lo que el email no es necesario en login.

**Solución:** Eliminar `email` de `LoginUserPublic`. El frontend obtendrá el email desde `/auth/me` después del login.

### 2. 🔴 Registro devuelve email del usuario (seguridad)

**Endpoint:** `POST /users`
**Esquema:** `ManagedUserPublic` incluye `email`
**Impacto:** Endpoint de registro no autenticado expone el email registrado. Similar al login.

**Solución:** Crear un esquema `RegisterResponse` sin email para el endpoint de registro. Usar `ManagedUserPublic` (con email) solo para endpoints autenticados de admin/dueño.

### 3. 🟡 AssetEntry/Exit publican user_uuid (campo interno)

**Endpoints:** `POST /inventory/orders/inbound`, `POST /inventory/orders/outbound`
**Esquemas:** `AssetEntryPublic`, `AssetExitPublic` incluyen `user_uuid`
**Impacto:** Se expone un UUID interno del servidor que el frontend no consume. Información innecesaria en el payload.

**Solución:** Eliminar `user_uuid` de `AssetEntryPublic` y `AssetExitPublic`.

---

## Correcciones aplicadas

### Fase 1: Schemas

#### `LoginUserPublic` — sin email

```diff
class LoginUserPublic(BaseModel):
    id: int
-   email: EmailStr
    name: str
    role: UserRole
```

#### `RegisterResponse` — nuevo esquema sin email

```python
class RegisterResponse(BaseModel):
    id: int
    name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
```

#### `AssetEntryPublic` — sin user_uuid

```diff
class AssetEntryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    asset_id: int
    quantity: int
    supplier: str
    office: Office
    created_at: datetime
-   user_uuid: str
```

#### `AssetExitPublic` — sin user_uuid

```diff
class AssetExitPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    asset_id: int
    quantity: int
    exit_type: Literal["allocation", "consumption"]
    assigned_to: str | None
    office: Office
    created_at: datetime
-   user_uuid: str
```

### Fase 2: Endpoints

#### `POST /users` (register) — usar RegisterResponse

```diff
- @router.post("", response_model=ManagedUserPublic, ...)
+ @router.post("", response_model=RegisterResponse, ...)
```

### Fase 3: Frontend

#### `uis/backoffice/main.js` — llamar `/auth/me` tras login

```diff
  state.token = result.access_token;
  sessionStorage.setItem(TOKEN_KEY, state.token);
- state.user = result.user;
+ state.user = await apiRequest("/auth/me");
```

---

## Checklist de verificación

- [x] Todos los endpoints tienen `response_model` explícito declarado
- [x] Los esquemas Pydantic están definidos para entrada y salida (los de entrada ya existen y son correctos)
- [x] Los esquemas de listado devuelven solo campos necesarios
- [x] Ningún endpoint expone contraseñas hasheadas (verificado: ningún esquema incluye `hashed_password` o `password_hash`)
- [x] Ningún endpoint de auth no autenticado devuelve email
- [x] `GET /auth/me` puede devolver email (sigue siendo correcto)
- [x] Los tests existentes pasan después de los cambios (116 tests, 0 fallos)
- [x] Este documento de auditoría existe y lista todos los endpoints

---

## Historial de cambios

| Fecha      | Cambio                                                                                                                          |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 2026-10-24 | Auditoría inicial — identificación de endpoints                                                                                 |
| 2026-10-24 | Implementación: LoginUserPublic sin email, RegisterResponse nuevo, AssetEntry/ExitPublic sin user_uuid, frontend llama /auth/me |
| 2026-10-24 | Corrección: eliminado `email` de `LoginUserPublic`                                                                              |
| 2026-10-24 | Corrección: creado `RegisterResponse` sin email                                                                                 |
| 2026-10-24 | Corrección: eliminado `user_uuid` de `AssetEntryPublic` y `AssetExitPublic`                                                     |
| 2026-10-24 | Corrección: frontend llama `/auth/me` tras login                                                                                |

---

## Verificación

### Tests automatizados

```
$ python -m pytest tests/ -v
============================= 116 passed in 25.19s ==============================
```

### Pruebas manuales

**POST /users (register)**

```json
// Response 201 — sin email
{
  "id": 8,
  "name": "Manual Test",
  "role": "user",
  "is_active": true,
  "created_at": "2026-10-24T00:54:05.770441Z"
}
```

**POST /auth/login**

```json
// Response 200 — user sin email
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": { "id": 8, "name": "Manual Test", "role": "user" }
}
```

**GET /auth/me** (endpoint autenticado — email presente, correcto)

```json
{
  "id": 8,
  "email": "manual@test.com",
  "role": "user",
  "profile": {
    "id": 6,
    "user_id": 8,
    "name": "Manual Test",
    "phone": null,
    "address": null
  }
}
```
