# `uis` folder

This folder contains **all projects with a user interface** for the cross-functional AI Engineering company project — for example: a public website, admin dashboard frontend, ecommerce UI, customer portals, Streamlit/Gradio app or other frontend-only tools.

The two main projects stored here are:

- **`website`** — the company's public-facing web presence.
- **`backoffice`** — the internal admin application. This is the ideal place to develop multiple solutions within a single project: authentication, people management, operations management, internal communication, and other back-office capabilities.

Organize `uis/` by **different concerns** — each subfolder covers a distinct area of the company (for example, public web vs internal operations) and includes its own technical and functional documentation.

- **Main purpose**: to centralize in a single place all frontend applications that support the company's use cases.
- **Recommendation**: document in this file (or in sub-READMEs) the applications you add, their objective, the technology used, and how to run them.

## Docker development

`uis/Dockerfile` uses Node Alpine and installs `website` and `backoffice` dependencies separately. `start.sh` runs both Next.js development servers in one container on ports 3000 and 3001. The root `docker-compose.yml` bind-mounts this directory so source changes trigger hot reload.

Run the complete platform from the repository root:

```bash
docker compose up
```

> _Estas instrucciones también están disponibles en [español](./README.es.md)._
