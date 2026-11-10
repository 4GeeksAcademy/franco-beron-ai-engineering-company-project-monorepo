## Feature: RFP Intake Pipeline (Part 1/3)

### Descripción

Implementación completa del pipeline de ingesta de RFP (Request for Proposal) para Nexova. Esta es la primera de tres partes, que cubre el flujo desde la subida del PDF hasta el análisis completo y handoff a Ventas.

### ¿Qué incluye?

#### Backend (Python/FastAPI/LangGraph)

| Componente                 | Archivo                                           | Propósito                                                               |
| -------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------- |
| **Pipeline principal**     | `data/pipelines/rfp_intake/graph.py`              | Grafo LangGraph con 9 nodos (orchestrator-worker-synthesizer)           |
| **PDF→Markdown**           | `data/pipelines/rfp_intake/pdf_service.py`        | Conversión vía MarkItDown + métricas de legibilidad                     |
| **Clasificador**           | `data/pipelines/rfp_intake/classifier.py`         | Heurísticas para detectar RFP válidas vs pitches de vendedores          |
| **Extractor de metadatos** | `data/pipelines/rfp_intake/metadata_extractor.py` | Extrae cliente, HQ, servicios, alcance, deadline, presupuesto           |
| **Modelos SQLModel**       | `services/support-api/app/rfp_models.py`          | 4 tablas: `RFPTicket`, `RFPMetadata`, `DepartmentSection`, `RFPHandoff` |
| **Router API**             | `services/support-api/app/routers/rfp.py`         | 3 endpoints: upload (202), status, list                                 |
| **DB integration**         | `services/support-api/app/database.py`            | Registro de modelos RFP en SQLite fallback                              |

#### Frontend (Vanilla JS SPA)

| Componente                  | Archivo                  | Propósito                                                              |
| --------------------------- | ------------------------ | ---------------------------------------------------------------------- |
| **UI de carga y monitoreo** | `uis/backoffice/main.js` | Formulario de upload, lista de tickets, detalle con metadata y handoff |

#### Testing & Utilidades

| Componente                 | Archivo                              | Propósito                                                      |
| -------------------------- | ------------------------------------ | -------------------------------------------------------------- |
| **Tests unitarios**        | `tests/pipelines/test_rfp_intake.py` | 40 tests: classifier, metadata extractor, workers, integración |
| **CLI de reprocesamiento** | `scripts/rfp_reprocess.py`           | `python scripts/rfp_reprocess.py ruta/al/pdf`                  |

### Flujo del Pipeline

```
PDF Upload → ingest_pdf → classify → extract_metadata → orchestrator
                                                          ↓
                  ┌──────────────────┬────────────────────┤
                  ↓                  ↓                    ↓
          worker_seleccion   worker_capacitacion    worker_soporte
                  ↓                  ↓                    ↓
                  └──────────────────┴────────────────────┘
                                          ↓
                                    synthesizer → persist_results → END
```

- Si `classify` determina que NO es una RFP válida → `descartado_end`
- Si hay error en cualquier nodo → `error_end`

### Endpoints API

| Método | Ruta                          | Descripción                                                        |
| ------ | ----------------------------- | ------------------------------------------------------------------ |
| `POST` | `/api/rfp/upload`             | Sube PDF → crea ticket `analizando` → pipeline async → retorna 202 |
| `GET`  | `/api/rfp/status/{ticket_id}` | Estado completo + metadata + departamentos + handoff               |
| `GET`  | `/api/rfp/tickets`            | Lista todos los tickets RFP                                        |

### Cómo probar

```bash
# 1. Iniciar el servidor
cd services/support-api
uvicorn app.main:app --reload

# 2. Probar con los PDFs de ejemplo (desde el repositorio del syllabus)
curl -X POST http://localhost:8000/api/rfp/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@nexova-request-1.pdf"

# 3. Consultar estado
curl http://localhost:8000/api/rfp/status/<ticket_id>

# 4. Probar clasificación de documento inválido
curl -X POST http://localhost:8000/api/rfp/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@nexova-request-3.pdf"
# → Debe resultar en status "descartado"

# 5. Reprocesamiento manual vía CLI
python scripts/rfp_reprocess.py data/raw/<ticket_id>_nexova-request-1.pdf
```

### Resultados esperados con PDFs de ejemplo

| PDF                                         | Clasificación | Departamentos               | Moneda |
| ------------------------------------------- | ------------- | --------------------------- | ------ |
| `nexova-request-1.pdf` (Vantex, formal)     | `rfp_valida`  | `seleccion`, `capacitacion` | EUR    |
| `nexova-request-2.pdf` (NubeSoft, informal) | `rfp_valida`  | `soporte`, `seleccion`      | USD    |
| `nexova-request-3.pdf` (vendor pitch)       | `descartado`  | —                           | —      |

### Criterios de aceptación cubiertos

- [x] Upload de PDF con respuesta 202 (aceptado asíncrono)
- [x] Creación de ticket en DB con estado `analizando`
- [x] Pipeline con clasificador que rechaza documentos no-RFP
- [x] Detección de departamentos aplicables (selección, capacitación, soporte)
- [x] Extracción de metadatos (cliente, HQ, servicios, alcance, deadline, presupuesto)
- [x] Workers extraen secciones relevantes para cada departamento
- [x] Síntesis con payload estructurado para handoff a Ventas
- [x] Persistencia en PostgreSQL (con SQLite como fallback)
- [x] UI en backoffice con upload, listado y detalle de tickets
- [x] Tests unitarios (40 tests, todos pasando)
- [x] No se inventan headcounts/volúmenes no presentes en el RFP
- [x] Moneda determinada por HQ del cliente (España→EUR, Miami/US→USD)
- [x] IDs de departamento exactos del BRIEFING
