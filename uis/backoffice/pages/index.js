import Head from "next/head";
import Script from "next/script";
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
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Archivo:wght@600;700&display=swap"
          rel="stylesheet"
        />
      </Head>
      <Script
        src="https://unpkg.com/lucide@0.468.0/dist/umd/lucide.min.js"
        strategy="afterInteractive"
        onLoad={() =>
          window.lucide?.createIcons({ attrs: { "stroke-width": 1.8 } })
        }
      />
      <div className="layout" id="app" />
    </>
  );
}
