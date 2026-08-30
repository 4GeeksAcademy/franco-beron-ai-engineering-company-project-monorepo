export function nav(items) {
  const links = items
    .map((item) => `<a href="${item.href}">${item.label}</a>`)
    .join("");

  return `
    <header class="topbar">
      <div class="brand">
        <span class="brand-mark">NX</span>
        <span class="brand-text">Nexova</span>
      </div>
      <nav class="menu">${links}</nav>
      <a class="btn btn-outline" href="#contacto">Hablar con un asesor</a>
    </header>
  `;
}

export function hero({ title, subtitle, ctaPrimary, ctaSecondary }) {
  return `
    <section class="hero" id="inicio">
      <div>
        <p class="eyebrow">Outsourcing de soporte + consultoria RR. HH.</p>
        <h1>${title}</h1>
        <p class="hero-copy">${subtitle}</p>
        <div class="hero-actions">
          <a class="btn btn-solid" href="#servicios">${ctaPrimary}</a>
          <a class="btn btn-ghost" href="#modelo">${ctaSecondary}</a>
        </div>
      </div>
      <aside class="hero-card" aria-label="indicadores">
        <h2>Operacion global</h2>
        <ul>
          <li><strong>Valencia + Miami</strong><span>Presencia operativa</span></li>
          <li><strong>30 agentes</strong><span>Equipo de soporte dedicado</span></li>
          <li><strong>SLA 24h</strong><span>Compromiso actual con clientes</span></li>
        </ul>
      </aside>
    </section>
  `;
}

export function featureGrid(title, items, id) {
  const cards = items
    .map(
      (item) => `
      <article class="card">
        <h3>${item.title}</h3>
        <p>${item.description}</p>
      </article>
    `,
    )
    .join("");

  return `
    <section class="section" id="${id}">
      <h2>${title}</h2>
      <div class="grid">${cards}</div>
    </section>
  `;
}

export function timeline(id, steps) {
  const rows = steps
    .map(
      (step) => `
      <li>
        <span class="step">${step.step}</span>
        <p>${step.text}</p>
      </li>
    `,
    )
    .join("");

  return `
    <section class="section" id="${id}">
      <h2>Como trabajamos</h2>
      <ol class="timeline">${rows}</ol>
    </section>
  `;
}

export function footer() {
  return `
    <footer class="footer" id="contacto">
      <div>
        <h2>Nexova</h2>
        <p>
          Consultoria y outsourcing de RR. HH. con operacion especializada en soporte al cliente.
        </p>
      </div>
      <div class="footer-meta">
        <p>Valencia, Espana · Miami, USA</p>
        <p>Clientes: tecnologia, retail y finanzas</p>
      </div>
    </footer>
  `;
}
