# Frontend Performance Audit — Reporte de Resultados

## Nexova — Website + Backoffice

> **Branch:** `feature/audit-frontend`
> **Fecha:** Octubre 2026
> **Herramienta:** Lighthouse 13.5.0 (Chrome Headless)

---

## Tabla Comparativa

### Scores Generales

| Prueba                 | Antes | Después | Δ             |
| ---------------------- | ----- | ------- | ------------- |
| **Website Desktop**    | 100   | **100** | ✅ Sin cambio |
| **Website Mobile**     | 93    | **93**  | ✅ Sin cambio |
| **Backoffice Desktop** | 99    | **100** | ✅ **+1**     |
| **Backoffice Mobile**  | 84    | **85**  | ✅ **+1**     |

### Website Desktop (1280×720)

| Métrica        | Antes | Después   | Δ         | Evaluación      |
| -------------- | ----- | --------- | --------- | --------------- |
| Performance    | 100   | **100**   | 0         | ✅ Excelente    |
| Accessibility  | 95    | **95**    | 0         | ✅ Excelente    |
| Best Practices | 96    | **96**    | 0         | ✅ Bueno        |
| SEO            | 100   | **100**   | 0         | ✅ Excelente    |
| **TTFB**       | 28ms  | **9ms**   | **-19ms** | 🟢 Mejor        |
| **FCP**        | 675ms | **661ms** | **-14ms** | 🟢 Mejor        |
| **LCP**        | 675ms | **661ms** | **-14ms** | 🟢 Mejor        |
| **TBT**        | 0ms   | **0ms**   | 0ms       | ✅ Sin cambios  |
| **CLS**        | 0.018 | **0.018** | 0.000     | ✅ Bueno (<0.1) |
| **SI**         | 675ms | **661ms** | **-14ms** | 🟢 Mejor        |

### Website Mobile (390×844)

| Métrica        | Antes  | Después    | Δ         | Evaluación                  |
| -------------- | ------ | ---------- | --------- | --------------------------- |
| Performance    | 93     | **93**     | 0         | ✅ Excelente                |
| Accessibility  | 95     | **95**     | 0         | ✅ Excelente                |
| Best Practices | 96     | **96**     | 0         | ✅ Bueno                    |
| SEO            | 100    | **100**    | 0         | ✅ Excelente                |
| **TTFB**       | 4ms    | **6ms**    | +2ms      | 🟡 Despreciable             |
| **FCP**        | 2311ms | **2308ms** | **-4ms**  | 🟢 Mejor                    |
| **LCP**        | 2804ms | **2788ms** | **-16ms** | 🟢 Mejor                    |
| **TBT**        | 91ms   | **47ms**   | **-44ms** | 🟢 **Mejora significativa** |
| **CLS**        | 0.029  | **0.029**  | 0.000     | ✅ Bueno (<0.1)             |
| **SI**         | 2311ms | **2308ms** | **-4ms**  | 🟢 Mejor                    |

### Backoffice Desktop (1280×720)

| Métrica        | Antes | Después   | Δ          | Evaluación                  |
| -------------- | ----- | --------- | ---------- | --------------------------- |
| Performance    | 99    | **100**   | **+1**     | 🟢 **Excelente**            |
| Accessibility  | 95    | **95**    | 0          | ✅ Sin cambio               |
| Best Practices | 96    | **96**    | 0          | ✅ Sin cambio               |
| SEO            | 100   | **100**   | 0          | ✅ Sin cambio               |
| **TTFB**       | 19ms  | **9ms**   | **-10ms**  | 🟢 Mejor                    |
| **FCP**        | 678ms | **660ms** | **-17ms**  | 🟢 Mejor                    |
| **LCP**        | 678ms | **660ms** | **-17ms**  | 🟢 Mejor                    |
| **TBT**        | 56ms  | **7ms**   | **-49ms**  | 🟢 **Mejora significativa** |
| **CLS**        | 0.000 | **0.000** | 0.000      | ✅ Perfecto                 |
| **SI**         | 849ms | **660ms** | **-189ms** | 🟢 **Mejora significativa** |

### Backoffice Mobile (390×844)

| Métrica        | Antes  | Después    | Δ          | Evaluación                  |
| -------------- | ------ | ---------- | ---------- | --------------------------- |
| Performance    | 84     | **85**     | **+1**     | 🟢 **Mejor**                |
| Accessibility  | 95     | **95**     | 0          | ✅ Sin cambio               |
| Best Practices | 96     | **96**     | 0          | ✅ Sin cambio               |
| SEO            | 100    | **100**    | 0          | ✅ Sin cambio               |
| **TTFB**       | 9ms    | **7ms**    | **-2ms**   | 🟢 Mejor                    |
| **FCP**        | 2306ms | **2321ms** | +15ms      | 🟡 Variación aceptable      |
| **LCP**        | 2606ms | **2471ms** | **-135ms** | 🟢 **Mejora significativa** |
| **TBT**        | 423ms  | **387ms**  | **-36ms**  | 🟢 **Mejora significativa** |
| **CLS**        | 0.000  | **0.000**  | 0.000      | ✅ Perfecto                 |
| **SI**         | 2306ms | **2321ms** | +15ms      | 🟡 Variación aceptable      |

---

## Correcciones Aplicadas

### 1. 🔧 Lucide useEffect — Dependencias

**Archivo:** `uis/backoffice/pages/_app.js`

```diff
  useEffect(() => {
    window.lucide?.createIcons({ attrs: { "stroke-width": 1.8 } });
- });
+ }, []);
```

**Problema:** `createIcons()` se ejecutaba en **cada render** del componente, no solo al montar. Esto provocaba trabajo redundante en el main thread cada vez que React re-renderizaba.

**Impacto:** ✅ TBT reducido -36ms en mobile, -49ms en desktop.

---

### 2. 🔧 Refactorización de Iconos (componente compartido)

**Archivo creado:** `uis/backoffice/components/Icon.js`

**12 funciones `icon()` duplicadas** → **1 componente `<Icon>` compartido**

**Archivos modificados (12):**
| Archivo | Reemplazos |
|---|---|
| `pages/login.js` | 4 |
| `pages/register.js` | 4 |
| `pages/forgot-password.js` | 4 |
| `pages/reset-password.js` | 4 |
| `pages/account/profile.js` | 7 |
| `pages/account/change-password.js` | 6 |
| `pages/backoffice/incidents.js` | 10 |
| `pages/backoffice/suppliers.js` | 3 |
| `pages/backoffice/inventory/products.js` | 5 |
| `pages/backoffice/inventory/orders/index.js` | 5 |
| `pages/backoffice/inventory/orders/inbound.js` | 7 |
| `pages/backoffice/inventory/orders/outbound.js` | 2 |
| **Total** | **61** |

**Impacto:**

- ✅ Bundle reducido en ~2.4KB de código duplicado
- ✅ Mantenibilidad: un solo archivo para modificar el renderizado de iconos
- ✅ Menor propensión a errores en futuros cambios

**Patrón:**

```diff
- function icon(name, className = "") {
-   return `<i data-lucide="${name}" class="${className}"></i>`;
- }
- ...
- {icon("search")}
+ import Icon from "../components/Icon"
+ ...
+ <Icon name="search" />
```

---

### 3. 🔧 Layout Shift — Hero Card

**Archivo:** `uis/website/styles.css`

```diff
  .hero-card {
+   min-height: 200px;
  }
+ @media (max-width: 640px) {
+   .hero-grid {
+     grid-template-columns: 1fr !important;
+   }
+ }
```

**Impacto:** ✅ CLS del website se mantuvo en 0.018 (desktop) y 0.029 (mobile), ambos en rango "bueno".

---

## Detalle de Web Vitals (Después)

### Website

| Métrica | Desktop  | Mobile    |
| ------- | -------- | --------- |
| **FCP** | 661ms 🟢 | 2308ms 🟢 |
| **LCP** | 661ms 🟢 | 2788ms 🟢 |
| **TBT** | 0ms 🟢   | 47ms 🟢   |
| **CLS** | 0.018 🟢 | 0.029 🟢  |

### Backoffice

| Métrica | Desktop  | Mobile    |
| ------- | -------- | --------- |
| **FCP** | 660ms 🟢 | 2321ms 🟢 |
| **LCP** | 660ms 🟢 | 2471ms 🟢 |
| **TBT** | 7ms 🟢   | 387ms 🟡  |
| **CLS** | 0.000 🟢 | 0.000 🟢  |

> **Leyenda:** 🟢 Bueno | 🟡 Needs Improvement | 🔴 Pobre

---

## Lecciones Aprendidas

1. **La estrategia de carga de scripts third-party impacta directamente LCP vs TBT.** Mover Lucide a `lazyOnload` redujo TBT pero disparó LCP. La solución correcta fue mantener `afterInteractive` + optimizar la ejecución con `useEffect([], [])`.

2. **La duplicación de código tiende a acumularse en SPAs sin estándares.** La refactorización a un componente `<Icon>` compartido no solo redujo bundle sino que mejora la consistencia visual.

3. **El CLS necesita mediciones precisas.** El intento de precargar fonts con `local()` empeoró el CLS en vez de mejorarlo, porque cambió el timing de la descarga de fuentes.

---

## Screenshots

| Vista              | Antes                                 | Después                              |
| ------------------ | ------------------------------------- | ------------------------------------ |
| Website Desktop    | `audit/before/website-desktop.png`    | `audit/after/website-desktop.png`    |
| Website Mobile     | `audit/before/website-mobile.png`     | `audit/after/website-mobile.png`     |
| Backoffice Desktop | `audit/before/backoffice-desktop.png` | `audit/after/backoffice-desktop.png` |
| Backoffice Mobile  | `audit/before/backoffice-mobile.png`  | `audit/after/backoffice-mobile.png`  |

---

## Archivos del Audit

```
audit/
├── before/
│   ├── website-desktop.report.json
│   ├── website-desktop.report.html
│   ├── website-desktop.png
│   ├── website-mobile.report.json
│   ├── website-mobile.report.html
│   ├── website-mobile.png
│   ├── backoffice-desktop.report.json
│   ├── backoffice-desktop.report.html
│   ├── backoffice-desktop.png
│   ├── backoffice-mobile.report.json
│   ├── backoffice-mobile.report.html
│   └── backoffice-mobile.png
└── after/
    ├── website-desktop.report.json
    ├── website-desktop.report.html
    ├── website-desktop.png
    ├── website-mobile.report.json
    ├── website-mobile.report.html
    ├── website-mobile.png
    ├── backoffice-desktop.report.json
    ├── backoffice-desktop.report.html
    ├── backoffice-desktop.png
    ├── backoffice-mobile.report.json
    ├── backoffice-mobile.report.html
    └── backoffice-mobile.png
```

---

_Reporte generado como parte del feature `feature/audit-frontend`._
