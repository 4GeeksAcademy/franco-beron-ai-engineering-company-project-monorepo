const TOKEN_KEY = "nexova_support_token";
const API_BASE = (
  process.env.NEXT_PUBLIC_INVENTORY_API_URL || "/backend"
).replace(/\/$/, "");

export class IncidentApiError extends Error {
  constructor(message, status, field = "") {
    super(message);
    this.name = "IncidentApiError";
    this.status = status;
    this.field = field;
  }
}

function redirectToLogin() {
  if (typeof window === "undefined") return;
  const returnTo = `${window.location.pathname}${window.location.search}`;
  window.sessionStorage.removeItem(TOKEN_KEY);
  window.location.assign(`/?next=${encodeURIComponent(returnTo)}`);
}

function errorMessage(payload, status) {
  const detail = payload?.detail ?? payload;
  if (status === 400 && detail?.error === "invalid_transition") {
    return "Ese cambio de estado no está permitido.";
  }
  if (status === 400 || status === 422) {
    return "Revisa los campos indicados e inténtalo de nuevo.";
  }
  if (status === 404) return "La incidencia ya no está disponible.";
  if (status >= 500) {
    return "El servicio no pudo completar la solicitud. Inténtalo de nuevo.";
  }
  return "No se pudo completar la solicitud. Inténtalo de nuevo.";
}

async function request(path, { method = "GET", body } = {}) {
  const token =
    typeof window === "undefined"
      ? null
      : window.sessionStorage.getItem(TOKEN_KEY);
  if (!token) {
    redirectToLogin();
    throw new IncidentApiError("Tu sesión ha terminado. Inicia sesión.", 401);
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
    throw new IncidentApiError(
      "No se pudo conectar con el servicio. Comprueba tu conexión e inténtalo de nuevo.",
      0,
    );
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401) redirectToLogin();
    const detail = payload?.detail ?? payload;
    throw new IncidentApiError(
      errorMessage(payload, response.status),
      response.status,
      typeof detail?.field === "string" ? detail.field : "",
    );
  }
  return payload;
}

export function getIncidents(filters = {}) {
  const query = new URLSearchParams();
  for (const key of ["status", "origin", "branch", "category"]) {
    if (filters[key]) query.set(key, filters[key]);
  }
  const suffix = query.size ? `?${query.toString()}` : "";
  return request(`/api/incidents${suffix}`);
}

export function getIncidentSummary() {
  return request("/api/incidents/summary");
}

export function createIncident(payload) {
  return request("/api/incidents", { method: "POST", body: payload });
}

export function updateIncidentStatus(incidentId, nextStatus) {
  return request(`/api/incidents/${encodeURIComponent(incidentId)}/status`, {
    method: "PATCH",
    body: { status: nextStatus },
  });
}
