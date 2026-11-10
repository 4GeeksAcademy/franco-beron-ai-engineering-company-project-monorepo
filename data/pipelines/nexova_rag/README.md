# Nexova RAG pipeline

Pipeline local y determinista sobre `CONTEXT.md`, la fuente de verdad de negocio
del monorepo. No envía preguntas ni documentos a servicios externos.

## Funciones

- `setup(source_path=None)` carga bloques Markdown con fuente e identificador.
- `embed(chunks)` genera vectores dispersos por frecuencia de términos.
- `retrieve(question, knowledge_base)` devuelve coincidencias con score y cita.
- `generate_answer(question, context)` produce una respuesta extractiva con fuente.
- `query(question, knowledge_base=None)` mantiene el flujo RAG combinado para usos
  directos; el agente LangGraph llama `retrieve` y `generate_answer` por separado.

Ejecuta los evals de trazas desde `services/support-api` con:

```bash
uv run pytest ../../tests/pipelines
```
