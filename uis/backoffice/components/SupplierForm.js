import Icon from "./Icon";

export default function SupplierForm({
  categories,
  form,
  onChange,
  onCategoryToggle,
  onSubmit,
  error,
  saving,
}) {
  return (
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
      <form className="supplier-form" onSubmit={onSubmit}>
        <div className="supplier-form-grid">
          <label>
            Nombre comercial
            <input
              name="name"
              value={form.name}
              onChange={onChange}
              required
              maxLength="160"
            />
          </label>
          <label>
            País del contrato
            <select name="country" value={form.country} onChange={onChange}>
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
              onChange={onChange}
              required
            />
          </label>
          <label>
            Moneda
            <input value={form.country === "Spain" ? "EUR" : "USD"} readOnly />
          </label>
          <label>
            Estado inicial
            <select name="status" value={form.status} onChange={onChange}>
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
              onChange={onChange}
            />
          </label>
          <label>
            Email de contacto
            <input
              name="contact_email"
              type="email"
              autoComplete="email"
              value={form.contact_email}
              onChange={onChange}
            />
          </label>
          <label className="supplier-notes-field">
            Notas internas
            <textarea
              name="notes"
              rows="2"
              value={form.notes}
              onChange={onChange}
            />
          </label>
        </div>
        <fieldset className="supplier-category-fieldset">
          <legend>Categorías de servicio</legend>
          <div className="supplier-category-options">
            {categories.map(([value, label]) => (
              <label className="supplier-category-option" key={value}>
                <input
                  type="checkbox"
                  checked={form.categories.includes(value)}
                  onChange={() => onCategoryToggle(value)}
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
        </fieldset>
        {error && (
          <p className="supplier-error" role="alert">
            {error}
          </p>
        )}
        <div className="supplier-form-actions">
          <p className="inventory-muted">
            La fecha de actualización la asigna el sistema.
          </p>
          <button className="primary-button" type="submit" disabled={saving}>
            {saving ? <Icon name="loader-circle" /> : <Icon name="save" />}
            <span>{saving ? "Guardando..." : "Guardar proveedor"}</span>
          </button>
        </div>
      </form>
    </section>
  );
}
