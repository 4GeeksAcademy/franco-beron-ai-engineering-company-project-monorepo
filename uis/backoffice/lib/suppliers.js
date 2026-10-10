const TOKEN_KEY = "nexova_support_token";
const API_BASE = (
  process.env.NEXT_PUBLIC_INVENTORY_API_URL || "/backend"
).replace(/\/$/, "");

export class SupplierApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "SupplierApiError";
    this.status = status;
  }
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  const returnTo = `${window.location.pathname}${window.location.search}`;
  window.sessionStorage.removeItem(TOKEN_KEY);
  window.location.assign(`/?next=${encodeURIComponent(returnTo)}`);
}

function errorMessage(payload, status) {
  const detail = payload?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.message) return detail.message;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return payload?.message || `La API respondió con estado ${status}.`;
}

async function request(path, { method = "GET", body } = {}) {
  const token =
    typeof window === "undefined"
      ? null
      : window.sessionStorage.getItem(TOKEN_KEY);
  if (!token) {
    redirectToLogin();
    throw new SupplierApiError("Inicia sesión para continuar.", 401);
  }

  const headers = { Authorization: `Bearer ${token}` };
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new SupplierApiError(
      "No se pudo conectar con el directorio de proveedores.",
      0,
    );
  }

  if (response.status === 204) return null;
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const message = errorMessage(payload, response.status);
    if (response.status === 401) redirectToLogin();
    throw new SupplierApiError(message, response.status);
  }
  return payload;
}

export function getSuppliers({ country = "", category = "" } = {}) {
  const query = new URLSearchParams();
  if (country) query.set("country", country);
  if (category) query.set("category", category);
  const suffix = query.size ? `?${query.toString()}` : "";
  return request(`/suppliers${suffix}`);
}

export function createSupplier(payload) {
  return request("/suppliers", { method: "POST", body: payload });
}

export function updateSupplierRate(supplierId, monthlyRate) {
  return request(`/suppliers/${supplierId}/rate`, {
    method: "PATCH",
    body: { monthly_rate: monthlyRate },
  });
}

export function updateSupplierStatus(supplierId, nextStatus) {
  return request(`/suppliers/${supplierId}/status`, {
    method: "PATCH",
    body: { status: nextStatus },
  });
}
