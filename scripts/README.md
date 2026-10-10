# `scripts` folder

This folder contains **helper scripts** for the monorepo: development automation, maintenance utilities, repetitive tasks (setup, lint, migrations, data generation, etc.), and internal tooling.

- **Main purpose**: group support tools that do not belong to a specific app, agent, or pipeline but make the team’s work easier.
- **Recommendation**: document each script (what it does, parameters, requirements, usage examples) and keep them reproducible (and safe) across environments.

> _Spanish version: [README.es.md](./README.es.md)._

## Importación de incidencias

Desde la raíz, con las dependencias de support-api instaladas:

```bash
services/support-api/.venv/bin/python scripts/seed_incidents.py ruta/incidents.csv
```

El importador valida UTF-8, encabezados, columnas y estructura de todas las filas antes de escribir. Los registros inválidos se descartan con nombres de campos en `stderr`, nunca con valores ni emails. Un fallo crítico de lectura, parsing o escritura devuelve código `1`, sin traceback. Si falla la persistencia puede haber filas importadas previamente; revisar el destino antes de reintentar. `--database` permite usar un destino local separado.
