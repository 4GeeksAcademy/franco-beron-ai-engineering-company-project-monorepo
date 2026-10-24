const fs = require("fs");
const path = require("path");

const files = ["uis/backoffice/pages/backoffice/suppliers.js"];

for (const relPath of files) {
  const fp = path.join(
    "/workspaces/franco-beron-ai-engineering-company-project-monorepo",
    relPath,
  );
  let c = fs.readFileSync(fp, "utf-8");

  // Remove the standalone icon() function
  c = c.replace(
    /function icon\(name\) \{\s*\n\s*return <i data-lucide=\{name\} aria-hidden="true" \/>;\s*\n\s*\}\s*\n/g,
    "",
  );

  // Replace {icon("name")} or {icon("name", "cls")} with JSX <Icon ... />
  c = c.replace(
    /\{icon\(("(?:[^"\\]|\\.)*")(?:\s*,\s*("(?:[^"\\]|\\.)*"))?\)\}/g,
    (match, name, className) => {
      if (className) {
        return `<Icon name=${name} className=${className} />`;
      }
      return `<Icon name=${name} />`;
    },
  );

  fs.writeFileSync(fp, c, "utf-8");
  console.log("Fixed:", relPath);
}
