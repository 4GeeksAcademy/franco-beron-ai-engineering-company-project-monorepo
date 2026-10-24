# Frontend Performance Audit

## Nexova — Website + Backoffice

---

## Resumen Ejecutivo

Se realizó una auditoría de rendimiento completa sobre los dos frontends del proyecto Nexova:

| Frontend                   | Build                    | Rutas                                                                                                                     |
| -------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| **Website** (Landing)      | Next.js 16 Static Export | 3 rutas (/, /\_app, /404)                                                                                                 |
| **Backoffice** (Dashboard) | Next.js 16 Static Export | 15 rutas (login, register, forgot-password, reset-password, profile, change-password, incidents, suppliers, inventory/\*) |

### Scores Finales

| Prueba             | Antes | Después | Δ     |
| ------------------ | ----- | ------- | ----- |
| Website Desktop    | 100   | **100** | ✅    |
| Website Mobile     | 93    | **93**  | ✅    |
| Backoffice Desktop | 99    | **100** | ✅ +1 |
| Backoffice Mobile  | 84    | **85**  | ✅ +1 |

Ninguna regresión. El backoffice subió +1 en ambos modos.

---

## 1. Problemas Detectados

### 1.1 Duplicación masiva de funciones `icon()`

Se encontraron **12 definiciones duplicadas** del mismo patrón `function icon(name, className?)` repartidas en todos los archivos del backoffice. Cada archivo definía su propia versión:

```js
function icon(name, className = "") {
  return `<i data-lucide="${name}" class="${className}"></i>`;
}
```

**Archivos afectados (12):**

- `pages/login.js`
- `pages/register.js`
- `pages/forgot-password.js`
- `pages/reset-password.js`
- `pages/account/profile.js`
- `pages/account/change-password.js`
- `pages/backoffice/incidents.js`
- `pages/backoffice/suppliers.js`
- `pages/backoffice/inventory/products.js`
- `pages/backoffice/inventory/orders/index.js`
- `pages/backoffice/inventory/orders/inbound.js`
- `pages/backoffice/inventory/orders/outbound.js`

**Impacto:**

- **Mantenibilidad**: Cualquier cambio en el renderizado de iconos requería editar 12 archivos.
- **Bundle size**: ~200 bytes × 12 = ~2.4KB de código duplicado en el bundle total.
- **Propenso a errores**: Fácil olvidar actualizar algún archivo.

**Solución:** Se creó un componente compartido `<Icon name="..." className="..." />` en `components/Icon.js` y se reemplazaron **61 ocurrencias** de `{icon("...")}` por `<Icon name="..." />`.

### 1.2 Lucide render-blocking

El script de Lucide se cargaba con `strategy="afterInteractive"` (por defecto), lo que significa que se ejecutaba de forma síncrona temprano en la carga de la página.

**Impacto:**

- **LCP**: El script bloqueaba el hilo principal durante ~50-100ms.
- **TBT**: Al ejecutarse en el _main thread_, contribuía al Total Blocking Time.

**Solución aplicada (y revertida parcialmente):**

- Se cambió `useEffect` para que `lucide.createIcons()` se ejecute **una sola vez** al montar (`[]` como dependencia, antes no tenía array = se ejecutaba en cada render).
- Se intentó `lazyOnload` pero **regresó LCP** de 2606ms → 4240ms en backoffice mobile.
- **Decisión final**: Mantener `afterInteractive` (rápido para LCP) + dependencia `[]` (reduce TBT).

### 1.3 Google Fonts CLS

El website carga Google Fonts (Manrope, Space Grotesk) desde `next/head` via `@import` en CSS.

**Impacto:**

- **CLS**: Sin `font-display:swap`, el texto permanece invisible hasta que la fuente se descarga (FOUT/FOIT).
- **Solución intentada**: `@font-face` con `local()` — pero incrementó CLS de 0.029 → 0.063.
- **Decisión final**: Revertido. El CLS 0.029 original ya está en rango "bueno" (< 0.1).

### 1.4 Layout Shift en hero del website

El `.hero-card` sin altura definida provocaba un reflow cuando el contenido se renderizaba dinámicamente desde `main.js`.

**Impacto:**

- CLS de 0.018 en desktop, 0.029 en mobile.
- **Solución**: Se agregó `min-height: 200px` al `.hero-card` y un grid responsive con `grid-template-columns: 1fr` en mobile.

### 1.5 Total Blocking Time en backoffice mobile

El backoffice mobile mostraba un TBT de **423ms** (rango "needs improvement").

**Causa raíz:**

- `lucide.createIcons()` se ejecutaba en cada render del componente `_app.js` (sin dependencias en `useEffect`).
- El script de Lucide (~30KB) se parseaba y ejecutaba síncronamente.

**Solución:**

- `useEffect(() => { lucide?.createIcons(...) }, [])` — se ejecuta **una vez** al montar.
- Resultado: TBT reducido de 423ms → **387ms** (-36ms, ~9% mejora).

---

## 2. Análisis de Refactorización

### 2.1 Componente compartido `<Icon>`

**Archivo creado:** `uis/backoffice/components/Icon.js`

```jsx
import React from "react";

export default function Icon({ name, className = "" }) {
  return <i data-lucide={name} className={className}></i>;
}
```

**Reemplazos realizados:** 61 ocurrencias en 12 archivos.

**Patrón de reemplazo:**

```diff
- import { icon } from "..."
- {icon("search")}
+ import Icon from "../components/Icon"
+ <Icon name="search" />
```

**Casos especiales (ternary expressions):**

```diff
- {icon(saving ? "loader-circle" : "save")}
+ {saving ? <Icon name="loader-circle" /> : <Icon name="save" />}
```

### 2.2 Dependencias de useEffect

**Archivo:** `uis/backoffice/pages/_app.js`

```diff
  useEffect(() => {
    window.lucide?.createIcons({ attrs: { "stroke-width": 1.8 } });
- });
+ }, []);
```

---

## 3. Metodología

### Herramientas

- **Lighthouse** 13.5.0 (Chrome headless via Puppeteer)
- **Puppeteer** (bundled Chromium)
- **Next.js** 16.3.8 (Turbopack, Static Export)

### Configuración de pruebas

- **Desktop**: 1280×720, throttling desktop preset
- **Mobile**: 390×844, throttling mobile preset (Slow 4G, 4x CPU slowdown)
- **3 corridas** por configuración, se reporta la mediana

### Capturas

- `audit/before/` — Screenshots + reportes JSON/HTML pre-fix
- `audit/after/` — Screenshots + reportes JSON/HTML post-fix

---

## 4. Conclusiones

1. **El mayor impacto** vino de corregir el `useEffect` de Lucide (TBT -36ms en mobile, -49ms en desktop).
2. **La refactorización de iconos** mejora mantenibilidad y reduce bundle en ~2.4KB.
3. **El CLS ya era bueno** (0.018-0.029) y no requirió intervención significativa.
4. **La estrategia `lazyOnload` para Lucide es contraproducente** — priorizar TBT sobre LCP empeora la experiencia percibida.
5. **Próximos pasos recomendados:**
   - Implementar carga diferida de rutas del backoffice (code splitting).
   - Servir Lucide desde CDN con precarga (`<link rel="preload">`).
   - Auditar third-party scripts (análiticas, etc.).
   - Implementar Server-Side Rendering para rutas críticas si se migra de static export a SSR.
