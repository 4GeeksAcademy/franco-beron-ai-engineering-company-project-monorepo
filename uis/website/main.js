import { featureGrid, footer, hero, nav, timeline } from "./components.js";

const navItems = [
  { label: "Inicio", href: "#inicio" },
  { label: "Servicios", href: "#servicios" },
  { label: "Modelo", href: "#modelo" },
  { label: "Contacto", href: "#contacto" },
];

const services = [
  {
    title: "Outsourcing de soporte al cliente",
    description:
      "Equipos dedicados para telefono, correo y chat web, con foco en continuidad y calidad de respuesta.",
  },
  {
    title: "Consultoria de RR. HH.",
    description:
      "Diseno de procesos y operacion de talento para alinear personas, servicio y crecimiento del negocio.",
  },
  {
    title: "Analitica operativa",
    description:
      "Lectura estructurada de tickets, backlog y satisfaccion para detectar brechas de SLA y priorizar mejoras.",
  },
];

const valueProps = [
  {
    title: "Visibilidad real del soporte",
    description:
      "Transformamos datos de helpdesk legado en reportes claros para supervisores y lideres de cuenta.",
  },
  {
    title: "Proteccion de datos sensibles",
    description:
      "Disenamos flujos de analisis que evitan exponer informacion sensible de clientes en salidas operativas.",
  },
  {
    title: "Decision basada en evidencia",
    description:
      "Distribuciones por categoria, estado y satisfaccion para tomar acciones concretas antes de revisiones con clientes.",
  },
];

const steps = [
  {
    step: "01",
    text: "Integramos informacion de tickets y validamos calidad de datos sin comprometer privacidad.",
  },
  {
    step: "02",
    text: "Priorizamos backlog segun impacto en SLA y satisfaccion del cliente final.",
  },
  {
    step: "03",
    text: "Convertimos hallazgos en planes de mejora para equipos de soporte y operaciones.",
  },
];

const app = document.getElementById("app");

app.innerHTML = `
  <main class="shell">
    ${nav(navItems)}
    ${hero({
      title: "Soporte al cliente de alto impacto para operaciones exigentes",
      subtitle:
        "En Nexova ayudamos a empresas de tecnologia, retail y finanzas a reducir friccion operativa, mejorar satisfaccion y sostener compromisos de servicio con equipos especializados.",
      ctaPrimary: "Ver servicios",
      ctaSecondary: "Conocer modelo",
    })}
    ${featureGrid("Servicios para operaciones en crecimiento", services, "servicios")}
    ${featureGrid("Propuesta de valor", valueProps, "modelo")}
    ${timeline("metodologia", steps)}
    ${footer()}
  </main>
`;
