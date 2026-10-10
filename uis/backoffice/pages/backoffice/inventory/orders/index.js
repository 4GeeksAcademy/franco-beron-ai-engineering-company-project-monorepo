import { useEffect, useState } from "react";

import InventoryShell from "../../../../components/InventoryShell";
import { getOrders } from "../../../../lib/inventory";

function icon(name) {
  return <i data-lucide={name} aria-hidden="true" />;
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Fecha no disponible";
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function InventoryOrdersPage() {
  const [orders, setOrders] = useState([]);
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState("");

  async function loadOrders() {
    setStatus("loading");
    setError("");
    try {
      setOrders(await getOrders());
      setStatus("ready");
    } catch (requestError) {
      setError(requestError.message || "No se pudo cargar el historial.");
      setStatus("error");
    }
  }

  useEffect(() => {
    void loadOrders();
  }, []);

  return (
    <InventoryShell
      active="orders"
      title="Historial de movimientos"
      description="Consulta las entradas y salidas registradas por el equipo."
    >
      <div className="inventory-toolbar">
        <div>
          <p className="inventory-eyebrow">Trazabilidad</p>
          <h2>Movimientos de inventario</h2>
          <p className="inventory-muted">
            Vista de solo lectura con responsable y fecha de registro.
          </p>
        </div>
        <button
          className="secondary-button"
          type="button"
          onClick={loadOrders}
          disabled={status === "loading"}
        >
          {icon("refresh-cw")}
          <span>Actualizar</span>
        </button>
      </div>

      {status === "loading" && (
        <div className="inventory-state" role="status">
          <span className="inventory-spinner" aria-hidden="true" />
          Cargando movimientos...
        </div>
      )}
      {status === "error" && (
        <div className="inventory-alert inventory-alert-error" role="alert">
          <span>{error}</span>
          <button
            className="secondary-button"
            type="button"
            onClick={loadOrders}
          >
            {icon("refresh-cw")}
            <span>Reintentar</span>
          </button>
        </div>
      )}
      {status === "ready" && orders.length === 0 && (
        <div className="inventory-state">
          <strong>Sin movimientos registrados</strong>
          <span>
            Las próximas entradas y salidas aparecerán en este historial.
          </span>
        </div>
      )}
      {status === "ready" && orders.length > 0 && (
        <>
          <div className="inventory-summary-line">
            <span>{orders.length} movimientos</span>
            <span className="history-legend">
              <span className="order-type order-inbound">
                {icon("arrow-down-to-line")} Entrada
              </span>
              <span className="order-type order-outbound">
                {icon("arrow-up-from-line")} Salida
              </span>
            </span>
          </div>
          <div className="inventory-table-wrap">
            <table className="inventory-table inventory-orders-table">
              <thead>
                <tr>
                  <th scope="col">Movimiento</th>
                  <th scope="col">Activo</th>
                  <th scope="col">Cantidad</th>
                  <th scope="col">Oficina</th>
                  <th scope="col">Fecha</th>
                  <th scope="col">Registrado por</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((order) => {
                  const inbound = order.order_type === "inbound";
                  return (
                    <tr key={`${order.order_type}-${order.id}`}>
                      <td>
                        <span
                          className={`order-type ${inbound ? "order-inbound" : "order-outbound"}`}
                        >
                          {icon(
                            inbound
                              ? "arrow-down-to-line"
                              : "arrow-up-from-line",
                          )}
                          {inbound ? "Entrada" : "Salida"}
                        </span>
                        <span className="order-subtype">
                          {inbound
                            ? order.supplier
                            : order.exit_type === "allocation"
                              ? `Asignado a ${order.assigned_to}`
                              : "Consumo"}
                        </span>
                      </td>
                      <th scope="row" className="asset-name">
                        {order.asset_name}
                        <small>{order.asset_sku}</small>
                      </th>
                      <td className="quantity-cell">
                        {inbound ? "+" : "−"}
                        {order.quantity}
                      </td>
                      <td>{order.office}</td>
                      <td>{formatDate(order.created_at)}</td>
                      <td>
                        <code className="user-uuid" title={order.user_uuid}>
                          {order.user_uuid}
                        </code>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </InventoryShell>
  );
}
