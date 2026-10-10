import Head from "next/head";
import Script from "next/script";

import "../styles.css";

export default function App({ Component, pageProps }) {
  return (
    <>
      <Head>
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
      <Component {...pageProps} />
    </>
  );
}
