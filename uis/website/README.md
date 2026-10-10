# Website — Nexova

Aplicacion publica corporativa de Nexova.

## Objetivo

Mostrar identidad, propuesta de valor y servicios de Nexova para clientes corporativos de tecnologia, retail y finanzas.

## Stack

- Next.js
- React
- HTML
- CSS
- JavaScript (modulos ES)

## Ejecutar con Docker

Desde la raiz del repositorio:

```bash
docker compose up
```

Abrir `http://localhost:3000/`.

## Ejecutar sin Docker

```bash
cd uis/website
npm install
npm run dev -- --port 3000
```

La pagina Next conserva los componentes, estilos y modulos ES existentes.

## Alcance actual

- Ruta `/` operativa.
- Navegacion principal.
- Secciones de servicios, propuesta de valor y metodologia.
- Contenido basado en `CONTEXT.md` (Nexova).
