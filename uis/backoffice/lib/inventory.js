const TOKEN_KEY = "nexova_support_token";
const API_BASE = (
  process.env.NEXT_PUBLIC_INVENTORY_API_URL || "/backend"
).replace(/\/$/, "");

export class InventoryApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "InventoryApiError";
    this.status = status;
  }
}

function storedToken() {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(TOKEN_KEY);
}

function redirectToLogin() {
  if (typeof window === "undefined") return;

  const returnTo = `${window.location.pathname}${window.location.search}`;
  window.sessionStorage.removeItem(TOKEN_KEY);
  window.location.assign(`/?next=${encodeURIComponent(returnTo)}`);
}

function responseMessage(payload, status) {
  const detail = payload?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) return detail.message;
  if (payload?.message) return payload.message;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (payload?.error) return payload.error;
  return `La API respondió con el estado ${status}.`;
}

async function request(path, { method = "GET", body, token } = {}) {
  const authToken = token ?? storedToken();
  if (!authToken) {
    redirectToLogin();
    throw new InventoryApiError("Inicia sesión para continuar.", 401);
  }

  const headers = {
    Authorization: `Bearer ${authToken}`,
  };
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new InventoryApiError(
      "No se pudo conectar con el servicio de inventario.",
      0,
    );
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const message = responseMessage(payload, response.status);
    if (response.status === 401) redirectToLogin();
    throw new InventoryApiError(message, response.status);
  }

  return payload;
}

export function getCurrentUser(token) {
  return request("/auth/me", { token });
}

export function getProducts({ office } = {}) {
  const query = office ? `?office=${encodeURIComponent(office)}` : "";
  return request(`/inventory/products${query}`);
}

export function getProduct(assetId) {
  return request(`/inventory/products/${encodeURIComponent(assetId)}`);
}

export function createInboundOrder(payload) {
  return request("/inventory/orders/inbound", {
    method: "POST",
    body: payload,
  });
}

export function createOutboundOrder(payload) {
  return request("/inventory/orders/outbound", {
    method: "POST",
    body: payload,
  });
}

export function getOrders({ office } = {}) {
  const query = office ? `?office=${encodeURIComponent(office)}` : "";
  return request(`/inventory/orders${query}`);
}
