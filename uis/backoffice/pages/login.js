import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";

import { login, setToken, isAuthenticated } from "../lib/auth";
import Icon from "../components/Icon";

function icon(name) {
  return <i data-lucide={name} aria-hidden="true" />;
}

export default function LoginPage() {
  const router = useRouter();
  const { next, reset, changed } = router.query;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);

  /* Show success messages passed by /reset-password or /account/change-password. */
  useEffect(() => {
    if (!router.isReady) return;
    if (typeof reset === "string" && reset === "success") {
      setNotice(
        "Contraseña actualizada. Inicia sesión con tu nueva contraseña.",
      );
    } else if (typeof changed === "string" && changed === "success") {
      setNotice("Contraseña actualizada. Inicia sesión nuevamente.");
    }
  }, [router.isReady, reset, changed]);

  /* If already authenticated, redirect immediately. */
  useEffect(() => {
    if (router.isReady && isAuthenticated()) {
      const destination =
        typeof next === "string" && next ? next : "/backoffice/incidents";
      void router.replace(destination);
    }
  }, [router, next]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    setLoading(true);

    try {
      const data = await login(email, password);
      setToken(data.access_token);
      const destination =
        typeof next === "string" && next ? next : "/backoffice/incidents";
      void router.replace(destination);
    } catch (requestError) {
      setError(requestError.message || "Error al iniciar sesión.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Head>
        <title>Iniciar sesión | Nexova Backoffice</title>
        <meta name="description" content="Accede al panel interno de Nexova." />
        <meta name="theme-color" content="#17201f" />
      </Head>

      <main className="auth-shell">
        <div className="auth-panel">
          <div className="auth-brand">
            <span className="brand-mark">N</span>
            <span>Nexova Ops</span>
          </div>
          <p className="kicker">Centro de operaciones</p>
          <h1>Bienvenido de nuevo</h1>
          <p className="auth-copy">Accede al espacio interno de soporte.</p>

          <form className="form-stack" onSubmit={handleSubmit}>
            <label htmlFor="login-email">Correo interno</label>
            <div className="input-shell">
              <Icon name="mail" />
              <input
                id="login-email"
                name="email"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <label htmlFor="login-password">Contraseña</label>
            <div className="input-shell">
              <Icon name="lock-keyhole" />
              <input
                id="login-password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button className="primary-button" type="submit" disabled={loading}>
              <Icon name="log-in" />
              <span>{loading ? "Iniciando sesión…" : "Iniciar sesión"}</span>
            </button>
          </form>

          <div className="auth-links">
            <Link className="text-button" href="/forgot-password">
              <Icon name="key-round" />
              <span>¿Olvidaste tu contraseña?</span>
            </Link>
            <Link className="text-button" href="/register">
              <Icon name="user-plus" />
              <span>Crear cuenta</span>
            </Link>
          </div>

          {notice ? (
            <p className="form-message success-message" role="status">
              {notice}
            </p>
          ) : (
            error && (
              <p className="form-message error-message" role="status">
                {error}
              </p>
            )
          )}
        </div>
      </main>
    </>
  );
}
