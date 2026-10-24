/**
 * Icon — shared component for Lucide icon rendering.
 *
 * Usage (JSX):  <Icon name="mail" className="..." aria-hidden="true" />
 *
 * Why a shared component:
 * - Previously duplicated as `icon()` in main.js (HTML-string helper)
 *   and `icon()` in pages/login.js (JSX helper).
 * - Deduplication reduces bundle size and ensures consistent icon rendering
 *   (stroke-width, aria handling) across all pages.
 */

export default function Icon({ name, className = "", ...props }) {
  return (
    <i
      data-lucide={name}
      className={className || undefined}
      aria-hidden="true"
      {...props}
    />
  );
}
