import Head from "next/head";
import Link from "next/link";
import { useState } from "react";

import { forgotPassword } from "../lib/auth";
import Icon from "../components/Icon";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await forgotPassword(email);
      setSubmitted(true);
    } catch (requestError) {
      setError(requestError.message || "No se pudo solicitar la recuperación.");
      /* Keep the form enabled so the user can retry. */
      setSubmitted(false);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Head>
        <title>Recuperar acceso | Nexova Backoffice</title>
        <meta
          name="description"
          content="Solicita un enlace para restablecer tu contraseña."
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
          <h1>Recuperar acceso</h1>
          <p className="auth-copy">
            Introduce tu correo interno para solicitar un enlace de
            recuperación.
          </p>

          <form className="form-stack" onSubmit={handleSubmit}>
            <label htmlFor="forgot-email">Correo interno</label>
            <div className="input-shell">
              <Icon name="mail" />
              <input
                id="forgot-email"
                name="email"
                type="email"
                autoComplete="username"
                required
                disabled={submitted}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <button
              className="primary-button"
              type="submit"
              disabled={loading || submitted}
            >
              <Icon name="send" />
              <span>
                {loading
                  ? "Enviando…"
                  : submitted
                    ? "Enlace enviado"
                    : "Enviar enlace"}
              </span>
            </button>
          </form>

          <Link className="text-button back-link" href="/login">
            <Icon name="arrow-left" />
            <span>Volver al acceso</span>
          </Link>

          {submitted ? (
            <p className="form-message success-message" role="status">
              Si esa dirección está registrada, recibirás un enlace en breve.
            </p>
          ) : (
            error && (
              <p className="form-message error-message" role="alert">
                {error}
              </p>
            )
          )}
        </div>
      </main>
    </>
  );
}
