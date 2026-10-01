const codespacesHost = window.location.hostname.match(
  /^(.*)-4174(\.app\.github\.dev)$/,
);
const defaultApiUrl = codespacesHost
  ? `${window.location.protocol}//${codespacesHost[1]}-8001${codespacesHost[2]}`
  : "http://127.0.0.1:8001";
const API_URL = window.NEXOVA_API_URL ?? defaultApiUrl;
const TOKEN_KEY = "nexova_support_token";
const CATEGORIES = ["TECHNICAL", "BILLING", "ACCESS", "HR_QUERY", "COMPLAINT"];
const STATUSES = ["OPEN", "CLOSED", "DISCARDED"];
const STATUS_LABELS = {
  OPEN: "Abierto",
  CLOSED: "Cerrado",
  DISCARDED: "Descartado",
};

const metrics = [
  {
    label: "SLA comprometido",
    value: "24 h",
    note: "Compromiso promedio actual con clientes corporativos.",
  },
  {
    label: "SLA promedio actual",
    value: "48 h",
    note: "Brecha activa detectada por el equipo de soporte.",
  },
  {
    label: "Agentes en operacion",
    value: "30",
    note: "Equipo de outsourcing de soporte al cliente.",
  },
  {
    label: "Filas exportadas (mes)",
    value: "1,000",
    note: "Volumen base exportado desde helpdesk legado para analisis.",
  },
  {
    label: "Archivo de prueba",
    value: "100 filas",
    note: "Dataset provisto para validacion del analizador de incidentes.",
  },
];

const priorities = [
  "Reducir backlog de tickets antes de revision con clientes.",
  "Elevar satisfaccion en tickets cerrados con seguimiento estandar.",
  "Asegurar que reportes y UIs no expongan correos de clientes.",
];

const state = {
  token: sessionStorage.getItem(TOKEN_KEY),
  user: null,
  resetToken: null,
  incidents: [],
  summary: null,
  filters: { status: "", category: "" },
  loginError: "",
  listError: "",
  summaryError: "",
  notice: "",
  listLoading: false,
  summaryLoading: false,
};

const app = document.getElementById("app");

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[character];
  });
}

function card(metric) {
  return `
    <article class="metric-card">
      <p class="metric-label">${escapeHTML(metric.label)}</p>
      <h3>${escapeHTML(metric.value)}</h3>
      <p class="metric-note">${escapeHTML(metric.note)}</p>
    </article>
  `;
}

function optionMarkup(values, selected, emptyLabel) {
  const emptyOption = `<option value="">${escapeHTML(emptyLabel)}</option>`;
  return (
    emptyOption +
    values
      .map(
        (value) => `
    <option value="${escapeHTML(value)}" ${value === selected ? "selected" : ""}>
      ${escapeHTML(value)}
    </option>
  `,
      )
      .join("")
  );
}

async function apiRequest(path, options = {}) {
  const headers = {};
  if (options.body) headers["Content-Type"] = "application/json";
  if (state.token) headers.Authorization = `Bearer ${state.token}`;

  const response = await fetch(`${API_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login") {
      clearSession("La sesión terminó. Inicia sesión nuevamente.");
    }
    const detail = data?.detail ?? data;
    const message =
      typeof detail === "string"
        ? detail
        : (detail?.message ??
          detail?.detail ??
          "No se pudo completar la solicitud.");
    throw new Error(message);
  }

  return data;
}

function renderLogin(message = state.loginError, messageType = "error") {
  app.className = "auth-shell";
  app.innerHTML = `
    <main class="auth-panel">
      <p class="kicker">Nexova Ops</p>
      <h1>Acceso interno</h1>
      <p class="auth-copy">Operaciones de soporte</p>
      <form id="login-form" class="form-stack">
        <label for="login-email">Correo interno</label>
        <input id="login-email" name="email" type="email" autocomplete="username" required />
        <label for="login-password">Contraseña</label>
        <input id="login-password" name="password" type="password" autocomplete="current-password" required />
        <button type="submit">Iniciar sesión</button>
      </form>
      <div class="auth-links">
        <button class="text-button" type="button" data-action="forgot-password">Olvidé mi contraseña</button>
      </div>
      <p class="form-message ${messageType === "error" ? "error-message" : ""}" role="status">${escapeHTML(message)}</p>
    </main>
  `;
}

function renderForgotPassword(message = "", messageType = "") {
  app.className = "auth-shell";
  app.innerHTML = `
    <main class="auth-panel">
      <p class="kicker">Nexova Ops</p>
      <h1>Recuperar acceso</h1>
      <p class="auth-copy">Introduce tu correo interno para solicitar un enlace de recuperación.</p>
      <form id="forgot-password-form" class="form-stack">
        <label for="forgot-email">Correo interno</label>
        <input id="forgot-email" name="email" type="email" autocomplete="username" required />
        <button type="submit">Enviar enlace</button>
      </form>
      <button class="text-button back-link" type="button" data-action="back-login">Volver al acceso</button>
      <p class="form-message ${messageType === "error" ? "error-message" : ""}" role="status">${escapeHTML(message)}</p>
    </main>
  `;
}

function renderResetPassword(token, message = "", messageType = "") {
  state.resetToken = token;
  window.history.replaceState({}, "", window.location.pathname);
  app.className = "auth-shell";
  app.innerHTML = `
    <main class="auth-panel">
      <p class="kicker">Nexova Ops</p>
      <h1>Nueva contraseña</h1>
      <form id="reset-password-form" class="form-stack">
        <label for="new-password">Contraseña nueva</label>
        <input id="new-password" name="new_password" type="password" minlength="8" maxlength="72" autocomplete="new-password" required />
        <label for="confirm-password">Repetir contraseña</label>
        <input id="confirm-password" name="confirm_password" type="password" minlength="8" maxlength="72" autocomplete="new-password" required />
        <button type="submit">Actualizar contraseña</button>
      </form>
      <p class="form-message ${messageType === "error" ? "error-message" : ""}" role="status">${escapeHTML(message)}</p>
    </main>
  `;
}

function renderDashboard() {
  app.className = "layout";
  app.innerHTML = `
    <aside class="sidebar">
      <h1>Nexova Ops</h1>
      <p>Backoffice interno para supervisores de soporte y coordinacion operativa.</p>
      <nav aria-label="Navegación principal">
        <a href="#resumen">Resumen</a>
        <a href="#tickets">Tickets</a>
        <a href="#prioridades">Prioridades</a>
        <a href="#privacidad">Privacidad</a>
      </nav>
      <button class="sidebar-logout" type="button" data-action="logout">Cerrar sesión</button>
    </aside>

    <main class="content">
      <header class="content-header" id="resumen">
        <div>
          <p class="kicker">Panel operativo</p>
          <h2>Seguimiento de soporte</h2>
        </div>
        <div class="user-controls">
          <span>${escapeHTML(state.user?.name || state.user?.email || "")}</span>
          <button type="button" data-action="change-password">Cambiar contraseña</button>
          <button type="button" data-action="logout">Salir</button>
        </div>
      </header>

      <section class="metrics-grid" aria-label="Contexto operativo">
        ${metrics.map(card).join("")}
      </section>

      <section class="summary-panel" id="incident-summary" aria-live="polite"></section>

      <section class="ticket-workspace" id="tickets">
        <section class="ticket-list-panel">
          <p class="kicker">Registro</p>
          <h3>Nuevo ticket</h3>
          <form id="incident-form" class="form-stack">
            <label for="ticket-date">Fecha</label>
            <input id="ticket-date" name="date" type="date" value="${new Date().toISOString().slice(0, 10)}" required />

            <label for="ticket-company">Empresa cliente</label>
            <input id="ticket-company" name="client_company" required />

            <label for="ticket-category">Categoría</label>
            <select id="ticket-category" name="category" required>
              ${CATEGORIES.map((category) => `<option value="${category}">${category}</option>`).join("")}
            </select>

            <label for="ticket-description">Descripción</label>
            <textarea id="ticket-description" name="description" minlength="5" required></textarea>

            <label for="ticket-agent">Agente asignado (AGT-XX)</label>
            <input id="ticket-agent" name="agent_id" pattern="AGT-[0-9]{2}" required />

            <label for="ticket-email">Correo del cliente</label>
            <input id="ticket-email" name="customer_email" type="email" autocomplete="off" required />

            <button type="submit">Registrar ticket</button>
          </form>
          <p id="ticket-notice" class="form-message" role="status"></p>
          <p id="ticket-error" class="form-message error-message" role="alert"></p>
        </section>

        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="kicker">Seguimiento</p>
              <h3>Tickets</h3>
            </div>
            <button type="button" data-action="refresh">Actualizar</button>
          </div>
          <div class="filter-grid">
            <label>Estado
              <select data-filter="status">
                ${optionMarkup(STATUSES, state.filters.status, "Todos")}
              </select>
            </label>
            <label>Categoría
              <select data-filter="category">
                ${optionMarkup(CATEGORIES, state.filters.category, "Todas")}
              </select>
            </label>
          </div>
          <div id="incident-list" aria-live="polite"></div>
        </section>
      </section>

      <section class="panel" id="prioridades">
        <h3>Prioridades inmediatas</h3>
        <ul>${priorities.map((item) => `<li>${escapeHTML(item)}</li>`).join("")}</ul>
      </section>

      <section class="panel" id="privacidad">
        <h3>Politica de datos sensibles</h3>
        <p>
          El campo <strong>customer_email</strong> es sensible. Se captura para el registro del ticket,
          pero no se muestra en listados, resúmenes ni errores.
        </p>
      </section>
    </main>
  `;
  renderSummary();
  renderIncidents();
}

function renderSummary() {
  const section = document.getElementById("incident-summary");
  if (!section) return;
  if (state.summaryError) {
    section.innerHTML = `
      <div class="section-heading">
        <h3>Resumen de tickets</h3>
        <button type="button" data-action="retry-summary">Reintentar resumen</button>
      </div>
      <p class="error-message">${escapeHTML(state.summaryError)}</p>
    `;
    return;
  }
  if (!state.summary) {
    section.innerHTML = `<h3>Resumen de tickets</h3><p>${state.summaryLoading ? "Cargando resumen..." : "Sin datos."}</p>`;
    return;
  }

  const statusItems = Object.entries(state.summary.by_status)
    .map(
      ([key, value]) =>
        `<li><span>${escapeHTML(STATUS_LABELS[key] ?? key)}</span><strong>${value}</strong></li>`,
    )
    .join("");
  const categoryItems = Object.entries(state.summary.by_category)
    .map(
      ([key, value]) =>
        `<li><span>${escapeHTML(key)}</span><strong>${value}</strong></li>`,
    )
    .join("");
  const average =
    state.summary.average_satisfaction == null
      ? "Sin puntuaciones"
      : `${Number(state.summary.average_satisfaction).toFixed(2)} / 5`;

  section.innerHTML = `
    <div class="section-heading">
      <div>
        <p class="kicker">Datos registrados</p>
        <h3>Resumen de tickets</h3>
      </div>
      <button type="button" data-action="retry-summary">Actualizar resumen</button>
    </div>
    <div class="summary-overview">
      <article><span>Total de tickets</span><strong>${state.summary.total}</strong></article>
      <article><span>Tickets cerrados con puntuación</span><strong>${state.summary.closed_scored}</strong></article>
      <article><span>Satisfacción media</span><strong>${escapeHTML(average)}</strong></article>
    </div>
    <div class="summary-breakdowns">
      <div><h4>Por estado</h4><ul>${statusItems}</ul></div>
      <div><h4>Por categoría</h4><ul>${categoryItems}</ul></div>
    </div>
  `;
}

function renderIncidents() {
  const section = document.getElementById("incident-list");
  if (!section) return;
  if (state.listLoading) {
    section.innerHTML = `<p class="empty-state">Cargando tickets...</p>`;
    return;
  }
  if (state.listError) {
    section.innerHTML = `
      <p class="error-message">${escapeHTML(state.listError)}</p>
      <button type="button" data-action="retry-list">Reintentar</button>
    `;
    return;
  }
  if (state.incidents.length === 0) {
    section.innerHTML = `<p class="empty-state">No hay tickets para los filtros seleccionados.</p>`;
    return;
  }

  section.innerHTML = state.incidents
    .map(
      (incident) => `
    <article class="ticket-item">
      <div class="ticket-heading">
        <strong>${escapeHTML(incident.ticket_id)}</strong>
        <span class="status-label status-${escapeHTML(incident.status.toLowerCase())}">
          ${escapeHTML(STATUS_LABELS[incident.status] ?? incident.status)}
        </span>
      </div>
      <h4>${escapeHTML(incident.client_company)}</h4>
      <p>${escapeHTML(incident.description)}</p>
      <dl class="ticket-facts">
        <div><dt>Fecha</dt><dd>${escapeHTML(incident.date)}</dd></div>
        <div><dt>Categoría</dt><dd>${escapeHTML(incident.category)}</dd></div>
        <div><dt>Agente</dt><dd>${escapeHTML(incident.agent_id)}</dd></div>
        <div><dt>Satisfacción</dt><dd>${incident.satisfaction_score ?? "Sin puntuar"}</dd></div>
      </dl>
      <form class="status-form" data-ticket-id="${escapeHTML(incident.ticket_id)}">
        <label>Estado
          <select name="status">
            ${STATUSES.map(
              (statusValue) => `
              <option value="${statusValue}" ${incident.status === statusValue ? "selected" : ""}>
                ${escapeHTML(STATUS_LABELS[statusValue])}
              </option>
            `,
            ).join("")}
          </select>
        </label>
        <label>Puntuación al cerrar
          <input name="satisfaction_score" type="number" min="1" max="5" value="${incident.satisfaction_score ?? ""}" />
        </label>
        <button type="submit">Guardar estado</button>
      </form>
    </article>
  `,
    )
    .join("");
}

function setTicketMessage({ notice = "", error = "" } = {}) {
  const noticeNode = document.getElementById("ticket-notice");
  const errorNode = document.getElementById("ticket-error");
  if (noticeNode) noticeNode.textContent = notice;
  if (errorNode) errorNode.textContent = error;
}

async function loadIncidents() {
  state.listLoading = true;
  state.listError = "";
  renderIncidents();
  const params = new URLSearchParams();
  if (state.filters.status) params.set("status", state.filters.status);
  if (state.filters.category) params.set("category", state.filters.category);
  const query = params.toString();

  try {
    state.incidents = await apiRequest(
      `/api/incidents${query ? `?${query}` : ""}`,
    );
  } catch (error) {
    state.listError =
      error instanceof Error
        ? error.message
        : "No se pudieron cargar los tickets.";
  } finally {
    state.listLoading = false;
    renderIncidents();
  }
}

async function loadSummary() {
  state.summaryLoading = true;
  state.summaryError = "";
  renderSummary();
  try {
    state.summary = await apiRequest("/api/incidents/summary");
  } catch (error) {
    state.summaryError =
      error instanceof Error ? error.message : "No se pudo cargar el resumen.";
  } finally {
    state.summaryLoading = false;
    renderSummary();
  }
}

function clearSession(message = "") {
  sessionStorage.removeItem(TOKEN_KEY);
  state.token = null;
  state.user = null;
  state.loginError = message;
  renderLogin(message);
}

function renderChangePassword(message = "", messageType = "") {
  app.className = "auth-shell";
  app.innerHTML = `
    <main class="auth-panel">
      <p class="kicker">Nexova Ops</p>
      <h1>Cambiar contraseña</h1>
      <form id="change-password-form" class="form-stack">
        <label for="current-password">Contraseña actual</label>
        <input id="current-password" name="current_password" type="password" autocomplete="current-password" required />
        <label for="changed-password">Contraseña nueva</label>
        <input id="changed-password" name="new_password" type="password" minlength="8" maxlength="72" autocomplete="new-password" required />
        <label for="changed-password-confirm">Repetir contraseña nueva</label>
        <input id="changed-password-confirm" name="confirm_password" type="password" minlength="8" maxlength="72" autocomplete="new-password" required />
        <button type="submit">Actualizar contraseña</button>
      </form>
      <button class="text-button back-link" type="button" data-action="back-dashboard">Volver al panel</button>
      <p class="form-message ${messageType === "error" ? "error-message" : ""}" role="status">${escapeHTML(message)}</p>
    </main>
  `;
}

async function handleLogin(form) {
  const button = form.querySelector("button[type='submit']");
  button.disabled = true;
  button.textContent = "Ingresando...";
  state.loginError = "";

  try {
    const formData = new FormData(form);
    const result = await apiRequest("/auth/login", {
      method: "POST",
      body: {
        email: formData.get("email"),
        password: formData.get("password"),
      },
    });
    state.token = result.access_token;
    sessionStorage.setItem(TOKEN_KEY, state.token);
    state.user = result.user;
    renderDashboard();
    await Promise.all([loadIncidents(), loadSummary()]);
  } catch (error) {
    state.loginError =
      error instanceof Error ? error.message : "No se pudo iniciar sesión.";
    renderLogin();
  }
}

async function handleForgotPassword(form) {
  const button = form.querySelector("button[type='submit']");
  button.disabled = true;
  button.textContent = "Enviando...";

  try {
    const formData = new FormData(form);
    const result = await apiRequest("/auth/forgot-password", {
      method: "POST",
      body: { email: formData.get("email") },
    });
    renderForgotPassword(result.message, "success");
  } catch (error) {
    renderForgotPassword(
      error instanceof Error
        ? error.message
        : "No se pudo solicitar la recuperación.",
      "error",
    );
  }
}

async function handleResetPassword(form) {
  const formData = new FormData(form);
  const newPassword = formData.get("new_password");
  if (newPassword !== formData.get("confirm_password")) {
    renderResetPassword(
      state.resetToken,
      "Las contraseñas no coinciden.",
      "error",
    );
    return;
  }

  const button = form.querySelector("button[type='submit']");
  button.disabled = true;
  button.textContent = "Actualizando...";
  try {
    const result = await apiRequest("/auth/reset-password", {
      method: "POST",
      body: {
        token: state.resetToken,
        new_password: newPassword,
      },
    });
    state.resetToken = null;
    renderLogin(result.message, "success");
  } catch (error) {
    renderResetPassword(
      state.resetToken,
      error instanceof Error
        ? error.message
        : "No se pudo actualizar la contraseña.",
      "error",
    );
  }
}

async function handleChangePassword(form) {
  const formData = new FormData(form);
  const newPassword = formData.get("new_password");
  if (newPassword !== formData.get("confirm_password")) {
    renderChangePassword("Las contraseñas no coinciden.", "error");
    return;
  }

  const button = form.querySelector("button[type='submit']");
  button.disabled = true;
  button.textContent = "Actualizando...";
  try {
    const result = await apiRequest("/auth/change-password", {
      method: "POST",
      body: {
        current_password: formData.get("current_password"),
        new_password: newPassword,
      },
    });
    sessionStorage.removeItem(TOKEN_KEY);
    state.token = null;
    state.user = null;
    renderLogin(`${result.message} Inicia sesión nuevamente.`, "success");
  } catch (error) {
    if (!state.token) return;
    renderChangePassword(
      error instanceof Error
        ? error.message
        : "No se pudo cambiar la contraseña.",
      "error",
    );
  }
}

async function handleCreateIncident(form) {
  const button = form.querySelector("button[type='submit']");
  button.disabled = true;
  button.textContent = "Guardando...";
  setTicketMessage();

  try {
    const payload = Object.fromEntries(new FormData(form).entries());
    await apiRequest("/api/incidents", { method: "POST", body: payload });
    form.reset();
    const dateInput = form.elements.namedItem("date");
    dateInput.value = new Date().toISOString().slice(0, 10);
    setTicketMessage({ notice: "Ticket registrado correctamente." });
    await Promise.all([loadIncidents(), loadSummary()]);
  } catch (error) {
    setTicketMessage({
      error:
        error instanceof Error
          ? error.message
          : "No se pudo registrar el ticket.",
    });
  } finally {
    if (button.isConnected) {
      button.disabled = false;
      button.textContent = "Registrar ticket";
    }
  }
}

async function handleStatusUpdate(form) {
  const ticketId = form.dataset.ticketId;
  const formData = new FormData(form);
  const newStatus = formData.get("status");
  const scoreValue = formData.get("satisfaction_score");
  const score = scoreValue === "" ? null : Number(scoreValue);
  if (newStatus === "CLOSED" && score === null) {
    state.listError = "Un ticket cerrado requiere puntuación de satisfacción.";
    renderIncidents();
    return;
  }

  const previous = state.incidents.find(
    (incident) => incident.ticket_id === ticketId,
  );
  if (!previous) return;
  const previousValue = { ...previous };
  state.incidents = state.incidents.map((incident) =>
    incident.ticket_id === ticketId
      ? {
          ...incident,
          status: newStatus,
          satisfaction_score: score ?? incident.satisfaction_score,
        }
      : incident,
  );
  renderIncidents();

  try {
    const updated = await apiRequest(
      `/api/incidents/${encodeURIComponent(ticketId)}/status`,
      {
        method: "PATCH",
        body: { status: newStatus, satisfaction_score: score },
      },
    );
    state.incidents = state.incidents.map((incident) =>
      incident.ticket_id === ticketId ? updated : incident,
    );
    state.listError = "";
    await Promise.all([loadSummary(), loadIncidents()]);
  } catch (error) {
    state.incidents = state.incidents.map((incident) =>
      incident.ticket_id === ticketId ? previousValue : incident,
    );
    state.listError =
      error instanceof Error
        ? error.message
        : "No se pudo actualizar el ticket.";
    renderIncidents();
  }
}

app.addEventListener("submit", (event) => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  event.preventDefault();
  if (form.id === "login-form") void handleLogin(form);
  if (form.id === "forgot-password-form") void handleForgotPassword(form);
  if (form.id === "reset-password-form") void handleResetPassword(form);
  if (form.id === "change-password-form") void handleChangePassword(form);
  if (form.id === "incident-form") void handleCreateIncident(form);
  if (form.matches(".status-form")) void handleStatusUpdate(form);
});

app.addEventListener("change", (event) => {
  const filter = event.target.closest?.("[data-filter]");
  if (!filter) return;
  state.filters[filter.dataset.filter] = filter.value;
  void loadIncidents();
});

app.addEventListener("click", (event) => {
  const button = event.target.closest?.("[data-action]");
  if (!button) return;
  if (button.dataset.action === "logout") clearSession();
  if (button.dataset.action === "forgot-password") renderForgotPassword();
  if (button.dataset.action === "back-login") renderLogin();
  if (button.dataset.action === "change-password") renderChangePassword();
  if (button.dataset.action === "back-dashboard") renderDashboard();
  if (
    button.dataset.action === "refresh" ||
    button.dataset.action === "retry-list"
  ) {
    void loadIncidents();
  }
  if (button.dataset.action === "retry-summary") void loadSummary();
});

async function start() {
  const resetToken = new URLSearchParams(window.location.search).get(
    "reset_token",
  );
  if (resetToken) {
    renderResetPassword(resetToken);
    return;
  }
  if (!state.token) {
    renderLogin();
    return;
  }
  try {
    state.user = await apiRequest("/auth/me");
    renderDashboard();
    await Promise.all([loadIncidents(), loadSummary()]);
  } catch {
    if (state.token)
      clearSession("La sesión no es válida. Inicia sesión nuevamente.");
  }
}

void start();
