import argparse
import csv
import hashlib
from collections import Counter
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SUPPORT_API_ROOT = REPOSITORY_ROOT / "services" / "support-api"
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(SUPPORT_API_ROOT))

from app.config import SERVICE_DIR
from packages.shared.incident_validation import (
    IncidentValidationError,
    transform_csv_row,
)
from tinydb import Query, TinyDB


def load_csv_rows(csv_file: Path):
    try:
        with csv_file.open(encoding="utf-8-sig", newline="") as source:
            return list(csv.DictReader(source))
    except FileNotFoundError:
        print(f"Error: file not found: {csv_file}", file=sys.stderr)
        raise SystemExit(1) from None
    except (OSError, csv.Error) as exc:
        print(f"Error: unreadable CSV file '{csv_file}': {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def seed_rows(rows, incidents, import_keys) -> dict:
    counters = Counter()
    import_query = Query()

    for row_number, row in enumerate(rows, start=2):
        counters["read"] += 1
        try:
            source_key, incident = transform_csv_row(row)
        except IncidentValidationError as error:
            counters["invalid"] += 1
            for field in error.field.split(", "):
                counters[f"invalid:{field}"] += 1
            print(
                f"Fila {row_number}: registro descartado; revisar campos "
                f"{error.field}."
            )
            continue

        fingerprint = hashlib.sha256(source_key.encode("utf-8")).hexdigest()
        if import_keys.search(import_query.fingerprint == fingerprint):
            counters["duplicates"] += 1
            continue

        incident_id = incidents.insert(incident)
        import_keys.insert(
            {
                "fingerprint": fingerprint,
                "incident_id": incident_id,
            }
        )
        counters["inserted"] += 1

    result = {
        key: counters[key]
        for key in ("read", "inserted", "duplicates", "invalid")
    }
    result.update(
        {key: value for key, value in counters.items() if key.startswith("invalid:")}
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Importa incidencias válidas del CSV histórico de Nexova."
    )
    parser.add_argument("csv_file", type=Path, help="Ruta al CSV histórico")
    parser.add_argument(
        "--database",
        type=Path,
        default=SERVICE_DIR / "db.json",
        help="Base TinyDB de destino (por defecto, la del support-api)",
    )
    args = parser.parse_args()

    if not args.csv_file.is_file():
        print(f"Error: file not found: {args.csv_file}", file=sys.stderr)
        return 1

    try:
        rows = load_csv_rows(args.csv_file)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 1

    with TinyDB(args.database) as database:
        result = seed_rows(
            rows,
            database.table("central_incidents"),
            database.table("incident_seed_keys"),
        )

    print(
        "Importación terminada: "
        f"{result.get('read', 0)} filas, "
        f"{result.get('inserted', 0)} nuevas, "
        f"{result.get('duplicates', 0)} duplicadas, "
        f"{result.get('invalid', 0)} inválidas."
    )
    for key in sorted(result):
        if key.startswith("invalid:"):
            print(f"  {key.removeprefix('invalid:')}: {result[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())