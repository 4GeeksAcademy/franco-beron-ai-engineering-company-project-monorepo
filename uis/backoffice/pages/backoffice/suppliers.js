import { useEffect, useState } from "react";

import InventoryShell from "../../components/InventoryShell";
import {
  createSupplier,
  getSuppliers,
  updateSupplierRate,
  updateSupplierStatus,
} from "../../lib/suppliers";

const CATEGORIES = [
  ["job_boards", "Portales de empleo"],
  ["ats_software", "Software ATS"],
  ["assessment_tools", "Evaluación"],
  ["training_platforms", "Formación"],
  ["payroll_and_hr_software", "Nómina y RR. HH."],
  ["video_interview", "Entrevista por video"],
  ["background_check", "Antecedentes"],
  ["office_and_facilities", "Oficina e instalaciones"],
  ["it_and_software_licenses", "TI y licencias"],
];

const EMPTY_FORM = {
  name: "",
  country: "Spain",
  categories: [],
  monthly_rate: "",
  status: "active",
  contract_renewal_date: "",
  contact_email: "",
  notes: "",
};

function icon(name) {
  return <i data-lucide={name} aria-hidden="true" />;
}

function categoryLabel(value) {
  return CATEGORIES.find(([category]) => category === value)?.[1] ?? value;
}

function formatRate(rate, currency) {
  return new Intl.NumberFormat("es-ES", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(rate);
}

function formatUpdatedAt(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function renewalMeta(value) {
  if (!value) return { label: "Sin fecha", tone: "renewal-none" };
  const renewalDate = new Date(`${value}T00:00:00`);
  if (Number.isNaN(renewalDate.getTime())) {
    return { label: "Fecha no válida", tone: "renewal-none" };
  }
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const daysUntil = Math.ceil((renewalDate - today) / 86400000);
  if (daysUntil < 0) return { label: "Vencida", tone: "renewal-overdue" };
  if (daysUntil <= 60) {
    return {
      label: daysUntil === 0 ? "Hoy" : `En ${daysUntil} días`,
      tone: "renewal-soon",
    };
  }
  return {
    label: new Intl.DateTimeFormat("es-ES", { dateStyle: "medium" }).format(
      renewalDate,
    ),
    tone: "renewal-normal",
  };
}

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState([]);
  const [filters, setFilters] = useState({ country: "", category: "" });
  const [loadState, setLoadState] = useState("loading");
  const [loadError, setLoadError] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [formSuccess, setFormSuccess] = useState("");
  const [saving, setSaving] = useState(false);
  const [editingRateId, setEditingRateId] = useState(null);
  const [rateDraft, setRateDraft] = useState("");
  const [savingRateId, setSavingRateId] = useState(null);
  const [updatingStatusId, setUpdatingStatusId] = useState(null);
  const [rowError, setRowError] = useState("");

  async function reloadSuppliers(nextFilters = filters) {
    setLoadState("loading");
    setLoadError("");
    try {
      setSuppliers(await getSuppliers(nextFilters));
      setLoadState("ready");
    } catch (error) {
      setLoadError(error.message || "No se pudo cargar el directorio.");
      setLoadState("error");
    }
  }

  useEffect(() => {
    let current = true;
    setLoadState("loading");
    setLoadError("");
    getSuppliers(filters)
      .then((items) => {
        if (!current) return;
        setSuppliers(items);
        setLoadState("ready");
      })
      .catch((error) => {
        if (!current) return;
        setLoadError(error.message || "No se pudo cargar el directorio.");
        setLoadState("error");
      });
    return () => {
      current = false;
    };
  }, [filters.country, filters.category]);

  useEffect(() => {
    window.lucide?.createIcons({ attrs: { "stroke-width": 1.8 } });
  }, [formOpen, loadState, suppliers, editingRateId]);

  function updateForm(event) {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
    setFormError("");
    setFormSuccess("");
  }

  function toggleCategory(category) {
    setForm((previous) => ({
      ...previous,
      categories: previous.categories.includes(category)
        ? previous.categories.filter((item) => item !== category)
        : [...previous.categories, category],
    }));
    setFormError("");
  }

  async function submitSupplier(event) {
    event.preventDefault();
    setFormError("");
    setFormSuccess("");

    const monthlyRate = Number(form.monthly_rate);
    if (!form.name.trim()) {
      setFormError("El nombre comercial es obligatorio.");
      return;
    }
    if (form.categories.length === 0) {
      setFormError("Selecciona al menos una categoría.");
      return;
    }
    if (!Number.isFinite(monthlyRate) || monthlyRate <= 0) {
      setFormError("La tarifa mensual debe ser un número mayor que cero.");
      return;
    }

    setSaving(true);
    try {
      await createSupplier({
        name: form.name.trim(),
        country: form.country,
        categories: form.categories,
        monthly_rate: monthlyRate,
        currency: form.country === "Spain" ? "EUR" : "USD",
        status: form.status,
        contract_renewal_date: form.contract_renewal_date || null,
        contact_email: form.contact_email.trim() || null,
        notes: form.notes.trim() || null,
      });
      setForm(EMPTY_FORM);
      setFormOpen(false);
      setFormSuccess("Proveedor registrado correctamente.");
      await reloadSuppliers(filters);
    } catch (error) {
      setFormError(error.message || "No se pudo registrar el proveedor.");
    } finally {
      setSaving(false);
    }
  }

  function startRateEdit(supplier) {
    setEditingRateId(supplier.id);
    setRateDraft(String(supplier.monthly_rate));
    setRowError("");
  }

  async function saveRate(supplier) {
    const monthlyRate = Number(rateDraft);
    if (!Number.isFinite(monthlyRate) || monthlyRate <= 0) {
      setRowError("La tarifa debe ser mayor que cero.");
      return;
    }
    setSavingRateId(supplier.id);
    setRowError("");
    try {
      const updated = await updateSupplierRate(supplier.id, monthlyRate);
      setSuppliers((current) =>
        current.map((item) => (item.id === supplier.id ? updated : item)),
      );
      setEditingRateId(null);
    } catch (error) {
      setRowError(error.message || "No se pudo actualizar la tarifa.");
    } finally {
      setSavingRateId(null);
    }
  }

  async function toggleStatus(supplier) {
    const nextStatus = supplier.status === "active" ? "suspended" : "active";
    setUpdatingStatusId(supplier.id);
    setRowError("");
    try {
      const updated = await updateSupplierStatus(supplier.id, nextStatus);
      setSuppliers((current) =>
        current.map((item) => (item.id === supplier.id ? updated : item)),
      );
    } catch (error) {
      setRowError(error.message || "No se pudo actualizar el estado.");
    } finally {
      setUpdatingStatusId(null);
    }
  }

  return (
    <InventoryShell
      active="suppliers"
      title="Directorio de proveedores"
      description="Gestiona relaciones comerciales, tarifas y renovaciones."
      eyebrow="Compras · Proveedores"
    >
      <div className="supplier-toolbar">
        <div>
          <p className="inventory-eyebrow">Directorio operativo</p>
          <h2>Relaciones comerciales</h2>
          <p className="inventory-muted">
            Filtra proveedores por país y servicio, y mantén sus tarifas
            actualizadas.
          </p>
        </div>
        <div className="supplier-toolbar-actions">
          <button
            className="secondary-button"
            type="button"
            onClick={() => void reloadSuppliers()}
            disabled={loadState === "loading"}
          >
            {icon("refresh-cw")}
            <span>Actualizar</span>
          </button>
          <button
            className="primary-button"
            type="button"
            onClick={() => {
              setFormOpen((value) => !value);
              setFormError("");
              setFormSuccess("");
            }}
          >
            {icon(formOpen ? "x" : "plus")}
            <span>{formOpen ? "Cerrar" : "Nuevo proveedor"}</span>
          </button>
        </div>
      </div>

      {formSuccess && (
        <p className="supplier-notice" role="status">
          {formSuccess}
        </p>
      )}
      {rowError && (
        <p className="supplier-error" role="alert">
          {rowError}
        </p>
      )}

      {formOpen && (
        <section
          className="supplier-form-panel"
          aria-labelledby="supplier-form-title"
        >
          <div className="supplier-form-heading">
            <div>
              <p className="inventory-eyebrow">Alta de proveedor</p>
              <h2 id="supplier-form-title">Datos comerciales</h2>
            </div>
          </div>
          <form className="supplier-form" onSubmit={submitSupplier}>
            <div className="supplier-form-grid">
              <label>
                Nombre comercial
                <input
                  name="name"
                  value={form.name}
                  onChange={updateForm}
                  required
                  maxLength="160"
                />
              </label>
              <label>
                País del contrato
                <select
                  name="country"
                  value={form.country}
                  onChange={updateForm}
                >
                  <option value="Spain">Spain</option>
                  <option value="USA">USA</option>
                </select>
              </label>
              <label>
                Tarifa mensual
                <input
                  name="monthly_rate"
                  type="number"
                  min="0.01"
                  step="0.01"
                  inputMode="decimal"
                  value={form.monthly_rate}
                  onChange={updateForm}
                  required
                />
              </label>
              <label>
                Moneda
                <input
                  value={form.country === "Spain" ? "EUR" : "USD"}
                  readOnly
                />
              </label>
              <label>
                Estado inicial
                <select name="status" value={form.status} onChange={updateForm}>
                  <option value="active">Activo</option>
                  <option value="suspended">Suspendido</option>
                </select>
              </label>
              <label>
                Renovación de contrato
                <input
                  name="contract_renewal_date"
                  type="date"
                  value={form.contract_renewal_date}
                  onChange={updateForm}
                />
              </label>
              <label>
                Email de contacto
                <input
                  name="contact_email"
                  type="email"
                  autoComplete="email"
                  value={form.contact_email}
                  onChange={updateForm}
                />
              </label>
              <label className="supplier-notes-field">
                Notas internas
                <textarea
                  name="notes"
                  rows="2"
                  value={form.notes}
                  onChange={updateForm}
                />
              </label>
            </div>
            <fieldset className="supplier-category-fieldset">
              <legend>Categorías de servicio</legend>
              <div className="supplier-category-options">
                {CATEGORIES.map(([value, label]) => (
                  <label className="supplier-category-option" key={value}>
                    <input
                      type="checkbox"
                      checked={form.categories.includes(value)}
                      onChange={() => toggleCategory(value)}
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </fieldset>
            {formError && (
              <p className="supplier-error" role="alert">
                {formError}
              </p>
            )}
            <div className="supplier-form-actions">
              <p className="inventory-muted">
                La fecha de actualización la asigna el sistema.
              </p>
              <button
                className="primary-button"
                type="submit"
                disabled={saving}
              >
                {icon(saving ? "loader-circle" : "save")}
                <span>{saving ? "Guardando..." : "Guardar proveedor"}</span>
              </button>
            </div>
          </form>
        </section>
      )}

      <section
        className="supplier-directory"
        aria-label="Listado de proveedores"
      >
        <div className="supplier-filters">
          <label>
            País
            <select
              value={filters.country}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  country: event.target.value,
                }))
              }
            >
              <option value="">Todos los países</option>
              <option value="Spain">Spain</option>
              <option value="USA">USA</option>
            </select>
          </label>
          <label>
            Categoría
            <select
              value={filters.category}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  category: event.target.value,
                }))
              }
            >
              <option value="">Todas las categorías</option>
              {CATEGORIES.map(([value, label]) => (
                <option value={value} key={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <span className="supplier-result-count" aria-live="polite">
            {loadState === "ready" ? `${suppliers.length} proveedores` : ""}
          </span>
        </div>

        {loadState === "loading" && (
          <div className="inventory-state" role="status">
            Cargando directorio...
          </div>
        )}
        {loadState === "error" && (
          <div className="inventory-alert inventory-alert-error" role="alert">
            <span>{loadError}</span>
            <button
              className="secondary-button"
              type="button"
              onClick={() => void reloadSuppliers()}
            >
              {icon("refresh-cw")}
              <span>Reintentar</span>
            </button>
          </div>
        )}
        {loadState === "ready" && suppliers.length === 0 && (
          <div className="inventory-state">
            <strong>No hay proveedores para estos filtros</strong>
            <span>Prueba otra combinación o registra un proveedor nuevo.</span>
          </div>
        )}
        {loadState === "ready" && suppliers.length > 0 && (
          <div className="supplier-table-wrap">
            <table className="supplier-table">
              <thead>
                <tr>
                  <th scope="col">Proveedor</th>
                  <th scope="col">País</th>
                  <th scope="col">Categorías</th>
                  <th scope="col">Tarifa mensual</th>
                  <th scope="col">Renovación</th>
                  <th scope="col">Estado</th>
                  <th scope="col">
                    <span className="visually-hidden">Acciones</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {suppliers.map((supplier) => {
                  const renewal = renewalMeta(supplier.contract_renewal_date);
                  const editing = editingRateId === supplier.id;
                  return (
                    <tr
                      key={supplier.id}
                      className={
                        supplier.status === "suspended"
                          ? "supplier-row-suspended"
                          : ""
                      }
                    >
                      <th scope="row" className="supplier-name-cell">
                        <strong>{supplier.name}</strong>
                        {supplier.contact_email && (
                          <a href={`mailto:${supplier.contact_email}`}>
                            {supplier.contact_email}
                          </a>
                        )}
                      </th>
                      <td>{supplier.country}</td>
                      <td>
                        <div className="supplier-category-list">
                          {(supplier.categories ?? []).map((category) => (
                            <span
                              className="supplier-category-tag"
                              key={category}
                            >
                              {categoryLabel(category)}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td>
                        {editing ? (
                          <form
                            className="supplier-rate-edit"
                            onSubmit={(event) => {
                              event.preventDefault();
                              void saveRate(supplier);
                            }}
                          >
                            <input
                              aria-label={`Nueva tarifa mensual para ${supplier.name}`}
                              type="number"
                              min="0.01"
                              step="0.01"
                              value={rateDraft}
                              onChange={(event) =>
                                setRateDraft(event.target.value)
                              }
                              required
                            />
                            <button
                              className="icon-button"
                              type="submit"
                              disabled={savingRateId === supplier.id}
                              aria-label="Guardar tarifa"
                              title="Guardar tarifa"
                            >
                              {icon(
                                savingRateId === supplier.id
                                  ? "loader-circle"
                                  : "check",
                              )}
                            </button>
                            <button
                              className="icon-button"
                              type="button"
                              onClick={() => setEditingRateId(null)}
                              aria-label="Cancelar edición"
                              title="Cancelar"
                            >
                              {icon("x")}
                            </button>
                          </form>
                        ) : (
                          <div className="supplier-rate-cell">
                            <div>
                              <strong>
                                {formatRate(
                                  supplier.monthly_rate,
                                  supplier.currency,
                                )}
                              </strong>
                              <small>
                                Actualizada{" "}
                                {formatUpdatedAt(supplier.updated_at)}
                              </small>
                            </div>
                            <button
                              className="icon-button supplier-edit-rate"
                              type="button"
                              onClick={() => startRateEdit(supplier)}
                              aria-label={`Editar tarifa de ${supplier.name}`}
                              title="Editar tarifa"
                            >
                              {icon("pencil")}
                            </button>
                          </div>
                        )}
                      </td>
                      <td>
                        <span className={`renewal-label ${renewal.tone}`}>
                          {renewal.tone === "renewal-soon" &&
                            icon("triangle-alert")}
                          {renewal.label}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`supplier-status supplier-status-${supplier.status}`}
                        >
                          <span aria-hidden="true" />
                          {supplier.status === "active"
                            ? "Activo"
                            : "Suspendido"}
                        </span>
                      </td>
                      <td>
                        <button
                          className={`supplier-status-action ${supplier.status === "active" ? "action-suspend" : "action-activate"}`}
                          type="button"
                          onClick={() => void toggleStatus(supplier)}
                          disabled={updatingStatusId === supplier.id}
                        >
                          {updatingStatusId === supplier.id
                            ? "Actualizando..."
                            : supplier.status === "active"
                              ? "Suspender"
                              : "Activar"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </InventoryShell>
  );
}
