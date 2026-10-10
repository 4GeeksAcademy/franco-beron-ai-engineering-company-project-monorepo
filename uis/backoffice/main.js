const API_URL = "/backend";
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
    label: "SLA objetivo",
    value: "24 h",
    note: "Compromiso con clientes",
    icon: "target",
    tone: "blue",
  },
  {
    label: "SLA actual",
    value: "48 h",
    note: "24 h sobre el objetivo",
    icon: "clock-alert",
    tone: "amber",
  },
  {
    label: "Equipo activo",
    value: "30",
    note: "Agentes de soporte",
    icon: "users",
    tone: "teal",
  },
  {
    label: "Volumen mensual",
    value: "1,000",
    note: "Tickets exportados",
    icon: "database",
    tone: "coral",
  },
  {
    label: "Muestra validada",
    value: "100 filas",
    note: "Dataset de control",
    icon: "file-check-2",
    tone: "violet",
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

function icon(name, className = "") {
  return `<i data-lucide="${name}" class="${className}" aria-hidden="true"></i>`;
}

function renderIcons() {
  window.lucide?.createIcons({ attrs: { "stroke-width": 1.8 } });
}

function card(metric) {
  return `
    <article class="metric-card metric-${escapeHTML(metric.tone)}">
      <div class="metric-icon">${icon(metric.icon)}</div>
      <div>
        <p class="metric-label">${escapeHTML(metric.label)}</p>
        <strong class="metric-value">${escapeHTML(metric.value)}</strong>
        <p class="metric-note">${escapeHTML(metric.note)}</p>
      </div>
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

  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: AbortSignal.timeout(15000),
    });
  } catch {
    throw new Error(
      "No se pudo conectar con el servicio. Comprueba tu conexión e inténtalo de nuevo.",
    );
  }
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401 && path !== "/auth/login") {
      clearSession("La sesión terminó. Inicia sesión nuevamente.");
    }
    const message =
      response.status === 401
        ? path === "/auth/login"
          ? "Correo o contraseña incorrectos. Revisa tus credenciales e inténtalo de nuevo."
          : "La sesión terminó. Inicia sesión nuevamente."
        : response.status === 400 || response.status === 422
          ? "Revisa los datos indicados e inténtalo de nuevo."
          : "No se pudo completar la solicitud. Inténtalo de nuevo en unos momentos.";
    throw new Error(message);
  }

  if (
    data === null ||
    typeof data !== "object" ||
    (path.split("?")[0] === "/api/tickets" &&
      !options.body &&
      !Array.isArray(data))
  ) {
    throw new Error(
      "El servicio devolvió una respuesta inválida. Inténtalo de nuevo.",
    );
  }
  return data;
}

function renderLogin(message = state.loginError, messageType = "error") {
  app.className = "auth-shell";
  app.innerHTML = `
    <main class="auth-panel">
      <div class="auth-brand"><span class="brand-mark">N</span><span>Nexova Ops</span></div>
      <p class="kicker">Centro de operaciones</p>
      <h1>Bienvenido de nuevo</h1>
      <p class="auth-copy">Accede al espacio interno de soporte.</p>
      <form id="login-form" class="form-stack">
        <label for="login-email">Correo interno</label>
        <div class="input-shell">${icon("mail")}<input id="login-email" name="email" type="email" autocomplete="username" required /></div>
        <label for="login-password">Contraseña</label>
        <div class="input-shell">${icon("lock-keyhole")}<input id="login-password" name="password" type="password" autocomplete="current-password" required /><button class="icon-button password-toggle" type="button" data-action="toggle-password" data-target="login-password" aria-label="Mostrar contraseña" aria-pressed="false">${icon("eye")}</button></div>
        <button class="primary-button" type="submit">${icon("log-in")}<span>Iniciar sesión</span></button>
      </form>
      <div class="auth-links">
        <button class="text-button" type="button" data-action="forgot-password">Olvidé mi contraseña</button>
      </div>
      <p class="form-message ${messageType === "error" ? "error-message" : ""}" role="status">${escapeHTML(message)}</p>
    </main>
  `;
  renderIcons();
}

function renderForgotPassword(message = "", messageType = "") {
  app.className = "auth-shell";
  app.innerHTML = `
    <main class="auth-panel">
      <div class="auth-brand"><span class="brand-mark">N</span><span>Nexova Ops</span></div>
      <p class="kicker">Seguridad de cuenta</p>
      <h1>Recuperar acceso</h1>
      <p class="auth-copy">Introduce tu correo interno para solicitar un enlace de recuperación.</p>
      <form id="forgot-password-form" class="form-stack">
        <label for="forgot-email">Correo interno</label>
        <div class="input-shell">${icon("mail")}<input id="forgot-email" name="email" type="email" autocomplete="username" required /></div>
        <button class="primary-button" type="submit">${icon("send")}<span>Enviar enlace</span></button>
      </form>
      <button class="text-button back-link" type="button" data-action="back-login">${icon("arrow-left")}<span>Volver al acceso</span></button>
      <p class="form-message ${messageType === "error" ? "error-message" : ""}" role="status">${escapeHTML(message)}</p>
    </main>
  `;
  renderIcons();
}

function renderResetPassword(token, message = "", messageType = "") {
  state.resetToken = token;
  window.history.replaceState({}, "", window.location.pathname);
  app.className = "auth-shell";
  app.innerHTML = `
    <main class="auth-panel">
      <div class="auth-brand"><span class="brand-mark">N</span><span>Nexova Ops</span></div>
      <p class="kicker">Seguridad de cuenta</p>
      <h1>Nueva contraseña</h1>
      <p class="auth-copy">Usa al menos 8 caracteres para proteger tu cuenta.</p>
      <form id="reset-password-form" class="form-stack">
        <label for="new-password">Contraseña nueva</label>
        <div class="input-shell">${icon("lock-keyhole")}<input id="new-password" name="new_password" type="password" minlength="8" maxlength="72" autocomplete="new-password" required /></div>
        <label for="confirm-password">Repetir contraseña</label>
        <div class="input-shell">${icon("shield-check")}<input id="confirm-password" name="confirm_password" type="password" minlength="8" maxlength="72" autocomplete="new-password" required /></div>
        <button class="primary-button" type="submit">${icon("key-round")}<span>Actualizar contraseña</span></button>
      </form>
      <p class="form-message ${messageType === "error" ? "error-message" : ""}" role="status">${escapeHTML(message)}</p>
    </main>
  `;
  renderIcons();
}

function renderDashboard() {
  app.className = "layout";
  app.innerHTML = `
    <aside class="sidebar">
      <div class="brand-lockup"><span class="brand-mark">N</span><div><strong>Nexova</strong><span>Operations</span></div></div>
      <nav aria-label="Navegación principal">
        <a class="nav-link active" href="#resumen">${icon("layout-dashboard")}<span>Resumen</span></a>
        <a class="nav-link" href="/backoffice/inventory/products">${icon("boxes")}<span>Inventario</span></a>
        <a class="nav-link" href="/backoffice/suppliers">${icon("building-2")}<span>Proveedores</span></a>
        <a class="nav-link" href="#tickets">${icon("inbox")}<span>Tickets</span></a>
        <a class="nav-link" href="#prioridades">${icon("list-checks")}<span>Prioridades</span></a>
        <a class="nav-link" href="#privacidad">${icon("shield-check")}<span>Privacidad</span></a>
      </nav>
      <div class="sidebar-footer">
        <div class="sidebar-user"><span class="avatar">${escapeHTML((state.user?.name || state.user?.email || "N").slice(0, 1).toUpperCase())}</span><div><strong>${escapeHTML(state.user?.name || "Usuario interno")}</strong><span>${escapeHTML(state.user?.email || "")}</span></div></div>
        <button class="sidebar-logout" type="button" data-action="logout">${icon("log-out")}<span>Cerrar sesión</span></button>
      </div>
    </aside>

    <main class="content">
      <header class="content-header" id="resumen">
        <div>
          <p class="kicker">Operaciones de soporte</p>
          <h1>Centro de control</h1>
          <p class="header-copy">Visión diaria de carga, servicio y satisfacción.</p>
        </div>
        <div class="user-controls">
          <span class="system-status"><span aria-hidden="true"></span>API conectada</span>
          <button class="secondary-button" type="button" data-action="change-password">${icon("key-round")}<span>Cambiar contraseña</span></button>
        </div>
      </header>

      <section class="metrics-grid" aria-label="Indicadores operativos">
        ${metrics.map(card).join("")}
      </section>

      <section class="summary-panel" id="incident-summary" aria-live="polite"></section>

      <section class="ticket-workspace" id="tickets">
        <section class="panel create-ticket-panel">
          <div class="panel-heading"><span class="section-icon">${icon("square-pen")}</span><div><p class="kicker">Registro</p><h2>Nuevo ticket</h2></div></div>
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

            <button class="primary-button" type="submit">${icon("plus")}<span>Registrar ticket</span></button>
          </form>
          <p id="ticket-notice" class="form-message" role="status"></p>
          <p id="ticket-error" class="form-message error-message" role="alert"></p>
        </section>

        <section class="panel">
          <div class="section-heading">
            <div>
              <p class="kicker">Seguimiento</p>
              <h2>Cola de tickets</h2>
            </div>
            <button class="icon-button" type="button" data-action="refresh" aria-label="Actualizar tickets" title="Actualizar tickets">${icon("refresh-cw")}</button>
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
        <div class="panel-heading"><span class="section-icon">${icon("list-checks")}</span><div><p class="kicker">Foco operativo</p><h2>Prioridades inmediatas</h2></div></div>
        <ol class="priority-list">${priorities.map((item) => `<li><span>${escapeHTML(item)}</span></li>`).join("")}</ol>
      </section>

      <section class="panel" id="privacidad">
        <div class="panel-heading"><span class="section-icon">${icon("shield-check")}</span><div><p class="kicker">Gobierno de datos</p><h2>Privacidad por diseño</h2></div></div>
        <p>
          El correo del cliente es sensible. Se captura para el registro del ticket,
          pero no se muestra en listados, resúmenes ni errores.
        </p>
      </section>
    </main>
  `;
  renderSummary();
  renderIncidents();
  renderIcons();
}

function renderSummary() {
  const section = document.getElementById("incident-summary");
  if (!section) return;
  if (state.summaryError) {
    section.innerHTML = `
      <div class="section-heading">
        <h2>Resumen de tickets</h2>
        <button class="secondary-button" type="button" data-action="retry-summary">${icon("refresh-cw")}<span>Reintentar</span></button>
      </div>
      <p class="error-message">${escapeHTML(state.summaryError)}</p>
    `;
    return;
  }
  if (state.summaryLoading || !state.summary) {
    section.innerHTML = `<div class="loading-state">${icon("loader-circle", state.summaryLoading ? "spin" : "")}<span>${state.summaryLoading ? "Cargando resumen..." : "Sin datos."}</span></div>`;
    renderIcons();
    return;
  }

  const statusItems = Object.entries(state.summary?.by_status ?? {})
    .map(
      ([key, value]) =>
        `<li><span>${escapeHTML(STATUS_LABELS[key] ?? key)}</span><span class="breakdown-track"><span style="--value:${state.summary.total ? (value / state.summary.total) * 100 : 0}%"></span></span><strong>${value}</strong></li>`,
    )
    .join("");
  const categoryItems = Object.entries(state.summary?.by_category ?? {})
    .map(
      ([key, value]) =>
        `<li><span>${escapeHTML(key)}</span><span class="breakdown-track"><span style="--value:${state.summary.total ? (value / state.summary.total) * 100 : 0}%"></span></span><strong>${value}</strong></li>`,
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
        <h2>Resumen de tickets</h2>
      </div>
      <button class="icon-button" type="button" data-action="retry-summary" aria-label="Actualizar resumen" title="Actualizar resumen">${icon("refresh-cw")}</button>
    </div>
    <div class="summary-overview">
      <article><span class="summary-icon">${icon("inbox")}</span><div><span>Total de tickets</span><strong>${state.summary.total}</strong></div></article>
      <article><span class="summary-icon">${icon("badge-check")}</span><div><span>Cerrados con puntuación</span><strong>${state.summary.closed_scored}</strong></div></article>
      <article><span class="summary-icon">${icon("star")}</span><div><span>Satisfacción media</span><strong>${escapeHTML(average)}</strong></div></article>
    </div>
    <div class="summary-breakdowns">
      <div><h4>Por estado</h4><ul>${statusItems}</ul></div>
      <div><h4>Por categoría</h4><ul>${categoryItems}</ul></div>
    </div>
  `;
  renderIcons();
}

function renderIncidents() {
  const section = document.getElementById("incident-list");
  if (!section) return;
  if (state.listLoading) {
    section.innerHTML = `<div class="empty-state">${icon("loader-circle", "spin")}<strong>Cargando tickets...</strong></div>`;
    renderIcons();
    return;
  }
  if (state.listError) {
    section.innerHTML = `
      <p class="error-message">${escapeHTML(state.listError)}</p>
      <button class="secondary-button" type="button" data-action="retry-list">${icon("refresh-cw")}<span>Reintentar</span></button>
    `;
    renderIcons();
    return;
  }
  if (state.incidents.length === 0) {
    section.innerHTML = `<div class="empty-state">${icon("inbox")}<strong>No hay tickets</strong><span>Prueba otros filtros o registra uno nuevo.</span></div>`;
    renderIcons();
    return;
  }

  section.innerHTML = state.incidents
    .map(
      (incident) => `
    <article class="ticket-item">
      <div class="ticket-heading">
        <div><strong>${escapeHTML(incident.ticket_id)}</strong><span class="category-label">${escapeHTML(incident.category)}</span></div>
        <span class="status-label status-${escapeHTML(incident.status.toLowerCase())}">
          ${escapeHTML(STATUS_LABELS[incident.status] ?? incident.status)}
        </span>
      </div>
      <h4>${escapeHTML(incident.client_company)}</h4>
      <p>${escapeHTML(incident.description)}</p>
      <dl class="ticket-facts">
        <div><dt>Fecha</dt><dd>${escapeHTML(incident.date)}</dd></div>
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
        <button class="secondary-button" type="submit">${icon("save")}<span>Guardar</span></button>
      </form>
    </article>
  `,
    )
    .join("");
  renderIcons();
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
      `/api/tickets${query ? `?${query}` : ""}`,
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
    state.summary = await apiRequest("/api/tickets/summary");
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
      <div class="auth-brand"><span class="brand-mark">N</span><span>Nexova Ops</span></div>
      <p class="kicker">Seguridad de cuenta</p>
      <h1>Cambiar contraseña</h1>
      <p class="auth-copy">Actualiza tus credenciales de acceso interno.</p>
      <form id="change-password-form" class="form-stack">
        <label for="current-password">Contraseña actual</label>
        <input id="current-password" name="current_password" type="password" autocomplete="current-password" required />
        <label for="changed-password">Contraseña nueva</label>
        <input id="changed-password" name="new_password" type="password" minlength="8" maxlength="72" autocomplete="new-password" required />
        <label for="changed-password-confirm">Repetir contraseña nueva</label>
        <input id="changed-password-confirm" name="confirm_password" type="password" minlength="8" maxlength="72" autocomplete="new-password" required />
        <button class="primary-button" type="submit">${icon("key-round")}<span>Actualizar contraseña</span></button>
      </form>
      <button class="text-button back-link" type="button" data-action="back-dashboard">${icon("arrow-left")}<span>Volver al panel</span></button>
      <p class="form-message ${messageType === "error" ? "error-message" : ""}" role="status">${escapeHTML(message)}</p>
    </main>
  `;
  renderIcons();
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
    const returnTo = new URLSearchParams(window.location.search).get("next");
    if (
      returnTo?.startsWith("/") &&
      !returnTo.startsWith("//") &&
      !returnTo.includes("\\")
    ) {
      window.location.assign(returnTo);
      return;
    }
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
    await apiRequest("/api/tickets", { method: "POST", body: payload });
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
      button.innerHTML = `${icon("plus")}<span>Registrar ticket</span>`;
      renderIcons();
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
      `/api/tickets/${encodeURIComponent(ticketId)}/status`,
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
  const navLink = event.target.closest?.(".nav-link");
  if (navLink) {
    document.querySelectorAll(".nav-link").forEach((link) => {
      link.classList.toggle("active", link === navLink);
    });
  }
  const button = event.target.closest?.("[data-action]");
  if (!button) return;
  if (button.dataset.action === "toggle-password") {
    const input = document.getElementById(button.dataset.target);
    if (input instanceof HTMLInputElement) {
      const isVisible = input.type === "text";
      input.type = isVisible ? "password" : "text";
      button.setAttribute("aria-pressed", String(!isVisible));
      button.setAttribute(
        "aria-label",
        isVisible ? "Mostrar contraseña" : "Ocultar contraseña",
      );
      button.innerHTML = icon(isVisible ? "eye" : "eye-off");
      renderIcons();
    }
  }
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

window.addEventListener("load", renderIcons);

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
