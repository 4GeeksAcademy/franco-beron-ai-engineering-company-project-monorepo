import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useState } from "react";

import { login, register, setToken } from "../lib/auth";
import Icon from "../components/Icon";

export default function RegisterPage() {
  const router = useRouter();

  const [form, setForm] = useState({
    email: "",
    password: "",
    confirmPassword: "",
    name: "",
    phone: "",
    address: "",
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [globalError, setGlobalError] = useState("");
  const [loading, setLoading] = useState(false);

  function setField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => ({ ...prev, [field]: "" }));
    setGlobalError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFieldErrors({});
    setGlobalError("");
    setLoading(true);

    /* Client-side validation. */
    const errors = {};
    if (form.password !== form.confirmPassword) {
      errors.confirmPassword = "Las contraseñas no coinciden.";
    }
    if (form.password.length < 8) {
      errors.password = "La contraseña debe tener al menos 8 caracteres.";
    }
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setLoading(false);
      return;
    }

    try {
      /* 1. Register user */
      await register({
        email: form.email,
        password: form.password,
        name: form.name || undefined,
        phone: form.phone || undefined,
        address: form.address || undefined,
      });

      /* 2. Login with same credentials */
      const data = await login(form.email, form.password);
      setToken(data.access_token);

      /* 3. Redirect to incidents */
      void router.replace("/backoffice/incidents");
    } catch (requestError) {
      setGlobalError(requestError.message || "Error al registrarse.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Head>
        <title>Crear cuenta | Nexova Backoffice</title>
        <meta
          name="description"
          content="Regístrate para acceder al panel interno de Nexova."
        />
        <meta name="theme-color" content="#17201f" />
      </Head>

      <main className="auth-shell">
        <div className="auth-panel auth-panel--wide">
          <div className="auth-brand">
            <span className="brand-mark">N</span>
            <span>Nexova Ops</span>
          </div>
          <p className="kicker">Centro de operaciones</p>
          <h1>Crear cuenta</h1>
          <p className="auth-copy">
            Regístrate para acceder al panel de soporte.
          </p>

          <form className="form-stack" onSubmit={handleSubmit}>
            <label htmlFor="reg-email">Correo electrónico *</label>
            <div className="input-shell">
              <Icon name="mail" />
              <input
                id="reg-email"
                name="email"
                type="email"
                autoComplete="username"
                required
                value={form.email}
                onChange={(e) => setField("email", e.target.value)}
              />
            </div>
            {fieldErrors.email && (
              <p className="field-error">{fieldErrors.email}</p>
            )}

            <label htmlFor="reg-password">Contraseña *</label>
            <div className="input-shell">
              <Icon name="lock-keyhole" />
              <input
                id="reg-password"
                name="password"
                type="password"
                autoComplete="new-password"
                minLength={8}
                required
                value={form.password}
                onChange={(e) => setField("password", e.target.value)}
              />
            </div>
            {fieldErrors.password && (
              <p className="field-error">{fieldErrors.password}</p>
            )}

            <label htmlFor="reg-confirm">Confirmar contraseña *</label>
            <div className="input-shell">
              <Icon name="shield-check" />
              <input
                id="reg-confirm"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                minLength={8}
                required
                value={form.confirmPassword}
                onChange={(e) => setField("confirmPassword", e.target.value)}
              />
            </div>
            {fieldErrors.confirmPassword && (
              <p className="field-error">{fieldErrors.confirmPassword}</p>
            )}

            <fieldset className="form-fieldset">
              <legend>Datos de perfil (opcional)</legend>

              <label htmlFor="reg-name">Nombre</label>
              <div className="input-shell">
                <Icon name="user" />
                <input
                  id="reg-name"
                  name="name"
                  type="text"
                  autoComplete="name"
                  maxLength={160}
                  value={form.name}
                  onChange={(e) => setField("name", e.target.value)}
                />
              </div>

              <label htmlFor="reg-phone">Teléfono</label>
              <div className="input-shell">
                <Icon name="phone" />
                <input
                  id="reg-phone"
                  name="phone"
                  type="tel"
                  autoComplete="tel"
                  maxLength={80}
                  value={form.phone}
                  onChange={(e) => setField("phone", e.target.value)}
                />
              </div>

              <label htmlFor="reg-address">Dirección</label>
              <div className="input-shell">
                <Icon name="map-pin" />
                <input
                  id="reg-address"
                  name="address"
                  type="text"
                  autoComplete="street-address"
                  maxLength={300}
                  value={form.address}
                  onChange={(e) => setField("address", e.target.value)}
                />
              </div>
            </fieldset>

            <button className="primary-button" type="submit" disabled={loading}>
              <Icon name="user-plus" />
              <span>{loading ? "Registrando…" : "Crear cuenta"}</span>
            </button>
          </form>

          <div className="auth-links">
            <Link className="text-button" href="/login">
              <Icon name="arrow-left" />
              <span>Ya tengo cuenta</span>
            </Link>
          </div>

          {globalError && (
            <p className="form-message error-message" role="status">
              {globalError}
            </p>
          )}
        </div>
      </main>
    </>
  );
}
