import Icon from "./Icon";

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Fecha no disponible";
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function InventoryOrdersTable({ orders }) {
  return (
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
                <td data-label="Movimiento">
                  <span
                    className={`order-type ${inbound ? "order-inbound" : "order-outbound"}`}
                  >
                    {inbound ? (
                      <Icon name="arrow-down-to-line" />
                    ) : (
                      <Icon name="arrow-up-from-line" />
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
                <th scope="row" className="asset-name" data-label="Activo">
                  {order.asset_name}
                  <small>{order.asset_sku}</small>
                </th>
                <td className="quantity-cell" data-label="Cantidad">
                  {inbound ? "+" : "−"}
                  {order.quantity}
                </td>
                <td data-label="Oficina">{order.office}</td>
                <td data-label="Fecha">{formatDate(order.created_at)}</td>
                <td data-label="Registrado por">
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
  );
}
