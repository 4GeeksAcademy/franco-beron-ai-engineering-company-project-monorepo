export function apiErrorMessage(status) {
  if (status === 401) return "La sesión terminó. Inicia sesión nuevamente.";
  if (status === 403)
    return "No tienes permiso para esta operación. Contacta con tu administrador.";
  if (status === 404)
    return "El registro ya no está disponible. Actualiza la página.";
  if (status === 400 || status === 422)
    return "Revisa los datos del formulario e inténtalo de nuevo.";
  return "No se pudo completar la solicitud. Inténtalo de nuevo en unos momentos.";
}

export async function readApiResponse(response) {
  if (!response.ok) throw new Error(apiErrorMessage(response.status));
  if (response.status === 204) return null;
  try {
    const payload = await response.json();
    if (payload === null || typeof payload !== "object") throw new Error();
    if (
      Array.isArray(payload) &&
      payload.some((item) => !item || typeof item !== "object")
    )
      throw new Error();
    return payload;
  } catch {
    throw new Error(
      "El servicio devolvió una respuesta inválida. Inténtalo de nuevo.",
    );
  }
}
