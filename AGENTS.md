# AGENTS.md

## Objetivo

Definir reglas obligatorias para cualquier agente que trabaje en este repositorio.

## Lectura mínima obligatoria al iniciar cada sesión

Todo agente debe leer, en este orden, antes de modificar código o documentación:

1. `CONTEXT.md`
2. `memory-bank/projectbrief.md`
3. `memory-bank/techContext.md`
4. `memory-bank/progress.md`
5. `README.md` de la raíz
6. `README.md` de cada carpeta que vaya a modificar o donde vaya a crear archivos

## Convenciones obligatorias

- Respetar la estructura del monorepo y el propósito de cada carpeta.
- No crear estructuras duplicadas si ya existe una ruta equivalente.
- No inventar información de negocio: usar solo `CONTEXT.md` y artefactos del repositorio.
- Mantener actualizado `memory-bank/` cuando cambien estado, arquitectura o decisiones técnicas.
- Si se trabaja en UI, mantener separación clara entre `uis/website` (público) y `uis/backoffice` (interno).
- Si se requiere backend nuevo, evaluarlo en `services/` y confirmar que no exista uno equivalente.

## Flujo obligatorio antes de cada commit

No se permite commit hasta completar todos los pasos:

1. Verificar que los cambios cumplen exactamente la tarea solicitada y no agregan alcance no pedido.
2. Ejecutar validaciones disponibles para lo modificado (`lint`, `test`, `typecheck`, `build` o equivalentes del proyecto afectado).
3. Revisar el diff completo y confirmar que no hay cambios accidentales ni archivos sensibles expuestos.
4. Confirmar que no se duplicaron carpetas/funcionalidades y que se respetaron los `README.md` relevantes.
5. Actualizar `memory-bank/progress.md` con estado final, validaciones y decisiones.
6. Solo después de completar los pasos anteriores, habilitar el commit.

## Cuándo detenerse y preguntar al desarrollador

El agente debe detenerse y pedir confirmación cuando:

- El `CONTEXT.md` no tenga información suficiente y sea necesario inventar datos para continuar.
- Exista contradicción entre una solicitud y reglas del repositorio.
- Haya que modificar o eliminar archivos críticos listados abajo.
- Se detecte posible impacto destructivo o riesgo de pérdida de información.

## Archivos/carpetas que no se deben modificar sin confirmación explícita

- `CONTEXT.md`
- `.devcontainer/devcontainer.json`
- `packages/shared/package.json`
- `packages/shared/types/index.ts`
- `.gitignore`

## Reglas de seguridad operativa

- No borrar archivos existentes salvo necesidad justificada y validada.
- No sobrescribir configuraciones sin inspección previa.
- No cambiar framework/stack existente sin aprobación.
- No introducir dependencias innecesarias.

## Mantenimiento del memory-bank

Después de cualquier cambio relevante, el agente debe actualizar:

- `memory-bank/projectbrief.md` si cambia el entendimiento de negocio.
- `memory-bank/techContext.md` si cambia stack, arquitectura o comandos.
- `memory-bank/progress.md` al cierre de cada tarea.
