import Head from "next/head";
import { useEffect } from "react";

export default function Home() {
  useEffect(() => {
    import("../main.js");
  }, []);

  return (
    <>
      <Head>
        <title>Nexova | Outsourcing de Soporte y RR. HH.</title>
        <meta
          name="description"
          content="Nexova ayuda a empresas de tecnologia, retail y finanzas con outsourcing de soporte al cliente y consultoria de RR. HH."
        />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&family=Space+Grotesk:wght@500;700&display=swap"
          rel="stylesheet"
        />
      </Head>
      <div className="bg-shape bg-shape-one" aria-hidden="true" />
      <div className="bg-shape bg-shape-two" aria-hidden="true" />
      <div id="app" />
    </>
  );
}
