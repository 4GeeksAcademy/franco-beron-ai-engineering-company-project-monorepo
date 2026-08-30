# SKILL: Actualizacion de Memory Bank Nexova

## OBJETIVO
Actualizar el `memory-bank` con contexto real y estado verificable despues de cada cambio relevante del repositorio.

## CUANDO USARLA
Usar esta skill cuando:
- Se creen o modifiquen aplicaciones en `uis/`.
- Se agreguen reglas o skills de agentes.
- Se altere estructura del monorepo.
- Se tomen decisiones tecnicas nuevas.
- Se cierre una tarea que impacte negocio o arquitectura.

## INPUTS
- `CONTEXT.md` vigente.
- Lista de archivos creados/modificados/eliminados en la tarea.
- Resultados de validaciones ejecutadas (lint/test/typecheck/build/manual).
- Decisiones tecnicas tomadas y restricciones observadas.

## PROCEDIMIENTO
1. Leer `CONTEXT.md` y extraer solo hechos de negocio verificables.
2. Revisar diff de la tarea e identificar cambios en arquitectura, stack o convenciones.
3. Actualizar `memory-bank/projectbrief.md` solo si cambia el entendimiento del negocio.
4. Actualizar `memory-bank/techContext.md` con stack real, comandos y restricciones tecnicas vigentes.
5. Actualizar `memory-bank/progress.md` con:
   - estado inicial,
   - trabajo realizado,
   - archivos cambiados,
   - validaciones y resultados,
   - problemas y proximos pasos.
6. Verificar coherencia entre los tres archivos y ausencia de placeholders o datos inventados.

## OUTPUT
- `memory-bank/projectbrief.md` consistente con negocio real.
- `memory-bank/techContext.md` consistente con estado tecnico real.
- `memory-bank/progress.md` actualizado al estado final de la tarea.

## CRITERIOS DE ACEPTACION
1. Los tres archivos existen en `memory-bank/`.
2. Ningun archivo contiene placeholders (ejemplo: "TBD", "Company X", "Lorem ipsum").
3. Toda afirmacion de negocio puede trazarse a `CONTEXT.md`.
4. `progress.md` incluye al menos una seccion de validaciones con resultado.
5. `techContext.md` enumera comandos de ejecucion/validacion realmente usados en la tarea.
6. El diff final muestra cambios en `memory-bank/progress.md` cuando hubo cambios de estado/estructura.