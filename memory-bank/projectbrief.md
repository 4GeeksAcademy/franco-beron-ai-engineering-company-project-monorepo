# Project Brief — Nexova

## Empresa

Nexova es una firma de consultoría y outsourcing de recursos humanos con sede en Valencia (España) y oficina en Miami.

## Qué hace la empresa

Nexova opera servicios de RR. HH. y, dentro de sus líneas de negocio, gestiona un servicio de outsourcing de soporte al cliente para empresas de tecnología, retail y finanzas.

## Problema que resuelve

El equipo de soporte de Nexova trabaja con un helpdesk legado y presenta una brecha de servicio: el SLA comprometido con clientes es de 24 horas, pero el promedio actual está en 48 horas. La empresa necesita visibilidad operativa para entender backlog, calidad de atención y causas de incumplimiento.

## Usuarios y clientes

- Clientes corporativos de Nexova (tecnología, retail y finanzas).
- Equipo interno de soporte (30 agentes).
- Supervisores de soporte.
- Liderazgo técnico y de operaciones:
  - Sergio Molina (CTO, Nexova AI Engineering)
  - Roberto Díaz (Customer Support Lead)

## Producto/servicio del proyecto

El proyecto actual se enfoca en una utilidad de análisis de datos para reportes de incidentes de soporte. El resultado esperado es una lectura clara, confiable y accionable de tickets desde CSV, incluyendo:

- Calidad de datos e invalidaciones por regla.
- Distribución por categoría y estado.
- Índice de satisfacción para tickets cerrados.
- Exportación resumida para reportes internos.

## Objetivos del proyecto

- Entregar análisis operativo fiable para revisión con clientes.
- Reducir incertidumbre sobre backlog y satisfacción.
- Estandarizar reglas de validación de incidentes.
- Mantener privacidad: no exponer correos de clientes en salidas.
- Habilitar trabajo de agentes de IA con contexto consistente en este monorepo.

## Contexto de negocio que debe conocer cualquier agente

- Fuente de verdad de dominio: `CONTEXT.md`.
- Los datos de incidentes incluyen información sensible (`customer_email`).
- No se debe imprimir ni exportar direcciones de correo individuales.
- El desempeño de soporte y el cumplimiento de SLA son métricas críticas para Nexova.
- Los entregables deben apoyar decisiones de supervisores y preparación de revisiones con clientes.
