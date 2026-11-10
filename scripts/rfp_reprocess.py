#!/usr/bin/env python3
"""CLI helper to manually re-process an RFP PDF through the intake pipeline.

Usage:
    python scripts/rfp_reprocess.py path/to/nexova-request-1.pdf

This runs the same LangGraph pipeline that the API uses and prints
the final classification, departments, and metadata to stdout.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Add the project root to sys.path so we can import from services/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.pipelines.rfp_intake.graph import run_rfp_intake

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/rfp_reprocess.py <path-to-pdf>", file=sys.stderr)
        sys.exit(1)

    pdf_path = Path(sys.argv[1]).resolve()

    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    if pdf_path.suffix.lower() != ".pdf":
        print(f"Warning: File is not a PDF (suffix: {pdf_path.suffix})", file=sys.stderr)

    print(f"Processing: {pdf_path.name}")
    print(f"Full path: {pdf_path}")
    print("-" * 60)

    result = run_rfp_intake(str(pdf_path), pdf_path.name)

    if result.get("error"):
        print(f"\n❌ Error: {result['error']}")
        sys.exit(1)

    print(f"\n✅ Ticket ID:     {result['ticket_id']}")
    print(f"   Status:        {result['status']}")
    print(f"   Classification: {result.get('classification', 'N/A')}")
    print(f"   Departments:   {', '.join(result.get('departments', []))}")

    if result.get("trace"):
        print(f"\nPipeline trace ({len(result['trace'])} steps):")
        for step in result["trace"]:
            node = step.get("node", "?")
            ts = step.get("timestamp", "?")[11:19]
            print(f"  [{ts}] {node}")

    print("\nDone.")


if __name__ == "__main__":
    main()
