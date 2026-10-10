# `services` folder

This folder contains **all the backend services** (APIs and background workers) related to the company for the cross-functional AI Engineering project.

Each subfolder inside `services/` must correspond to **one specific service** (for example: `admin-api`, `data-processor-worker`) and include its own technical and functional documentation.

- **Main purpose**: to centralize all the backend logic, APIs, and queue consumers that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the services you add, their objective, the technology used, and how to run them.

## Current services

- [`support-api/`](./support-api/README.md): FastAPI API for authentication, support, inventory, and the Nexova supplier directory. It uses TinyDB for users, profiles, tickets, and suppliers, plus SQLModel/Supabase for inventory.

## Docker development

`services/Dockerfile` uses Python slim, installs `uv`, and installs the support API requirements with `uv pip install`. The root Compose file bind-mounts `services/` and runs Uvicorn with `--reload` on port 8001.

```bash
docker compose up
```

> _Spanish version: [README.es.md](./README.es.md)._
