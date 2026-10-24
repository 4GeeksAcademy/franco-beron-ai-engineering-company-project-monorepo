import Head from "next/head";
import { useEffect, useState } from "react";

import InventoryShell from "../../components/InventoryShell";
import { getCurrentUser, updateProfile } from "../../lib/auth";
import Icon from "../../components/Icon";

export default function ProfilePage() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  /* Editable fields */
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState("");

  useEffect(() => {
    getCurrentUser()
      .then((data) => {
        setUser(data);
        setName(data.profile?.name || "");
        setPhone(data.profile?.phone || "");
        setAddress(data.profile?.address || "");
        setLoading(false);
      })
      .catch((requestError) => {
        setError(requestError.message || "No se pudo cargar el perfil.");
        setLoading(false);
      });
  }, []);

  async function handleSave(event) {
    event.preventDefault();
    setSaveError("");
    setSaveSuccess("");
    setSaving(true);

    try {
      const updated = await updateProfile({ name, phone, address });
      setUser((prev) => ({
        ...prev,
        profile: updated,
      }));
      setName(updated.name || "");
      setPhone(updated.phone || "");
      setAddress(updated.address || "");
      setSaveSuccess("Perfil actualizado correctamente.");
    } catch (requestError) {
      setSaveError(requestError.message || "No se pudo actualizar el perfil.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Head>
        <title>Mi perfil | Nexova Backoffice</title>
        <meta name="description" content="Gestiona tu perfil de usuario." />
        <meta name="theme-color" content="#17201f" />
      </Head>

      <InventoryShell
        active="profile"
        title="Mi perfil"
        eyebrow="Cuenta"
        description="Consulta y actualiza tus datos personales."
      >
        {loading && (
          <div className="inventory-auth-state" role="status">
            <span className="inventory-spinner" aria-hidden="true" />
            <p>Cargando perfil…</p>
          </div>
        )}

        {!loading && error && (
          <div className="inventory-auth-state" role="alert">
            <p>{error}</p>
          </div>
        )}

        {!loading && !error && user && (
          <div className="profile-page">
            <section className="profile-section">
              <h2>Correo electrónico</h2>
              <p className="profile-email">{user.email}</p>
            </section>

            <section className="profile-section">
              <h2>Datos de contacto</h2>

              <form className="form-stack profile-form" onSubmit={handleSave}>
                <label htmlFor="profile-name">Nombre</label>
                <div className="input-shell">
                  <Icon name="user" />
                  <input
                    id="profile-name"
                    name="name"
                    type="text"
                    autoComplete="name"
                    maxLength={160}
                    value={name}
                    onChange={(e) => {
                      setName(e.target.value);
                      setSaveSuccess("");
                      setSaveError("");
                    }}
                  />
                </div>

                <label htmlFor="profile-phone">Teléfono</label>
                <div className="input-shell">
                  <Icon name="phone" />
                  <input
                    id="profile-phone"
                    name="phone"
                    type="tel"
                    autoComplete="tel"
                    maxLength={80}
                    value={phone}
                    onChange={(e) => {
                      setPhone(e.target.value);
                      setSaveSuccess("");
                      setSaveError("");
                    }}
                  />
                </div>

                <label htmlFor="profile-address">Dirección</label>
                <div className="input-shell">
                  <Icon name="map-pin" />
                  <input
                    id="profile-address"
                    name="address"
                    type="text"
                    autoComplete="street-address"
                    maxLength={300}
                    value={address}
                    onChange={(e) => {
                      setAddress(e.target.value);
                      setSaveSuccess("");
                      setSaveError("");
                    }}
                  />
                </div>

                <div className="profile-actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => {
                      setName(user.profile?.name || "");
                      setPhone(user.profile?.phone || "");
                      setAddress(user.profile?.address || "");
                      setSaveSuccess("");
                      setSaveError("");
                    }}
                  >
                    <Icon name="rotate-ccw" />
                    <span>Restaurar</span>
                  </button>
                  <button
                    className="primary-button"
                    type="submit"
                    disabled={saving}
                  >
                    <Icon name="save" />
                    <span>{saving ? "Guardando…" : "Guardar cambios"}</span>
                  </button>
                </div>
              </form>

              {saveSuccess && (
                <p className="form-message success-message" role="status">
                  {saveSuccess}
                </p>
              )}
              {saveError && (
                <p className="form-message error-message" role="status">
                  {saveError}
                </p>
              )}
            </section>
          </div>
        )}
      </InventoryShell>
    </>
  );
}
