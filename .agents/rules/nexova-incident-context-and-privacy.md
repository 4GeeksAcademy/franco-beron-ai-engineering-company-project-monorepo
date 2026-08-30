# Regla: Nexova Incident Context & Privacy

## Objetivo

Asegurar que todo entregable relacionado con Nexova use contexto real de `CONTEXT.md` y preserve privacidad de datos sensibles de incidentes.

## Cuándo se aplica

Siempre que se creen o modifiquen archivos en:

- `memory-bank/`
- `uis/`
- `services/`
- `agents/`
- `skills/`
- `docs/`

## Alcance (archivos/carpetas)

- Aplica a contenido funcional, documentación y ejemplos que mencionen tickets, clientes o reportes.
- Aplica especialmente cuando se usen campos del CSV (`ticket_id`, `status`, `category`, `satisfaction_score`, `customer_email`).

## Qué debe hacer el agente

- Basar narrativa, labels, métricas y textos únicamente en `CONTEXT.md` y archivos reales del repo.
- Explicar explícitamente la brecha SLA (24h objetivo vs 48h actual) cuando sea relevante.
- Mantener `customer_email` como dato sensible: mostrar solo reglas o estados agregados, nunca valores individuales.
- En UI y reportes, priorizar métricas agregadas y breakdowns permitidos.

## Qué no debe hacer el agente

- No inventar cifras de negocio no presentes en `CONTEXT.md`.
- No imprimir, registrar, exportar o hardcodear emails de clientes reales o simulados como ejemplo.
- No reutilizar placeholders genéricos de empresa que contradigan el dominio Nexova.

## Cómo comprobar cumplimiento

Checklist verificable:

1. Buscar menciones de contexto no soportado por `CONTEXT.md` y corregirlas.
2. Ejecutar búsqueda de patrones de email en archivos nuevos/modificados y confirmar ausencia de direcciones concretas.
3. Revisar que textos de website/backoffice describan Nexova y no otra empresa.
4. Verificar que `memory-bank/projectbrief.md` cite el problema de SLA y usuarios correctos.
5. Confirmar actualización de `memory-bank/progress.md` con validaciones realizadas.
