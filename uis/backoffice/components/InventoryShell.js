import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";

import {
  clearToken,
  getCurrentUser,
  getToken,
  redirectToLogin,
} from "../lib/auth";

const navigation = [
  {
    href: "/backoffice/incidents",
    label: "Incidencias",
    icon: "alert-triangle",
    id: "incidents",
  },
  {
    href: "/backoffice/suppliers",
    label: "Proveedores",
    icon: "building-2",
    id: "suppliers",
  },
  {
    href: "/backoffice/inventory/products",
    label: "Activos",
    icon: "boxes",
    id: "products",
  },
  {
    href: "/backoffice/inventory/orders/inbound",
    label: "Registrar entrada",
    icon: "package-plus",
    id: "inbound",
  },
  {
    href: "/backoffice/inventory/orders/outbound",
    label: "Registrar salida",
    icon: "package-minus",
    id: "outbound",
  },
  {
    href: "/backoffice/inventory/orders",
    label: "Historial",
    icon: "history",
    id: "orders",
  },
  {
    href: "/account/profile",
    label: "Mi perfil",
    icon: "user-circle",
    id: "profile",
  },
];

function icon(name) {
  return <i data-lucide={name} aria-hidden="true" />;
}

export default function InventoryShell({
  active,
  title,
  description,
  eyebrow = "Operaciones · Inventario",
  children,
}) {
  const router = useRouter();
  const [auth, setAuth] = useState({
    status: "checking",
    user: null,
    error: "",
  });
  const [retry, setRetry] = useState(0);
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    if (!router.isReady) return undefined;

    let activeEffect = true;
    const returnTo = `${window.location.pathname}${window.location.search}`;
    const token = getToken();

    if (!token) {
      redirectToLogin(returnTo);
      return () => {
        activeEffect = false;
      };
    }

    setAuth({ status: "checking", user: null, error: "" });

    getCurrentUser(token)
      .then((user) => {
        if (activeEffect) setAuth({ status: "ready", user, error: "" });
      })
      .catch((error) => {
        if (!activeEffect) return;
        if (error.status === 401) {
          redirectToLogin(returnTo);
          return;
        }
        setAuth({
          status: "error",
          user: null,
          error: error.message || "No se pudo verificar la sesión.",
        });
      });

    return () => {
      activeEffect = false;
    };
  }, [router, retry]);

  useEffect(() => {
    window.lucide?.createIcons({ attrs: { "stroke-width": 1.8 } });
  }, [auth.status, active, children, navOpen]);

  // Close the mobile drawer on route change and lock scroll while open.
  useEffect(() => {
    setNavOpen(false);
  }, [router.asPath]);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("nav-open", navOpen);
    if (navOpen) {
      const previousOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        root.classList.remove("nav-open");
        document.body.style.overflow = previousOverflow;
      };
    }
    return () => root.classList.remove("nav-open");
  }, [navOpen]);

  function logout() {
    clearToken();
    redirectToLogin();
  }

  if (auth.status === "checking") {
    return (
      <main className="inventory-auth-state" aria-live="polite">
        <span className="inventory-spinner" aria-hidden="true" />
        <p>Verificando acceso...</p>
      </main>
    );
  }

  if (auth.status === "error") {
    return (
      <main className="inventory-auth-state" role="alert">
        <p>{auth.error}</p>
        <button
          className="secondary-button"
          type="button"
          onClick={() => setRetry((value) => value + 1)}
        >
          {icon("refresh-cw")} Reintentar
        </button>
      </main>
    );
  }

  return (
    <>
      <Head>
        <title>{title} | Nexova Inventario</title>
        <meta
          name="description"
          content="Gestión interna de activos, entradas y salidas de Nexova."
        />
      </Head>
      <div className="layout inventory-layout">
        <aside className="sidebar">
          <div className="sidebar-topbar">
            <Link className="brand-lockup inventory-brand" href="/">
              <span className="brand-mark">N</span>
              <span className="brand-name">
                <strong>Nexova</strong>
                <span>Inventario</span>
              </span>
            </Link>
            <button
              className="nav-toggle"
              type="button"
              onClick={() => setNavOpen((value) => !value)}
              aria-expanded={navOpen}
              aria-controls="inventory-nav"
              aria-label={navOpen ? "Cerrar menú" : "Abrir menú"}
            >
              <i data-lucide={navOpen ? "x" : "menu"} aria-hidden="true" />
            </button>
          </div>
          <div className="sidebar-drawer">
            <nav id="inventory-nav" aria-label="Navegación de inventario">
              {navigation.map((item) => (
                <Link
                  className={`nav-link ${active === item.id ? "active" : ""}`}
                  href={item.href}
                  key={item.id}
                  aria-current={active === item.id ? "page" : undefined}
                  title={item.label}
                >
                  {icon(item.icon)}
                  <span>{item.label}</span>
                </Link>
              ))}
            </nav>
            <div className="sidebar-footer inventory-sidebar-footer">
              <div className="sidebar-user">
                <span className="avatar">
                  {(auth.user?.name || auth.user?.email || "N")
                    .slice(0, 1)
                    .toUpperCase()}
                </span>
                <div>
                  <strong>{auth.user?.name || "Usuario interno"}</strong>
                  <span>{auth.user?.email || ""}</span>
                </div>
              </div>
              <button className="sidebar-logout" type="button" onClick={logout}>
                {icon("log-out")}
                <span>Cerrar sesión</span>
              </button>
            </div>
          </div>
          {navOpen && (
            <button
              className="nav-backdrop"
              type="button"
              aria-label="Cerrar menú"
              onClick={() => setNavOpen(false)}
            />
          )}
        </aside>

        <main className="content inventory-content">
          <header className="content-header inventory-header">
            <div>
              <p className="kicker">{eyebrow}</p>
              <h1>{title}</h1>
              <p className="header-copy">{description}</p>
            </div>
            <div className="user-controls">
              <span className="system-status">
                <span aria-hidden="true" />
                Sesión activa
              </span>
              <Link className="secondary-button" href="/">
                {icon("layout-dashboard")}
                <span>Panel de soporte</span>
              </Link>
            </div>
          </header>
          <section className="inventory-page-content">{children}</section>
        </main>
      </div>
    </>
  );
}
