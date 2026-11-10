import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

import InventoryShell from "../../../../components/InventoryShell";
import { getOrders } from "../../../../lib/inventory";
import Icon from "../../../../components/Icon";

const InventoryOrdersTable = dynamic(
  () => import("../../../../components/InventoryOrdersTable"),
  {
    loading: () => (
      <div className="inventory-state" role="status">
        Preparando historial...
      </div>
    ),
  },
);

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
          <Icon name="refresh-cw" />
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
            <Icon name="refresh-cw" />
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
                <Icon name="arrow-down-to-line" /> Entrada
              </span>
              <span className="order-type order-outbound">
                <Icon name="arrow-up-from-line" /> Salida
              </span>
            </span>
          </div>
          <InventoryOrdersTable orders={orders} />
        </>
      )}
    </InventoryShell>
  );
}
