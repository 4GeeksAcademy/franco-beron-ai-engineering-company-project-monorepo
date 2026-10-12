import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useState } from "react";

import { resetPassword } from "../lib/auth";

function icon(name) {
  return <i data-lucide={name} aria-hidden="true" />;
}

export default function ResetPasswordPage() {
  const router = useRouter();

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  /* Read the token from the URL query string once the router is ready. */
  const ready = router.isReady;
  const token =
    typeof router.query.token === "string" ? router.query.token : "";
  const invalidLink = ready && !token;

  async function handleSubmit(event) {
    event.preventDefault();
    setFieldError("");
    setError("");
    setLoading(true);

    if (password !== confirmPassword) {
      setFieldError("Las contraseñas no coinciden.");
      setLoading(false);
      return;
    }

    try {
      await resetPassword({ token, new_password: password });
      void router.replace({
        pathname: "/login",
        query: { reset: "success" },
      });
    } catch (requestError) {
      setError(
        requestError.message ||
          "El enlace de recuperación no es válido o ha expirado.",
      );
      setPassword("");
      setConfirmPassword("");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Head>
        <title>Nueva contraseña | Nexova Backoffice</title>
        <meta
          name="description"
          content="Establece una nueva contraseña para tu cuenta."
        />
        <meta name="theme-color" content="#17201f" />
      </Head>

      <main className="auth-shell">
        <div className="auth-panel">
          <div className="auth-brand">
            <span className="brand-mark">N</span>
            <span>Nexova Ops</span>
          </div>
          <p className="kicker">Seguridad de cuenta</p>
          <h1>Nueva contraseña</h1>
          <p className="auth-copy">
            Usa al menos 8 caracteres para proteger tu cuenta.
          </p>

          {invalidLink ? (
            <>
              <div className="auth-links" role="alert">
                <p className="form-message error-message">
                  El enlace de recuperación no es válido o ha expirado. Solicita
                  uno nuevo.
                </p>
              </div>
              <Link className="text-button back-link" href="/forgot-password">
                {icon("arrow-left")}
                <span>Solicitar un nuevo enlace</span>
              </Link>
            </>
          ) : !error && ready ? (
            <form className="form-stack" onSubmit={handleSubmit}>
              <label htmlFor="reset-password">Contraseña nueva</label>
              <div className="input-shell">
                {icon("lock-keyhole")}
                <input
                  id="reset-password"
                  name="new_password"
                  type="password"
                  minLength={8}
                  maxLength={72}
                  autoComplete="new-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <label htmlFor="reset-confirm">Repetir contraseña</label>
              <div className="input-shell">
                {icon("shield-check")}
                <input
                  id="reset-confirm"
                  name="confirm_password"
                  type="password"
                  minLength={8}
                  maxLength={72}
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
              {fieldError && <p className="field-error">{fieldError}</p>}

              <button
                className="primary-button"
                type="submit"
                disabled={loading}
              >
                {icon("key-round")}
                <span>
                  {loading ? "Actualizando…" : "Actualizar contraseña"}
                </span>
              </button>
            </form>
          ) : !invalidLink && error ? (
            <>
              <div className="auth-links" role="alert">
                <p className="form-message error-message">{error}</p>
              </div>
              <Link className="text-button back-link" href="/forgot-password">
                {icon("arrow-left")}
                <span>Solicitar un nuevo enlace</span>
              </Link>
            </>
          ) : null}
        </div>
      </main>
    </>
  );
}
