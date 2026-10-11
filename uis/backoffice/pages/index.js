import Head from "next/head";
import { useRouter } from "next/router";
import { useEffect } from "react";

import { isAuthenticated } from "../lib/auth";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    if (router.isReady) {
      if (isAuthenticated()) {
        void router.replace("/backoffice/incidents");
      } else {
        void router.replace("/login");
      }
    }
  }, [router]);

  return (
    <>
      <Head>
        <title>Nexova Backoffice | Operaciones de Soporte</title>
        <meta
          name="description"
          content="Backoffice interno de Nexova para seguimiento de soporte y calidad operativa."
        />
        <meta name="theme-color" content="#17201f" />
      </Head>
      <main className="inventory-auth-state" role="status">
        <span className="inventory-spinner" aria-hidden="true" />
        <p>Redirigiendo…</p>
      </main>
    </>
  );
}
