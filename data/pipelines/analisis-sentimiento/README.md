# Análisis de sentimiento en reseñas

Pipeline educativo para comparar el rating humano de las reseñas WeLoveReviews con la clasificación de sentimiento de un modelo Hugging Face fijado.

## Estructura

- `src/explore.ipynb`: EDA, decisiones de modelado, resultados y revisión manual.
- `src/app.py`: inferencia de producción y exportación CSV.
- `data/raw/reviews.csv`: dataset original descargado de la fuente oficial del syllabus.
- `data/processed/reviews_with_sentiment.csv`: salida enriquecida generada por el script.
- `requirements.txt`: dependencias fijadas del pipeline.

## Ejecución

Desde esta carpeta, instala `requirements.txt`, ejecuta el notebook y luego:

```bash
python src/app.py
```
