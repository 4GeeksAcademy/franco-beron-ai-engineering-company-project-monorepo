# Backoffice — Nexova Ops

Aplicacion interna para supervisores y operaciones de soporte de Nexova.

## Objetivo

Entregar una vista inicial con contexto operativo relevante: SLA, tamano del equipo, alcance del analisis y lineamientos de privacidad.

## Stack

- HTML
- CSS
- JavaScript (modulos ES)

## Ejecutar local

```bash
cd uis/backoffice
python3 -m http.server 4174
```

Abrir `http://127.0.0.1:4174/`.

## Alcance actual

- Ruta `/` operativa.
- Layout propio (sidebar + content), distinto al website publico.
- Informacion visible alineada con `CONTEXT.md`.
