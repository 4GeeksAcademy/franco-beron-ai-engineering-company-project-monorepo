"""
Safe snippet for basic pandas cleaning. Copy and adapt for your dataset.
Run: python pandas_clean.py  (ensure pandas is installed)
"""
import sys
from pathlib import Path

import pandas as pd

def main() -> int:
	path = Path("data.csv")
	try:
		df = pd.read_csv(path)
	except FileNotFoundError:
		print(f"Error: file not found: {path}", file=sys.stderr)
		return 1
	except (OSError, UnicodeError, ValueError, pd.errors.ParserError):
		print("Error: no se pudo leer el CSV. Revisa formato, permisos y codificación.", file=sys.stderr)
		return 1

	# Drop fully null columns
	df = df.dropna(axis=1, how="all")

	# Fill or drop nulls in key columns (customise columns)
	# df = df.dropna(subset=["required_col"])
	# df["optional_col"] = df["optional_col"].fillna(0)

	# Normalise column names (optional)
	df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

	# Deduplicate (optional)
	before = len(df)
	df = df.drop_duplicates()

	print(
		f"Rows loaded: {len(df)} | original rows: {before} | columns: {len(df.columns)}",
		file=sys.stdout,
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
