/**
 * Auth utilities shared across the backoffice application.
 *
 * Token lifecycle:
 * - Stored in localStorage so it persists across tabs and sessions.
 * - Attached as `Authorization: Bearer <token>` on every protected API call.
 * - Removed on logout; user is redirected to /login.
 */

const TOKEN_KEY = "nexova_support_token";
const API_BASE = (
  process.env.NEXT_PUBLIC_INVENTORY_API_URL || "/backend"
).replace(/\/$/, "");

/* ------------------------------------------------------------------ */
/*  Token helpers                                                      */
/* ------------------------------------------------------------------ */

export function getToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

/* ------------------------------------------------------------------ */
/*  Session helpers                                                     */
/* ------------------------------------------------------------------ */

export function redirectToLogin(returnTo) {
  if (typeof window === "undefined") return;
  clearToken();
  const next =
    returnTo ?? `${window.location.pathname}${window.location.search}`;
  window.location.href = `/login?next=${encodeURIComponent(next)}`;
}

export function isAuthenticated() {
  return !!getToken();
}

/* ------------------------------------------------------------------ */
/*  Auth API calls                                                      */
/* ------------------------------------------------------------------ */

/**
 * POST /auth/login — authenticate with email + password.
 * Returns { access_token, token_type, user }.
 */
export async function login(email, password) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    signal: AbortSignal.timeout(15000),
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      response.status === 401
        ? "Correo o contraseña incorrectos. Revisa tus credenciales e inténtalo de nuevo."
        : response.status === 400 || response.status === 422
          ? "Revisa los datos del formulario e inténtalo de nuevo."
          : "No se pudo conectar con el servicio. Inténtalo de nuevo en unos momentos.";
    throw new Error(message);
  }

  if (!payload?.access_token) {
    throw new Error(
      "El servicio devolvió una respuesta inválida. Inténtalo de nuevo.",
    );
  }

  return payload;
}

/**
 * POST /users — register a new user.
 * Returns { id, email, is_active, role, created_at }.
 */
export async function register({ email, password, name, phone, address }) {
  const body = { email, password };
  if (name) body.name = name;
  if (phone) body.phone = phone;
  if (address) body.address = address;

  const response = await fetch(`${API_BASE}/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    let message = "No se pudo completar el registro. Inténtalo de nuevo.";
    if (response.status === 409) {
      message = "Ya existe una cuenta con ese correo.";
    } else if (response.status === 400 || response.status === 422) {
      message = "Revisa los datos del formulario e inténtalo de nuevo.";
    }
    throw new Error(message);
  }

  return payload;
}

/**
 * GET /auth/me — fetch current user with profile.
 * Returns { id, email, role, profile: { name, phone, address } }.
 */
export async function getCurrentUser(token) {
  const authToken = token ?? getToken();
  if (!authToken) {
    redirectToLogin();
    throw new Error("No autenticado.");
  }

  const response = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${authToken}` },
    signal: AbortSignal.timeout(15000),
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401) redirectToLogin();
    throw new Error("La sesión terminó. Inicia sesión nuevamente.");
  }

  if (!payload?.email) {
    throw new Error(
      "El servicio devolvió una respuesta inválida. Inténtalo de nuevo.",
    );
  }

  return payload;
}

/**
 * PUT /profiles/me — update current user's profile.
 */
export async function updateProfile(changes, token) {
  const authToken = token ?? getToken();
  if (!authToken) {
    redirectToLogin();
    throw new Error("No autenticado.");
  }

  const response = await fetch(`${API_BASE}/profiles/me`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${authToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(changes),
    signal: AbortSignal.timeout(15000),
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401) redirectToLogin();
    throw new Error("No se pudo actualizar el perfil. Inténtalo de nuevo.");
  }

  return payload;
}

/**
 * POST /auth/forgot-password — request a password reset link.
 * Returns { message } and always resolves successfully (the API never
 * reveals whether the address is registered).
 */
export async function forgotPassword(email) {
  const response = await fetch(`${API_BASE}/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
    signal: AbortSignal.timeout(15000),
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(
      response.status === 400 || response.status === 422
        ? "Revisa el correo indicado e inténtalo de nuevo."
        : "No se pudo completar la solicitud. Inténtalo de nuevo en unos momentos.",
    );
  }

  return (
    payload ?? {
      message:
        "Si esa dirección está registrada, recibirás un enlace en breve.",
    }
  );
}

/**
 * POST /auth/reset-password — set a new password with a reset token.
 * Returns { message } on success, throws on invalid/expired tokens.
 */
export async function resetPassword({ token, new_password }) {
  const response = await fetch(`${API_BASE}/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password }),
    signal: AbortSignal.timeout(15000),
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const message =
      response.status === 400 || response.status === 422
        ? payload?.detail ||
          "El enlace de recuperación no es válido o ha expirado."
        : "No se pudo restablecer la contraseña. Inténtalo de nuevo.";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return payload ?? { message: "La contraseña se actualizó correctamente." };
}

/**
 * POST /auth/change-password — update the password for the current session.
 * Requires a valid token; verifies the current password server-side.
 * Returns { message } on success.
 */
export async function changePassword(
  { current_password, new_password },
  token,
) {
  const authToken = token ?? getToken();
  if (!authToken) {
    redirectToLogin();
    throw new Error("No autenticado.");
  }

  const response = await fetch(`${API_BASE}/auth/change-password`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${authToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ current_password, new_password }),
    signal: AbortSignal.timeout(15000),
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401) {
      redirectToLogin();
      throw new Error("La sesión terminó. Inicia sesión nuevamente.");
    }
    const message =
      response.status === 400 || response.status === 422
        ? payload?.detail || "Revisa los datos indicados e inténtalo de nuevo."
        : "No se pudo cambiar la contraseña. Inténtalo de nuevo.";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return payload ?? { message: "La contraseña se actualizó correctamente." };
}
