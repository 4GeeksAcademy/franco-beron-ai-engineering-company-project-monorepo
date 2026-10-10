import { useEffect, useState } from "react";
import { useRouter } from "next/router";

import InventoryShell from "../../../../components/InventoryShell";
import {
  createOutboundOrder,
  getProduct,
  getProducts,
} from "../../../../lib/inventory";

function icon(name) {
  return <i data-lucide={name} aria-hidden="true" />;
}

const emptyForm = {
  asset_id: "",
  quantity: "",
  exit_type: "allocation",
  assigned_to: "",
  office: "Valencia",
};

export default function OutboundOrderPage() {
  const router = useRouter();
  const [products, setProducts] = useState([]);
  const [productsStatus, setProductsStatus] = useState("loading");
  const [productsError, setProductsError] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [stockStatus, setStockStatus] = useState("empty");
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [quantityError, setQuantityError] = useState("");
  const [reload, setReload] = useState(0);
  const [stockReload, setStockReload] = useState(0);

  useEffect(() => {
    let current = true;
    setProductsStatus("loading");
    setProductsError("");
    getProducts()
      .then((items) => {
        if (!current) return;
        setProducts(items);
        setProductsStatus("ready");
      })
      .catch((requestError) => {
        if (!current) return;
        setProductsError(
          requestError.message || "No se pudieron cargar los activos.",
        );
        setProductsStatus("error");
      });
    return () => {
      current = false;
    };
  }, [reload]);

  useEffect(() => {
    if (!router.isReady || !router.query.asset_id) return;
    const assetId = Array.isArray(router.query.asset_id)
      ? router.query.asset_id[0]
      : router.query.asset_id;
    setForm((previous) => ({ ...previous, asset_id: String(assetId) }));
  }, [router.isReady, router.query.asset_id]);

  useEffect(() => {
    if (!form.asset_id) {
      setSelectedAsset(null);
      setStockStatus("empty");
      return undefined;
    }

    let current = true;
    setStockStatus("loading");
    setQuantityError("");
    getProduct(form.asset_id)
      .then((asset) => {
        if (!current) return;
        setSelectedAsset(asset);
        setStockStatus("ready");
        setForm((previous) => ({ ...previous, office: asset.office }));
      })
      .catch((requestError) => {
        if (!current) return;
        setSelectedAsset(null);
        setStockStatus("error");
        setQuantityError(
          requestError.message || "No se pudo consultar el stock actual.",
        );
      });
    return () => {
      current = false;
    };
  }, [form.asset_id, stockReload]);

  const quantity = Number(form.quantity);
  const exceedsStock =
    stockStatus === "ready" &&
    form.quantity !== "" &&
    Number.isFinite(quantity) &&
    quantity > (selectedAsset?.current_stock ?? 0);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
    setNotice("");
    setError("");
    setQuantityError("");
  }

  async function submit(event) {
    event.preventDefault();
    setNotice("");
    setError("");
    setQuantityError("");

    if (exceedsStock) {
      setQuantityError("La cantidad supera el stock disponible.");
      return;
    }
    if (form.exit_type === "allocation" && !form.assigned_to.trim()) {
      setError("Indica a quién se asigna este activo.");
      return;
    }

    setSubmitting(true);
    try {
      const result = await createOutboundOrder({
        asset_id: Number(form.asset_id),
        quantity,
        exit_type: form.exit_type,
        assigned_to:
          form.exit_type === "allocation" ? form.assigned_to.trim() : null,
        office: form.office,
      });
      setForm(emptyForm);
      setSelectedAsset(null);
      setNotice(
        `Salida registrada: ${result.quantity} unidades de ${selectedAsset?.name ?? "activo"}.`,
      );
      setStockStatus("empty");
    } catch (requestError) {
      if (requestError.status === 400) {
        setQuantityError(requestError.message || "Stock insuficiente.");
      } else {
        setError(requestError.message || "No se pudo registrar la salida.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <InventoryShell
      active="outbound"
      title="Registrar salida"
      description="Registra asignaciones a empleados o consumos de suministros."
    >
      <div className="inventory-form-layout">
        <section className="inventory-form-section">
          <div className="inventory-section-heading">
            <span className="inventory-section-icon tone-coral">
              {icon("package-minus")}
            </span>
            <div>
              <p className="inventory-eyebrow">Movimiento de salida</p>
              <h2>Nueva asignación o consumo</h2>
            </div>
          </div>

          {productsStatus === "loading" && (
            <p className="inventory-muted" role="status">
              Cargando catálogo de activos...
            </p>
          )}
          {productsStatus === "error" && (
            <p className="inventory-alert inventory-alert-error" role="alert">
              {productsError}
              <button
                className="secondary-button"
                type="button"
                onClick={() => setReload((value) => value + 1)}
              >
                {icon("refresh-cw")} Reintentar
              </button>
            </p>
          )}
          {productsStatus === "ready" && products.length === 0 && (
            <p className="inventory-alert" role="status">
              No hay activos disponibles para registrar una salida.
            </p>
          )}

          {productsStatus === "ready" && products.length > 0 && (
            <form className="inventory-form" onSubmit={submit}>
              <label htmlFor="outbound-asset">Activo</label>
              <select
                id="outbound-asset"
                name="asset_id"
                value={form.asset_id}
                onChange={updateField}
                required
              >
                <option value="" disabled>
                  Selecciona un activo
                </option>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name} · {product.sku} · {product.office}
                  </option>
                ))}
              </select>

              {form.asset_id && (
                <div
                  className={`available-stock ${stockStatus === "ready" && selectedAsset.current_stock === 0 ? "available-stock-empty" : ""}`}
                  aria-live="polite"
                >
                  {stockStatus === "loading" && (
                    <>
                      <span className="inventory-spinner" aria-hidden="true" />
                      Consultando existencias...
                    </>
                  )}
                  {stockStatus === "ready" && (
                    <>
                      <span>{icon("boxes")}Disponible ahora</span>
                      <strong>
                        {selectedAsset.current_stock} <small>unidades</small>
                      </strong>
                    </>
                  )}
                  {stockStatus === "error" && (
                    <span role="alert">
                      {quantityError}
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => setStockReload((value) => value + 1)}
                      >
                        {icon("refresh-cw")} Reintentar
                      </button>
                    </span>
                  )}
                </div>
              )}

              <div>
                <label htmlFor="outbound-quantity">Cantidad de salida</label>
                <input
                  id="outbound-quantity"
                  name="quantity"
                  type="number"
                  min="1"
                  step="1"
                  inputMode="numeric"
                  value={form.quantity}
                  onChange={updateField}
                  aria-invalid={Boolean(quantityError || exceedsStock)}
                  aria-describedby={
                    quantityError || exceedsStock
                      ? "outbound-quantity-message"
                      : undefined
                  }
                  required
                />
                {exceedsStock && (
                  <p
                    className="field-warning"
                    id="outbound-quantity-message"
                    role="alert"
                  >
                    {icon("triangle-alert")} Solicitas {quantity} y solo hay{" "}
                    {selectedAsset.current_stock} unidades disponibles.
                  </p>
                )}
                {quantityError && !exceedsStock && (
                  <p
                    className="field-error"
                    id="outbound-quantity-message"
                    role="alert"
                  >
                    {quantityError}
                  </p>
                )}
              </div>

              <div className="inventory-form-grid">
                <div>
                  <label htmlFor="outbound-type">Tipo de salida</label>
                  <select
                    id="outbound-type"
                    name="exit_type"
                    value={form.exit_type}
                    onChange={updateField}
                  >
                    <option value="allocation">Asignación a empleado</option>
                    <option value="consumption">Consumo</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="outbound-office">Oficina</label>
                  <select
                    id="outbound-office"
                    name="office"
                    value={form.office}
                    onChange={updateField}
                  >
                    <option value="Valencia">Valencia</option>
                    <option value="Miami">Miami</option>
                  </select>
                </div>
              </div>

              {form.exit_type === "allocation" && (
                <div>
                  <label htmlFor="outbound-assignee">Persona asignada</label>
                  <input
                    id="outbound-assignee"
                    name="assigned_to"
                    type="text"
                    autoComplete="name"
                    maxLength="120"
                    value={form.assigned_to}
                    onChange={updateField}
                    required
                  />
                </div>
              )}

              <div className="inventory-form-footer">
                <p className="inventory-muted">
                  La API vuelve a validar que el stock no quede negativo.
                </p>
                <button
                  className="primary-button"
                  type="submit"
                  disabled={
                    submitting || exceedsStock || stockStatus !== "ready"
                  }
                >
                  {icon(submitting ? "loader-circle" : "arrow-up-from-line")}
                  <span>
                    {submitting ? "Guardando..." : "Registrar salida"}
                  </span>
                </button>
              </div>
              {notice && (
                <p
                  className="inventory-alert inventory-alert-success"
                  role="status"
                >
                  {notice}
                </p>
              )}
              {error && (
                <p
                  className="inventory-alert inventory-alert-error"
                  role="alert"
                >
                  {error}
                </p>
              )}
            </form>
          )}
        </section>

        <aside className="inventory-aside-note inventory-aside-coral">
          <p className="inventory-eyebrow">Control de existencias</p>
          <h3>La cantidad disponible se consulta antes de registrar</h3>
          <p>
            Las asignaciones requieren indicar a la persona destinataria. En los
            consumos, ese campo no aplica.
          </p>
          <p>
            Si la salida supera las unidades disponibles, no se podrá enviar.
          </p>
        </aside>
      </div>
    </InventoryShell>
  );
}
