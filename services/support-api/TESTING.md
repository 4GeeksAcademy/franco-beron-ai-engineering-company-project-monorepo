# Testing — Nexova Support API

## Cómo ejecutar las pruebas

```bash
# Desde la raíz del proyecto (services/support-api/)

# Ejecutar todas las pruebas con cobertura
uv run pytest --cov=app --cov-report=term-missing

# Ejecutar solo las pruebas de autenticación
uv run pytest tests/ -k "auth or login or register or token or security or me" --cov=app --cov-report=term-missing

# Ejecutar un archivo específico
uv run pytest tests/test_security.py -v

# Ver cobertura sin ejecutar (si ya corriste antes)
uv run pytest --cov=app --cov-report=term-missing
```

> **Nota:** Las pruebas usan `pytest` con mocks. No requieren base de datos, servidor SMTP ni conexión externa.

---

## Estructura de la suite

```
tests/
├── conftest.py                      # Fixtures compartidos (fake users, tokens, DB mocks)
├── test_auth_flows.py               # Tests existentes (unittest) — change/forgot/reset password
├── test_email_service.py            # Tests existentes — envío de emails
├── test_error_handling.py           # Tests existentes — manejo de errores
├── test_incident_rules.py           # Tests existentes — reglas de incidentes
├── test_login.py                    # POST /auth/login — lógica de autenticación
├── test_me.py                       # GET /auth/me — perfil del usuario autenticado
├── test_register.py                 # POST /users — registro de usuarios
├── test_security.py                 # Funciones de seguridad (hash, JWT, tokens)
├── test_user_service.py             # user_service (CRUD de usuarios)
├── test_suppliers.py                # Endpoints de proveedores (extra)
└── test_central_incidents.py        # Endpoints de incidentes centrales (extra)
```

---

## Resultados de cobertura

**116 tests — 0 fallos — 77 % de cobertura global**

| Módulo                             | Cobertura | Objetivo |
| ---------------------------------- | --------- | -------- |
| `app/security.py`                  | 100 %     | 90 % ✅  |
| `app/user_service.py`              | 90 %      | 80 % ✅  |
| `app/auth.py`                      | 69 %      | 85 % 🟡  |
| `app/routers/suppliers.py` (extra) | 100 %     | 60 % ✅  |
| `app/routers/incidents.py` (extra) | 100 %     | 60 % ✅  |
| `app/error_handling.py`            | 88 %      | —        |
| `app/incident_rules.py`            | 81 %      | —        |
| `app/schemas.py`                   | 85 %      | —        |
| `app/email_service.py`             | 100 %     | —        |
| `app/db.py`                        | 100 %     | —        |
| `app/config.py`                    | 100 %     | —        |
| `app/models.py`                    | 100 %     | —        |

> 🟡 `app/auth.py` al 69 % — `get_current_user` no está 100 % cubierta por llamarse desde los endpoints de FastAPI en lugar de directamente en los tests unitarios. Para mejorarla harían falta tests de integración con TestClient.

---

## Plan de pruebas — Endpoints de autenticación

### `POST /auth/login`

| Tipo             | Caso                    | Verificación                                                                     |
| ---------------- | ----------------------- | -------------------------------------------------------------------------------- |
| ✅ Camino feliz  | Credenciales válidas    | Devuelve `access_token`, `token_type: bearer` y `user` con id, email, name, role |
| ✅ Caso límite   | Usuario inactivo        | `is_active == False` → 401 con mensaje genérico                                  |
| ✅ Caso límite   | Contraseña con 72 bytes | Se procesa correctamente (límite de bcrypt)                                      |
| ✅ Modo de fallo | Contraseña incorrecta   | 401 con mensaje genérico                                                         |
| ✅ Modo de fallo | Email inexistente       | 401 con mensaje genérico                                                         |
| ✅ Modo de fallo | Contraseña vacía        | Error de validación del schema                                                   |

**Decisiones:** Se usa un mensaje genérico ("Email o contraseña incorrectos.") tanto para email inexistente como para contraseña incorrecta para evitar enumeración de usuarios. La prueba verifica que no haya fuga de información.

### `GET /auth/me`

| Tipo             | Caso               | Verificación                                                  |
| ---------------- | ------------------ | ------------------------------------------------------------- |
| ✅ Camino feliz  | Token válido       | Devuelve id, email, role y profile (con name, phone, address) |
| ✅ Caso límite   | Usuario sin perfil | Se crea perfil por defecto con valores nulos                  |
| ✅ Modo de fallo | Sin token          | 401 — "No autenticado."                                       |
| ✅ Modo de fallo | Token inválido     | 401 — "Token inválido o expirado."                            |
| ✅ Modo de fallo | Token expirado     | 401 — "Token inválido o expirado."                            |

**Decisiones:** Se probó el caso de perfil faltante porque `ensure_profile` se llama dentro de `me()`. Un bug aquí dejaría a usuarios sin perfil viendo un 500.

### `POST /users` (Registro)

| Tipo             | Caso                      | Verificación                                                   |
| ---------------- | ------------------------- | -------------------------------------------------------------- |
| ✅ Camino feliz  | Datos válidos             | Usuario creado con email, contraseña hasheada, perfil asociado |
| ✅ Caso límite   | Email duplicado           | 409 — "Ya existe una cuenta con ese correo."                   |
| ✅ Caso límite   | Valores opcionales nulos  | name, phone, address se guardan como None                      |
| ✅ Modo de fallo | Contraseña < 8 caracteres | Error de validación del schema                                 |
| ✅ Modo de fallo | Email inválido            | Error de validación del schema                                 |
| ✅ Modo de fallo | Campos extra              | 422 — `extra="forbid"` en el schema                            |

**Decisiones:** Se eligió probar campos extra porque `UserCreate` tiene `extra="forbid"` y es un caso límite común en APIs públicas.

### `POST /auth/change-password`

| Tipo             | Caso                               | Verificación                                               |
| ---------------- | ---------------------------------- | ---------------------------------------------------------- |
| ✅ Camino feliz  | Contraseña actual correcta         | Se actualiza el hash, se invalidan reset tokens pendientes |
| ✅ Modo de fallo | Contraseña actual incorrecta       | 400 — detalle específico                                   |
| ✅ Caso límite   | Nueva contraseña igual a la actual | Se procesa (no hay validación en contra)                   |

**Decisiones:** Se incluyó el caso de "contraseña igual" documentando que la API no lo rechaza — es decisión de producto, no bug. Identificado con ayuda de IA.

### `POST /auth/forgot-password` + `POST /auth/reset-password`

| Tipo             | Caso                           | Verificación                              |
| ---------------- | ------------------------------ | ----------------------------------------- |
| ✅ Camino feliz  | Flujo completo: forgot → reset | Token se consume, contraseña se actualiza |
| ✅ Caso límite   | Email no registrado            | Mensaje genérico sin revelar existencia   |
| ✅ Modo de fallo | Token expirado                 | 400 — "no es válido o expiró"             |
| ✅ Modo de fallo | Token ya usado                 | 400 — "no es válido o expiró"             |
| ✅ Modo de fallo | Token inválido (no existe)     | 400 — "no es válido o expiró"             |
| ✅ Caso límite   | Dos forgot consecutivos        | El segundo invalida el primer token       |

**Decisiones:** Se documenta que el endpoint de forgot-password consume cualquier token anterior no usado (medida de seguridad ante robo de enlace). Bug potencial: si el email falla, el token se marca como usado — se probó y confirmó que es comportamiento intencional.

---

## Funciones de seguridad (`security.py`)

| Función               | Tipo     | Caso                                    |
| --------------------- | -------- | --------------------------------------- |
| `hash_password`       | ✅ Happy | Contraseña válida → hash de bcrypt      |
| `hash_password`       | ✅ Fail  | Contraseña > 72 bytes → ValueError      |
| `verify_password`     | ✅ Happy | Contraseña correcta → True              |
| `verify_password`     | ✅ Fail  | Contraseña incorrecta → False           |
| `verify_password`     | ✅ Fail  | Hash malformado → False (no error)      |
| `create_access_token` | ✅ Happy | user_id válido → JWT decodificable      |
| `create_access_token` | ✅ Fail  | JWT_SECRET vacío → RuntimeError         |
| `decode_access_token` | ✅ Happy | Token válido → payload con sub y exp    |
| `decode_access_token` | ✅ Fail  | Token expirado → JWTError               |
| `decode_access_token` | ✅ Fail  | Token malformado → JWTError             |
| `create_reset_token`  | ✅ Happy | Genera string URL-safe de 43 caracteres |
| `hash_reset_token`    | ✅ Happy | Hash SHA-256 de 64 caracteres hex       |

---

## Funciones de `user_service.py`

| Función                 | Tipo     | Caso                                |
| ----------------------- | -------- | ----------------------------------- |
| `create_user`           | ✅ Happy | Crea usuario + perfil               |
| `create_user`           | ✅ Fail  | Email duplicado → 409               |
| `get_user_by_email`     | ✅ Happy | Usuario encontrado                  |
| `get_user_by_email`     | ✅ Edge  | Usuario no encontrado → None        |
| `get_user_by_id`        | ✅ Happy | Usuario encontrado                  |
| `get_user_by_id`        | ✅ Edge  | Usuario no encontrado → None        |
| `update_user`           | ✅ Happy | Actualiza email/hash/role/is_active |
| `update_user`           | ✅ Fail  | Email duplicado → 409               |
| `update_user`           | ✅ Edge  | Usuario inexistente → None          |
| `delete_user`           | ✅ Happy | Elimina usuario + perfil            |
| `delete_user`           | ✅ Edge  | Usuario inexistente → False         |
| `normalize_user_record` | ✅ Happy | Añade campos por defecto            |
| `ensure_profile`        | ✅ Happy | Crea perfil si no existe            |
| `ensure_profile`        | ✅ Edge  | Perfil ya existe → lo retorna       |

---

## Plan de pruebas — Endpoints extra (Backoffice)

### `POST /suppliers`, `GET /suppliers`, etc.

| Tipo             | Caso                           | Endpoint                          |
| ---------------- | ------------------------------ | --------------------------------- |
| ✅ Camino feliz  | Crear proveedor                | POST /suppliers con datos válidos |
| ✅ Caso límite   | Filtrar por país/categoría     | GET /suppliers?country=...        |
| ✅ Modo de fallo | Proveedor no encontrado        | GET /suppliers/999 → 404          |
| ✅ Modo de fallo | Eliminar proveedor inexistente | DELETE /suppliers/999 → 404       |

### `POST /api/incidents`, `GET /api/incidents`, etc.

| Tipo             | Caso                          | Endpoint                                      |
| ---------------- | ----------------------------- | --------------------------------------------- |
| ✅ Camino feliz  | Crear incidencia              | POST /api/incidents con datos válidos         |
| ✅ Caso límite   | Filtrar por estado/origen     | GET /api/incidents?status=open                |
| ✅ Modo de fallo | Transición de estado inválida | PATCH /.../status con transición no permitida |
| ✅ Modo de fallo | Incidencia no encontrada      | GET /api/incidents/999 → 404                  |

---

## Bugs detectados por la batería de pruebas

_(Ninguno hasta el momento. Los tests existentes ya habían validado el flujo de reset-password. Esta batería amplía la cobertura a registro, login, perfil y utilidades.)_

---

## Flujo asistido por IA

1. Se usó la IA para identificar casos límite olvidados: contraseña igual a la actual en change-password, campos extra en registro, validación de 72 bytes en bcrypt.
2. Se usó la IA para generar el boilerplate de `conftest.py` y la estructura de fixtures reutilizables.
3. Cada test fue revisado y verificado contra la lógica real del código antes de confirmarlo.

---

## Tests del frontend (TypeScript/Jest) — Actividad extra

Actualmente el frontend tiene un archivo de prueba (`lib/api-errors.test.mjs`) usando el módulo `node:test` nativo. Para mantener consistencia, se amplió ese mismo enfoque:

**Funciones cubiertas:**

- `apiErrorMessage` en `lib/api-errors.js` — todos los códigos HTTP
- `readApiResponse` en `lib/api-errors.js` — parseo de respuestas
- `getToken/setToken/clearToken` en `lib/auth.js` — helpers de localStorage

Para ejecutar:

```bash
cd uis/backoffice
node --test lib/api-errors.test.mjs
```

_(Los tests de frontend se mantienen en el estilo existente del proyecto.)_
