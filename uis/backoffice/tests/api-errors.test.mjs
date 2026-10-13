/**
 * Tests unitarios para funciones de utilidad del frontend.
 *
 * Funciones cubiertas:
 *   - apiErrorMessage (api-errors.js) — mapeo de códigos HTTP a mensajes
 *   - readApiResponse  (api-errors.js) — parseo de respuestas HTTP
 *   - getToken / setToken / clearToken (auth.js) — helpers localStorage
 *
 * Cada función tiene como mínimo: un camino feliz y un modo de fallo.
 *
 * Uso:
 *   node --test tests/api-errors.test.mjs
 */

import assert from "node:assert/strict";
import test from "node:test";

// ---------------------------------------------------------------------------
// Setup: mock global window with localStorage
// ---------------------------------------------------------------------------
const store = {};
globalThis.window = {
  localStorage: {
    getItem: (k) => store[k] ?? null,
    setItem: (k, v) => {
      store[k] = v;
    },
    removeItem: (k) => {
      delete store[k];
    },
  },
  location: { pathname: "/", search: "", assign: () => {} },
};

// ---------------------------------------------------------------------------
// apiErrorMessage
// ---------------------------------------------------------------------------

test("apiErrorMessage: 401 retorna mensaje de sesión terminada", async () => {
  const { apiErrorMessage } = await import("../lib/api-errors.js");
  const msg = apiErrorMessage(401);
  assert.ok(msg.includes("sesión") || msg.includes("Sesión"));
  assert.ok(/inicia sesión/i.test(msg));
});

test("apiErrorMessage: 403 retorna mensaje de permiso denegado", async () => {
  const { apiErrorMessage } = await import("../lib/api-errors.js");
  const msg = apiErrorMessage(403);
  assert.ok(msg.includes("permiso"));
});

test("apiErrorMessage: 404 retorna mensaje de registro no disponible", async () => {
  const { apiErrorMessage } = await import("../lib/api-errors.js");
  const msg = apiErrorMessage(404);
  assert.ok(msg.includes("registro") || msg.includes("actualiza"));
});

test("apiErrorMessage: 400 y 422 retornan mensaje de formulario", async () => {
  const { apiErrorMessage } = await import("../lib/api-errors.js");
  assert.ok(/formulario/.test(apiErrorMessage(400)));
  assert.ok(/formulario/.test(apiErrorMessage(422)));
});

test("apiErrorMessage: código desconocido retorna mensaje genérico", async () => {
  const { apiErrorMessage } = await import("../lib/api-errors.js");
  const msg = apiErrorMessage(503);
  assert.ok(msg.includes("No se pudo completar"));
});

test("apiErrorMessage: código undefined retorna mensaje genérico", async () => {
  const { apiErrorMessage } = await import("../lib/api-errors.js");
  const msg = apiErrorMessage(undefined);
  assert.ok(msg.includes("No se pudo completar"));
});

// ---------------------------------------------------------------------------
// readApiResponse
// ---------------------------------------------------------------------------

test("readApiResponse: respuesta ok con json object retorna el payload", async () => {
  const { readApiResponse } = await import("../lib/api-errors.js");
  const res = {
    ok: true,
    status: 200,
    json: async () => ({ id: 1, name: "test" }),
  };
  const result = await readApiResponse(res);
  assert.deepStrictEqual(result, { id: 1, name: "test" });
});

test("readApiResponse: status 204 retorna null", async () => {
  const { readApiResponse } = await import("../lib/api-errors.js");
  const res = { ok: true, status: 204, json: async () => ({}) };
  const result = await readApiResponse(res);
  assert.strictEqual(result, null);
});

test("readApiResponse: no-ok 404 lanza error con mensaje mapeado", async () => {
  const { readApiResponse } = await import("../lib/api-errors.js");
  const res = { ok: false, status: 404, json: async () => ({}) };
  await assert.rejects(readApiResponse(res), (err) =>
    /registro/.test(err.message),
  );
});

test("readApiResponse: no-ok 401 lanza error con mensaje mapeado", async () => {
  const { readApiResponse } = await import("../lib/api-errors.js");
  const res = { ok: false, status: 401, json: async () => ({}) };
  await assert.rejects(readApiResponse(res), (err) =>
    /sesión/.test(err.message),
  );
});

test("readApiResponse: json inválido lanza error de respuesta inválida", async () => {
  const { readApiResponse } = await import("../lib/api-errors.js");
  const res = {
    ok: true,
    status: 200,
    json: async () => {
      throw new SyntaxError("Unexpected token");
    },
  };
  await assert.rejects(readApiResponse(res), (err) =>
    /respuesta inválida/.test(err.message),
  );
});

test("readApiResponse: payload null lanza error de respuesta inválida", async () => {
  const { readApiResponse } = await import("../lib/api-errors.js");
  const res = { ok: true, status: 200, json: async () => null };
  await assert.rejects(readApiResponse(res), (err) =>
    /respuesta inválida/.test(err.message),
  );
});

test("readApiResponse: payload string lanza error de respuesta inválida", async () => {
  const { readApiResponse } = await import("../lib/api-errors.js");
  const res = { ok: true, status: 200, json: async () => "cadena" };
  await assert.rejects(readApiResponse(res), (err) =>
    /respuesta inválida/.test(err.message),
  );
});

// ---------------------------------------------------------------------------
// getToken / setToken / clearToken
// ---------------------------------------------------------------------------

test("getToken: retorna null cuando no hay token", async () => {
  const { getToken } = await import("../lib/auth.js");
  assert.strictEqual(getToken(), null);
});

test("setToken + getToken: guarda y recupera el token", async () => {
  const { getToken, setToken } = await import("../lib/auth.js");
  setToken("mi-token-seguro");
  assert.strictEqual(getToken(), "mi-token-seguro");
});

test("clearToken: elimina el token almacenado", async () => {
  const { getToken, setToken, clearToken } = await import("../lib/auth.js");
  setToken("algo");
  clearToken();
  assert.strictEqual(getToken(), null);
});

test("setToken: sobrescribe un token anterior", async () => {
  const { getToken, setToken } = await import("../lib/auth.js");
  setToken("primero");
  setToken("segundo");
  assert.strictEqual(getToken(), "segundo");
});

test("getToken: retorna null cuando no hay window", async () => {
  // Save and remove window
  const savedWindow = globalThis.window;
  delete globalThis.window;
  const { getToken } = await import("../lib/auth.js");
  assert.strictEqual(getToken(), null);
  // Restore
  globalThis.window = savedWindow;
});
