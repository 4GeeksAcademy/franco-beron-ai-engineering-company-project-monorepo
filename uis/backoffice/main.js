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

function card(metric) {
  return `
    <article class="metric-card">
      <p class="metric-label">${metric.label}</p>
      <h3>${metric.value}</h3>
      <p class="metric-note">${metric.note}</p>
    </article>
  `;
}

function priorityList(items) {
  return items.map((item) => `<li>${item}</li>`).join("");
}

const app = document.getElementById("app");

app.innerHTML = `
  <aside class="sidebar">
    <h1>Nexova Ops</h1>
    <p>Backoffice interno para supervisores de soporte y coordinacion operativa.</p>
    <nav>
      <a href="#resumen">Resumen</a>
      <a href="#prioridades">Prioridades</a>
      <a href="#privacidad">Privacidad</a>
    </nav>
  </aside>

  <main class="content">
    <header class="content-header" id="resumen">
      <div>
        <p class="kicker">Panel inicial</p>
        <h2>Estado operativo de incidentes</h2>
      </div>
      <span class="tag">Nexova AI Engineering</span>
    </header>

    <section class="metrics-grid">
      ${metrics.map(card).join("")}
    </section>

    <section class="panel" id="prioridades">
      <h3>Prioridades inmediatas</h3>
      <ul>${priorityList(priorities)}</ul>
    </section>

    <section class="panel" id="privacidad">
      <h3>Politica de datos sensibles</h3>
      <p>
        El campo <strong>customer_email</strong> del analisis de incidentes es sensible.
        Este backoffice solo muestra informacion agregada y no expone correos individuales.
      </p>
    </section>
  </main>
`;
