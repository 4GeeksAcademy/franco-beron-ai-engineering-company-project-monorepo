import Head from "next/head";
import { useRouter } from "next/router";
import { useState } from "react";

import InventoryShell from "../../components/InventoryShell";
import { changePassword, clearToken } from "../../lib/auth";
import Icon from "../../components/Icon";

export default function ChangePasswordPage() {
  const router = useRouter();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saveSuccess, setSaveSuccess] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setFieldError("");
    setSaveError("");
    setSaveSuccess("");
    setSaving(true);

    /* Client-side validation: new password and confirmation must match. */
    if (newPassword !== confirmPassword) {
      setFieldError("Las contraseñas no coinciden.");
      setSaving(false);
      return;
    }

    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      /* Invalidate the current session: old token is no longer valid. */
      clearToken();
      void router.replace("/login?changed=success");
    } catch (requestError) {
      setSaveError(requestError.message || "No se pudo cambiar la contraseña.");
      setSaveSuccess("");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Head>
        <title>Cambiar contraseña | Nexova Backoffice</title>
        <meta
          name="description"
          content="Actualiza la contraseña de tu cuenta."
        />
        <meta name="theme-color" content="#17201f" />
      </Head>

      <InventoryShell
        active="profile"
        title="Cambiar contraseña"
        eyebrow="Cuenta"
        description="Actualiza la contraseña de acceso a tu cuenta interna."
      >
        <div className="profile-page">
          <section className="profile-section">
            <h2>Seguridad de cuenta</h2>
            <p className="profile-email">
              Introduce tu contraseña actual y elige una nueva.
            </p>

            <form className="form-stack profile-form" onSubmit={handleSubmit}>
              <label htmlFor="current-password">Contraseña actual</label>
              <div className="input-shell">
                <Icon name="lock-keyhole" />
                <input
                  id="current-password"
                  name="current_password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={currentPassword}
                  onChange={(e) => {
                    setCurrentPassword(e.target.value);
                    setSaveSuccess("");
                    setSaveError("");
                  }}
                />
              </div>

              <label htmlFor="new-password">Contraseña nueva</label>
              <div className="input-shell">
                <Icon name="key-round" />
                <input
                  id="new-password"
                  name="new_password"
                  type="password"
                  minLength={8}
                  maxLength={72}
                  autoComplete="new-password"
                  required
                  value={newPassword}
                  onChange={(e) => {
                    setNewPassword(e.target.value);
                    setSaveSuccess("");
                    setSaveError("");
                  }}
                />
              </div>

              <label htmlFor="confirm-password">Repetir contraseña nueva</label>
              <div className="input-shell">
                <Icon name="shield-check" />
                <input
                  id="confirm-password"
                  name="confirm_password"
                  type="password"
                  minLength={8}
                  maxLength={72}
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    setSaveSuccess("");
                    setSaveError("");
                  }}
                />
              </div>

              {fieldError && <p className="field-error">{fieldError}</p>}

              <div className="profile-actions">
                <button
                  className="primary-button"
                  type="submit"
                  disabled={saving}
                >
                  <Icon name="save" />
                  <span>
                    {saving ? "Actualizando…" : "Actualizar contraseña"}
                  </span>
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
      </InventoryShell>
    </>
  );
}
