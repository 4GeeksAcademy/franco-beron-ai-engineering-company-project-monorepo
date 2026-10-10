import Head from "next/head";
import { useEffect } from "react";

export default function Home() {
  useEffect(() => {
    import("../main.js");
  }, []);

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
      <div className="layout" id="app" />
    </>
  );
}
