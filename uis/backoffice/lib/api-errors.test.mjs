import assert from "node:assert/strict";
import test from "node:test";
import { getProducts } from "./inventory.js";
import { getSuppliers } from "./suppliers.js";
import { getIncidents } from "./incidents.js";

globalThis.window = {
  sessionStorage: { getItem: () => "test-token", removeItem: () => {} },
  location: { pathname: "/", search: "", assign: () => {} },
};

for (const [name, load] of [
  ["inventory", getProducts],
  ["suppliers", getSuppliers],
  ["incidents", getIncidents],
]) {
  test(`${name}: network, HTTP, invalid JSON and success`, async () => {
    for (const failure of [
      async () => {
        throw new Error("private@example.com");
      },
      async () => ({
        ok: false,
        status: 500,
        json: async () => ({ detail: "private@example.com" }),
      }),
      async () => ({
        ok: true,
        status: 200,
        json: async () => {
          throw new SyntaxError("Unexpected token");
        },
      }),
      async () => ({ ok: true, status: 200, json: async () => null }),
      async () => ({ ok: true, status: 200, json: async () => [null] }),
    ]) {
      globalThis.fetch = failure;
      await assert.rejects(
        load(),
        (error) =>
          /nuevo/.test(error.message) &&
          !/private@|Unexpected token|500/.test(error.message),
      );
    }
    globalThis.fetch = async () => ({
      ok: true,
      status: 200,
      json: async () => [],
    });
    assert.deepEqual(await load(), []);
  });
}
