import { useEffect, useState } from "react";
import { useRouter } from "next/router";

import InventoryShell from "../../../../components/InventoryShell";
import { createInboundOrder, getProducts } from "../../../../lib/inventory";

function icon(name) {
  return <i data-lucide={name} aria-hidden="true" />;
}

const emptyForm = {
  asset_id: "",
  quantity: "",
  supplier: "",
  office: "Valencia",
};

export default function InboundOrderPage() {
  const router = useRouter();
  const [products, setProducts] = useState([]);
  const [productsStatus, setProductsStatus] = useState("loading");
  const [productsError, setProductsError] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let current = true;
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
  }, []);

  useEffect(() => {
    if (!router.isReady || !router.query.asset_id) return;
    const assetId = Array.isArray(router.query.asset_id)
      ? router.query.asset_id[0]
      : router.query.asset_id;
    setForm((previous) => ({ ...previous, asset_id: String(assetId) }));
  }, [router.isReady, router.query.asset_id]);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((previous) => {
      const updates = { [name]: value };
      if (name === "asset_id") {
        const selectedProduct = products.find(
          (product) => String(product.id) === value,
        );
        if (selectedProduct) updates.office = selectedProduct.office;
      }
      return { ...previous, ...updates };
    });
    setNotice("");
    setError("");
  }

  async function submit(event) {
    event.preventDefault();
    setSubmitting(true);
    setNotice("");
    setError("");
    try {
      const result = await createInboundOrder({
        asset_id: Number(form.asset_id),
        quantity: Number(form.quantity),
        supplier: form.supplier.trim(),
        office: form.office,
      });
      setForm(emptyForm);
      setNotice(
        `Entrada registrada: ${result.quantity} unidades para ${result.office}.`,
      );
    } catch (requestError) {
      setError(requestError.message || "No se pudo registrar la entrada.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <InventoryShell
      active="inbound"
      title="Registrar entrada"
      description="Registra compras y entregas recibidas por Nexova."
    >
      <div className="inventory-form-layout">
        <section className="inventory-form-section">
          <div className="inventory-section-heading">
            <span className="inventory-section-icon tone-teal">
              {icon("package-plus")}
            </span>
            <div>
              <p className="inventory-eyebrow">Movimiento de entrada</p>
              <h2>Nueva entrega recibida</h2>
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
            </p>
          )}
          {productsStatus === "ready" && products.length === 0 && (
            <p className="inventory-alert" role="status">
              No hay activos disponibles para recibir una entrada.
            </p>
          )}

          {productsStatus === "ready" && products.length > 0 && (
            <form className="inventory-form" onSubmit={submit}>
              <label htmlFor="inbound-asset">Activo</label>
              <select
                id="inbound-asset"
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

              <div className="inventory-form-grid">
                <div>
                  <label htmlFor="inbound-quantity">Cantidad recibida</label>
                  <input
                    id="inbound-quantity"
                    name="quantity"
                    type="number"
                    min="1"
                    step="1"
                    inputMode="numeric"
                    value={form.quantity}
                    onChange={updateField}
                    required
                  />
                </div>
                <div>
                  <label htmlFor="inbound-office">Oficina receptora</label>
                  <select
                    id="inbound-office"
                    name="office"
                    value={form.office}
                    onChange={updateField}
                  >
                    <option value="Valencia">Valencia</option>
                    <option value="Miami">Miami</option>
                  </select>
                </div>
              </div>

              <label htmlFor="inbound-supplier">Proveedor</label>
              <input
                id="inbound-supplier"
                name="supplier"
                type="text"
                autoComplete="organization"
                maxLength="120"
                value={form.supplier}
                onChange={updateField}
                required
              />

              <div className="inventory-form-footer">
                <p className="inventory-muted">
                  El movimiento quedará asociado a tu cuenta.
                </p>
                <button
                  className="primary-button"
                  type="submit"
                  disabled={submitting}
                >
                  {icon(submitting ? "loader-circle" : "arrow-down-to-line")}
                  <span>
                    {submitting ? "Guardando..." : "Registrar entrada"}
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

        <aside className="inventory-aside-note">
          <p className="inventory-eyebrow">Registro de stock</p>
          <h3>Las entradas aumentan las existencias</h3>
          <p>
            Selecciona el activo recibido, indica cuántas unidades llegaron y en
            qué oficina se almacenan.
          </p>
          <p>
            El stock actual se calcula a partir del historial. No se modifica
            directamente desde el catálogo.
          </p>
        </aside>
      </div>
    </InventoryShell>
  );
}
