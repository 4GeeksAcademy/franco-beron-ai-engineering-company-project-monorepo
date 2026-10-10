import { useEffect, useState } from "react";

import InventoryShell from "../../components/InventoryShell";
import {
  createIncident,
  getIncidentSummary,
  getIncidents,
  updateIncidentStatus,
} from "../../lib/incidents";

const CATEGORIES = [
  ["technical_failure", "Fallo tecnológico"],
  ["process_error", "Error de proceso"],
  ["client_complaint", "Queja de cliente"],
  ["candidate_issue", "Problema de candidato"],
  ["staff_issue", "Incidencia de personal"],
  ["sla_breach", "Incumplimiento de SLA"],
  ["data_quality", "Calidad de datos"],
  ["other", "Otro"],
];
const STATUSES = [
  ["open", "Abierta"],
  ["in_progress", "En progreso"],
  ["resolved", "Resuelta"],
  ["discarded", "Descartada"],
];
const ORIGINS = [
  ["customer", "Cliente"],
  ["branch", "Sede"],
  ["internal", "Interno"],
];
const BRANCHES = [
  ["central", "Central — Sede Valencia"],
  ["valencia_operations", "Valencia — Operaciones"],
  ["miami_office", "Miami Office"],
  ["remote", "Remoto"],
];
const TRANSITIONS = {
  open: ["open", "in_progress", "discarded"],
  in_progress: ["in_progress", "resolved", "discarded"],
  resolved: ["resolved"],
  discarded: ["discarded"],
};
const LABELS = {
  category: Object.fromEntries(CATEGORIES),
  status: Object.fromEntries(STATUSES),
  origin: Object.fromEntries(ORIGINS),
  branch: Object.fromEntries(BRANCHES),
};
const SUMMARY_GROUPS = [
  ["by_status", "Estado", LABELS.status],
  ["by_category", "Categoría", LABELS.category],
  ["by_origin", "Origen", LABELS.origin],
  ["by_branch", "Sede", LABELS.branch],
];
const INITIAL_FORM = {
  title: "",
  description: "",
  category: "technical_failure",
  status: "open",
  origin: "internal",
  branch: "central",
};
const EMPTY_FILTERS = { status: "", origin: "", branch: "" };

function icon(name, className = "") {
  return <i data-lucide={name} className={className} aria-hidden="true" />;
}

function optionList(options) {
  return options.map(([value, label]) => (
    <option value={value} key={value}>
      {label}
    </option>
  ));
}

function humanize(value, labels) {
  return labels[value] ?? value;
}

function SummaryGroup({ title, values, labels }) {
  return (
    <section className="incident-summary-group">
      <h3>{title}</h3>
      <ul>
        {Object.entries(values ?? {}).map(([value, count]) => (
          <li key={value}>
            <span>{humanize(value, labels)}</span>
            <strong>{count}</strong>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function IncidentsPage() {
  const [form, setForm] = useState(INITIAL_FORM);
  const [formError, setFormError] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [incidents, setIncidents] = useState([]);
  const [listState, setListState] = useState("loading");
  const [listError, setListError] = useState("");
  const [statusErrors, setStatusErrors] = useState({});
  const [updatingId, setUpdatingId] = useState(null);
  const [summary, setSummary] = useState(null);
  const [summaryState, setSummaryState] = useState("loading");
  const [summaryError, setSummaryError] = useState("");
  const [listRevision, setListRevision] = useState(0);
  const [summaryRevision, setSummaryRevision] = useState(0);

  useEffect(() => {
    let active = true;
    setListState("loading");
    setListError("");
    getIncidents(filters)
      .then((items) => {
        if (!active) return;
        setIncidents(items);
        setListState("ready");
      })
      .catch((error) => {
        if (!active) return;
        setListError(error.message || "No se pudieron cargar las incidencias.");
        setListState("error");
      });
    return () => {
      active = false;
    };
  }, [filters.status, filters.origin, filters.branch, listRevision]);

  useEffect(() => {
    let active = true;
    setSummaryState("loading");
    setSummaryError("");
    getIncidentSummary()
      .then((result) => {
        if (!active) return;
        setSummary(result);
        setSummaryState("ready");
      })
      .catch((error) => {
        if (!active) return;
        setSummaryError(error.message || "No se pudo cargar el resumen.");
        setSummaryState("error");
      });
    return () => {
      active = false;
    };
  }, [summaryRevision]);

  function changeForm(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
    setFieldError("");
    setFormError("");
    setSuccess("");
  }

  function changeFilter(event) {
    const { name, value } = event.target;
    setFilters((current) => ({ ...current, [name]: value }));
  }

  async function submitIncident(event) {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    setFieldError("");
    setSuccess("");
    try {
      await createIncident(form);
      setForm(INITIAL_FORM);
      setSuccess("La incidencia se registró correctamente.");
      setListRevision((value) => value + 1);
      setSummaryRevision((value) => value + 1);
    } catch (error) {
      setFormError(
        error.message ||
          "No se pudo registrar la incidencia. Inténtalo de nuevo.",
      );
      setFieldError(error.field || "");
    } finally {
      setSaving(false);
    }
  }

  async function changeIncidentStatus(incident, nextStatus) {
    if (nextStatus === incident.status || updatingId !== null) return;
    const previous = incidents;
    setIncidents((current) =>
      current.map((item) =>
        item.id === incident.id ? { ...item, status: nextStatus } : item,
      ),
    );
    setUpdatingId(incident.id);
    setStatusErrors((current) => ({ ...current, [incident.id]: "" }));
    try {
      await updateIncidentStatus(incident.id, nextStatus);
      setListRevision((value) => value + 1);
      setSummaryRevision((value) => value + 1);
    } catch (error) {
      setIncidents(previous);
      setStatusErrors((current) => ({
        ...current,
        [incident.id]:
          error.message ||
          "No se pudo actualizar el estado. Se restauró el anterior.",
      }));
    } finally {
      setUpdatingId(null);
    }
  }

  return (
    <InventoryShell
      active="incidents"
      title="Gestor de incidencias"
      eyebrow="Operaciones · Soporte"
      description="Registro y seguimiento centralizado de incidencias de Nexova."
    >
      <div className="incident-manager">
        <section className="incident-summary" aria-live="polite">
          <div className="incident-summary-heading">
            <div>
              <p className="kicker">Visión general</p>
              <h2>Resumen de incidencias</h2>
            </div>
            {summaryState === "ready" && (
              <div className="incident-total">
                <span>Total registrado</span>
                <strong>{summary?.total ?? 0}</strong>
              </div>
            )}
          </div>
          {summaryState === "loading" && (
            <p className="incident-feedback" role="status">
              {icon("loader-circle", "spin")} Cargando métricas…
            </p>
          )}
          {summaryState === "error" && (
            <div
              className="incident-feedback incident-feedback-error"
              role="alert"
            >
              <span>{summaryError}</span>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setSummaryRevision((value) => value + 1)}
              >
                {icon("refresh-cw")} Reintentar
              </button>
            </div>
          )}
          {summaryState === "ready" && (
            <div className="incident-summary-grid">
              {SUMMARY_GROUPS.map(([key, title, labels]) => (
                <SummaryGroup
                  key={key}
                  title={title}
                  values={summary?.[key] ?? {}}
                  labels={labels}
                />
              ))}
            </div>
          )}
        </section>

        <div className="incident-workspace">
          <section className="panel incident-form-panel">
            <div className="panel-heading">
              <span className="section-icon">{icon("square-pen")}</span>
              <div>
                <p className="kicker">Registro</p>
                <h2>Nueva incidencia</h2>
              </div>
            </div>
            <form className="form-stack" onSubmit={submitIncident}>
              <label>
                Título
                <input
                  name="title"
                  maxLength={120}
                  value={form.title}
                  onChange={changeForm}
                  aria-invalid={fieldError === "title"}
                  required
                />
              </label>
              {fieldError === "title" && (
                <span className="incident-field-error">Revisa el título.</span>
              )}
              <label>
                Descripción
                <textarea
                  name="description"
                  value={form.description}
                  onChange={changeForm}
                  aria-invalid={fieldError === "description"}
                  required
                />
              </label>
              {fieldError === "description" && (
                <span className="incident-field-error">
                  La descripción es obligatoria.
                </span>
              )}
              <label>
                Categoría
                <select
                  name="category"
                  value={form.category}
                  onChange={changeForm}
                  aria-invalid={fieldError === "category"}
                  required
                >
                  {optionList(CATEGORIES)}
                </select>
              </label>
              {fieldError === "category" && (
                <span className="incident-field-error">
                  Selecciona una categoría válida.
                </span>
              )}
              <label>
                Estado inicial
                <select
                  name="status"
                  value={form.status}
                  onChange={changeForm}
                  required
                >
                  {optionList(STATUSES)}
                </select>
              </label>
              <label>
                Origen
                <select
                  name="origin"
                  value={form.origin}
                  onChange={changeForm}
                  required
                >
                  {optionList(ORIGINS)}
                </select>
              </label>
              <label
                className={
                  form.origin === "branch" ? "incident-branch-emphasis" : ""
                }
              >
                Sede
                <select
                  name="branch"
                  value={form.branch}
                  onChange={changeForm}
                  aria-invalid={fieldError === "branch"}
                  required
                >
                  {optionList(BRANCHES)}
                </select>
              </label>
              {form.origin === "branch" && (
                <p className="incident-branch-note">
                  Selecciona la sede desde la que se reporta.
                </p>
              )}
              {fieldError === "origin" && (
                <span className="incident-field-error">
                  Selecciona un origen válido.
                </span>
              )}
              {fieldError === "branch" && (
                <span className="incident-field-error">
                  Selecciona una sede válida.
                </span>
              )}
              <button
                className="primary-button"
                type="submit"
                disabled={saving}
              >
                {icon(saving ? "loader-circle" : "plus", saving ? "spin" : "")}
                <span>{saving ? "Registrando…" : "Registrar incidencia"}</span>
              </button>
              {formError && (
                <p className="form-message error-message" role="alert">
                  {formError}
                </p>
              )}
              {success && (
                <p className="form-message incident-success" role="status">
                  {success}
                </p>
              )}
            </form>
          </section>

          <section className="panel incident-list-panel">
            <div className="section-heading">
              <div>
                <p className="kicker">Seguimiento</p>
                <h2>Incidencias registradas</h2>
              </div>
              <button
                className="icon-button"
                type="button"
                aria-label="Actualizar incidencias"
                title="Actualizar incidencias"
                onClick={() => setListRevision((value) => value + 1)}
              >
                {icon("refresh-cw")}
              </button>
            </div>
            <div className="incident-filters">
              <label>
                Estado
                <select
                  name="status"
                  value={filters.status}
                  onChange={changeFilter}
                >
                  <option value="">Todos</option>
                  {optionList(STATUSES)}
                </select>
              </label>
              <label>
                Origen
                <select
                  name="origin"
                  value={filters.origin}
                  onChange={changeFilter}
                >
                  <option value="">Todos</option>
                  {optionList(ORIGINS)}
                </select>
              </label>
              <label>
                Sede
                <select
                  name="branch"
                  value={filters.branch}
                  onChange={changeFilter}
                >
                  <option value="">Todas</option>
                  {optionList(BRANCHES)}
                </select>
              </label>
            </div>
            {listState === "loading" && (
              <div className="incident-empty" role="status">
                {icon("loader-circle", "spin")} Cargando incidencias…
              </div>
            )}
            {listState === "error" && (
              <div
                className="incident-empty incident-feedback-error"
                role="alert"
              >
                <span>{listError}</span>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => setListRevision((value) => value + 1)}
                >
                  {icon("refresh-cw")} Reintentar
                </button>
              </div>
            )}
            {listState === "ready" && incidents.length === 0 && (
              <div className="incident-empty">
                {icon("inbox")}
                <strong>
                  {Object.values(filters).some(Boolean)
                    ? "No hay resultados para estos filtros"
                    : "Aún no hay incidencias registradas"}
                </strong>
                <span>
                  {Object.values(filters).some(Boolean)
                    ? "Cambia los filtros para consultar otras incidencias."
                    : "Las incidencias nuevas aparecerán aquí."}
                </span>
              </div>
            )}
            {listState === "ready" && incidents.length > 0 && (
              <div className="incident-items" aria-live="polite">
                {incidents.map((incident) => (
                  <article className="incident-item" key={incident.id}>
                    <div className="incident-item-heading">
                      <div>
                        <h3>{incident.title}</h3>
                        <span
                          className={`incident-status status-${incident.status}`}
                        >
                          {humanize(incident.status, LABELS.status)}
                        </span>
                      </div>
                      <time dateTime={incident.created_at}>
                        {new Intl.DateTimeFormat("es-ES", {
                          dateStyle: "medium",
                          timeStyle: "short",
                        }).format(new Date(incident.created_at))}
                      </time>
                    </div>
                    <p className="incident-description">
                      {incident.description}
                    </p>
                    <dl className="incident-facts">
                      <div>
                        <dt>Categoría</dt>
                        <dd>{humanize(incident.category, LABELS.category)}</dd>
                      </div>
                      <div>
                        <dt>Origen</dt>
                        <dd>{humanize(incident.origin, LABELS.origin)}</dd>
                      </div>
                      <div>
                        <dt>Sede</dt>
                        <dd>{humanize(incident.branch, LABELS.branch)}</dd>
                      </div>
                    </dl>
                    <label className="incident-status-control">
                      Actualizar estado
                      <select
                        value={incident.status}
                        disabled={
                          updatingId !== null ||
                          TRANSITIONS[incident.status].length === 1
                        }
                        onChange={(event) =>
                          void changeIncidentStatus(
                            incident,
                            event.target.value,
                          )
                        }
                      >
                        {TRANSITIONS[incident.status].map((value) => (
                          <option value={value} key={value}>
                            {humanize(value, LABELS.status)}
                          </option>
                        ))}
                      </select>
                      {statusErrors[incident.id] && (
                        <span className="incident-field-error" role="alert">
                          {statusErrors[incident.id]}
                        </span>
                      )}
                    </label>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </InventoryShell>
  );
}
