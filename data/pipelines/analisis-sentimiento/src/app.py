import argparse
import csv
import re
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "raw" / "reviews.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "reviews_with_sentiment.csv"
MODEL_ID = "nlptown/bert-base-multilingual-uncased-sentiment"
MODEL_REVISION = "8f6f4e3a8f70be4b65d3a4a8762b6d781cda240d"
REQUIRED_COLUMNS = ("review_id", "rating", "review_text")
SENTIMENT_LABELS = {
    1: "negative",
    2: "negative",
    3: "neutral",
    4: "positive",
    5: "positive",
}


def load_reviews(input_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with input_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError("El CSV no contiene una fila de encabezado.")
        missing_columns = set(REQUIRED_COLUMNS) - set(reader.fieldnames)
        if missing_columns:
            raise ValueError(
                "Faltan columnas requeridas: "
                + ", ".join(sorted(missing_columns))
            )

        rows = list(reader)
        input_columns = list(reader.fieldnames)

    if not rows:
        raise ValueError("El CSV no contiene reseñas.")

    for row_number, row in enumerate(rows, start=2):
        try:
            rating = int(row["rating"])
        except (TypeError, ValueError) as error:
            raise ValueError(f"Rating inválido en la fila {row_number}.") from error
        if rating < 1 or rating > 5:
            raise ValueError(f"Rating fuera de rango en la fila {row_number}.")
        if not row["review_text"].strip():
            raise ValueError(f"Texto vacío en la fila {row_number}.")

    return rows, input_columns


def parse_predicted_stars(label: str) -> int:
    match = re.search(r"\b([1-5])\b", label)
    if match is None:
        raise ValueError(f"Etiqueta de estrellas inesperada: {label!r}")
    return int(match.group(1))


def predict_rows(
    rows: list[dict[str, str]],
    classifier: Callable,
    batch_size: int,
) -> list[dict[str, str]]:
    enriched_rows = []
    for offset in range(0, len(rows), batch_size):
        batch = rows[offset : offset + batch_size]
        predictions = classifier(
            [row["review_text"] for row in batch],
            batch_size=batch_size,
            truncation=True,
            max_length=512,
        )
        if len(predictions) != len(batch):
            raise ValueError("El modelo devolvió una cantidad inesperada de resultados.")

        for row, prediction in zip(batch, predictions):
            stars = parse_predicted_stars(prediction["label"])
            enriched_rows.append(
                {
                    **row,
                    "predicted_stars": stars,
                    "sentiment": SENTIMENT_LABELS[stars],
                    "prediction_confidence": round(float(prediction["score"]), 6),
                }
            )
    return enriched_rows


def run_inference(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    batch_size: int = 2,
) -> dict[str, object]:
    if batch_size < 1:
        raise ValueError("batch_size debe ser mayor que cero.")

    try:
        from transformers import pipeline
    except ImportError as error:
        raise RuntimeError(
            "Instala las dependencias con `python -m pip install -r requirements.txt`."
        ) from error

    rows, input_columns = load_reviews(input_path)
    classifier = pipeline(
        "sentiment-analysis",
        model=MODEL_ID,
        revision=MODEL_REVISION,
        device=-1,
    )
    enriched_rows = predict_rows(rows, classifier, batch_size)
    output_columns = [
        *input_columns,
        "predicted_stars",
        "sentiment",
        "prediction_confidence",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=output_columns)
        writer.writeheader()
        writer.writerows(enriched_rows)

    sentiments = Counter(row["sentiment"] for row in enriched_rows)
    return {
        "processed_reviews": len(enriched_rows),
        "average_rating": round(mean(int(row["rating"]) for row in rows), 2),
        "sentiment_counts": dict(sentiments),
        "output_path": output_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clasifica reseñas con un modelo Hugging Face fijado."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=2)
    arguments = parser.parse_args()

    summary = run_inference(
        input_path=arguments.input,
        output_path=arguments.output,
        batch_size=arguments.batch_size,
    )
    print(f"Reseñas procesadas: {summary['processed_reviews']}")
    print(f"Rating humano promedio: {summary['average_rating']:.2f} / 5")
    print(f"Distribución de sentimiento: {summary['sentiment_counts']}")
    print(f"Archivo generado: {summary['output_path']}")


if __name__ == "__main__":
    main()
