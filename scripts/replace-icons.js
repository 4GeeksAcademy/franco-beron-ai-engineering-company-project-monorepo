/**
 * Replace all {icon("name")} patterns with <Icon name="name" /> in backoffice page files.
 */
const fs = require("fs");
const path = require("path");

const dir =
  "/workspaces/franco-beron-ai-engineering-company-project-monorepo/uis/backoffice/pages";

const files = [
  "login.js",
  "forgot-password.js",
  "register.js",
  "reset-password.js",
  "account/change-password.js",
  "account/profile.js",
  "backoffice/incidents.js",
  "backoffice/suppliers.js",
  "backoffice/inventory/products.js",
  "backoffice/inventory/orders/index.js",
  "backoffice/inventory/orders/inbound.js",
  "backoffice/inventory/orders/outbound.js",
];

// Regex: {icon("name")} or {icon("name", "className")}
const REGEX = /\{icon\(("[^"]+")(?:\s*,\s*("[^"]+"))?\)\}/g;

let total = 0;
for (const file of files) {
  const filePath = path.join(dir, file);
  let content = fs.readFileSync(filePath, "utf-8");
  const original = content;

  content = content.replace(REGEX, (match, name, className) => {
    total++;
    if (className) {
      return `<Icon name=${name} className=${className} />`;
    }
    return `<Icon name=${name} />`;
  });

  if (content !== original) {
    fs.writeFileSync(filePath, content, "utf-8");
    console.log(`✓ ${file} — icon() calls replaced`);
  } else {
    console.log(`  ${file} — no changes`);
  }
}
console.log(`\nTotal replacements: ${total}`);
