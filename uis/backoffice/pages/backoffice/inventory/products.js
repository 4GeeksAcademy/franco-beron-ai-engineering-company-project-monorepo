import Link from "next/link";
import { useEffect, useState } from "react";

import InventoryShell from "../../../components/InventoryShell";
import { getProducts } from "../../../lib/inventory";

// Menos de cinco unidades indica stock bajo; cero unidades indica agotado.
const LOW_STOCK_THRESHOLD = 5;

function icon(name) {
  return <i data-lucide={name} aria-hidden="true" />;
}

function StockStatus({ quantity }) {
  if (quantity === 0) {
    return (
      <span className="stock-badge stock-empty">{icon("circle-x")}Agotado</span>
    );
  }
  if (quantity < LOW_STOCK_THRESHOLD) {
    return (
      <span className="stock-badge stock-low">
        {icon("triangle-alert")}Stock bajo
      </span>
    );
  }
  return (
    <span className="stock-badge stock-healthy">
      {icon("circle-check")}Saludable
    </span>
  );
}

export default function InventoryProductsPage() {
  const [products, setProducts] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");

  async function loadProducts() {
    setStatus("loading");
    setError("");
    try {
      setProducts(await getProducts());
      setStatus("ready");
    } catch (requestError) {
      setError(requestError.message || "No se pudieron cargar los activos.");
      setStatus("error");
    }
  }

  useEffect(() => {
    void loadProducts();
  }, []);

  const lowStockCount = products.filter(
    (product) => product.current_stock < LOW_STOCK_THRESHOLD,
  ).length;

  return (
    <InventoryShell
      active="products"
      title="Activos"
      description="Consulta existencias y registra movimientos por oficina."
    >
      <div className="inventory-toolbar">
        <div>
          <p className="inventory-eyebrow">Catálogo de activos</p>
          <h2>Stock disponible</h2>
          <p className="inventory-muted">
            El stock se calcula a partir de entradas y salidas registradas.
          </p>
        </div>
        <div className="inventory-actions">
          <Link
            className="primary-button"
            href="/backoffice/inventory/orders/inbound"
          >
            {icon("package-plus")}
            <span>Registrar entrada</span>
          </Link>
          <Link
            className="secondary-button"
            href="/backoffice/inventory/orders/outbound"
          >
            {icon("package-minus")}
            <span>Registrar salida</span>
          </Link>
        </div>
      </div>

      {status === "loading" && (
        <div className="inventory-state" role="status">
          <span className="inventory-spinner" aria-hidden="true" />
          Cargando activos...
        </div>
      )}
      {status === "error" && (
        <div className="inventory-alert inventory-alert-error" role="alert">
          <span>{error}</span>
          <button
            className="secondary-button"
            type="button"
            onClick={loadProducts}
          >
            {icon("refresh-cw")}
            <span>Reintentar</span>
          </button>
        </div>
      )}
      {status === "ready" && products.length === 0 && (
        <div className="inventory-state">
          <strong>No hay activos registrados</strong>
          <span>
            Los activos aparecerán aquí cuando estén disponibles en el catálogo.
          </span>
        </div>
      )}
      {status === "ready" && products.length > 0 && (
        <>
          <div className="inventory-summary-line">
            <span>{products.length} activos</span>
            <span className="stock-legend">
              {icon("triangle-alert")} {lowStockCount} con menos de{" "}
              {LOW_STOCK_THRESHOLD} unidades
            </span>
          </div>
          <div className="inventory-table-wrap">
            <table className="inventory-table">
              <thead>
                <tr>
                  <th scope="col">Activo</th>
                  <th scope="col">SKU</th>
                  <th scope="col">Categoría</th>
                  <th scope="col">Oficina</th>
                  <th scope="col">Stock actual</th>
                  <th scope="col">
                    <span className="visually-hidden">Acciones</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.id}>
                    <th scope="row" className="asset-name">
                      {product.name}
                    </th>
                    <td>
                      <code>{product.sku}</code>
                    </td>
                    <td>
                      <span className="inventory-category">
                        {product.category.replaceAll("_", " ")}
                      </span>
                    </td>
                    <td>{product.office}</td>
                    <td>
                      <div className="stock-cell">
                        <strong>{product.current_stock}</strong>
                        <StockStatus quantity={product.current_stock} />
                      </div>
                    </td>
                    <td>
                      <div className="row-actions">
                        <Link
                          className="icon-button"
                          href={`/backoffice/inventory/orders/inbound?asset_id=${product.id}`}
                          aria-label={`Registrar entrada de ${product.name}`}
                          title={`Registrar entrada de ${product.name}`}
                        >
                          {icon("arrow-down-to-line")}
                        </Link>
                        <Link
                          className="icon-button"
                          href={`/backoffice/inventory/orders/outbound?asset_id=${product.id}`}
                          aria-label={`Registrar salida de ${product.name}`}
                          title={`Registrar salida de ${product.name}`}
                        >
                          {icon("arrow-up-from-line")}
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </InventoryShell>
  );
}
