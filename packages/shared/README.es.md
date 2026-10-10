# Validación compartida

`incident_validation.py` contiene funciones puras de validación y transformación CSV compartidas por la API de soporte y `scripts/seed_incidents.py`.

El CSV histórico no está guardado en este repositorio. Indica su ruta al ejecutar el seed; el correo se valida, pero nunca se persiste ni se imprime.
