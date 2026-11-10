"""PDF ingestion service — converts PDF to Markdown and extracts metadata.

Uses MarkItDown for PDF→Markdown conversion and py-readability-metrics
for text complexity analysis to estimate processing cost.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from markitdown import MarkItDown

logger = logging.getLogger(__name__)


def convert_pdf_to_markdown(pdf_path: str | Path) -> str:
    """Convert a PDF file to Markdown text using MarkItDown.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Markdown representation of the PDF content.

    Raises:
        FileNotFoundError: If the PDF file does not exist.
        ValueError: If conversion fails or produces empty output.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    md = MarkItDown()
    result = md.convert(str(pdf_path))

    if not result or not result.text_content:
        raise ValueError(f"MarkItDown returned empty content for {pdf_path}")

    markdown_text = result.text_content
    logger.info(
        "PDF→Markdown conversion OK: %s (%d chars)",
        pdf_path.name,
        len(markdown_text),
    )
    return markdown_text


def save_markdown(markdown_text: str, output_path: str | Path) -> Path:
    """Save Markdown text to a file.

    Args:
        markdown_text: The Markdown content to save.
        output_path: Destination file path.

    Returns:
        Path to the saved file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown_text, encoding="utf-8")
    logger.info("Markdown saved: %s (%d chars)", output_path, len(markdown_text))
    return output_path


def extract_text_from_markdown(markdown_text: str) -> str:
    """Strip Markdown formatting to get plain text for readability analysis.

    Removes headers, bold/italic markers, links, images, code blocks,
    blockquotes, horizontal rules, and list markers.
    """
    text = markdown_text
    # Remove code blocks (fenced)
    text = re.sub(r"```[a-z]*\n.*?\n```", "", text, flags=re.DOTALL)
    # Remove inline code
    text = re.sub(r"`[^`]+`", "", text)
    # Remove images
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    # Remove links, keep label
    text = re.sub(r"\[([^\]]*)\]\(.*?\)", r"\1", text)
    # Remove Markdown headers markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r"(\*{1,3}|_{1,3})", "", text)
    # Remove blockquotes
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Remove list markers
    text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    # Clean up excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def compute_readability_metrics(markdown_text: str) -> dict[str, float | int]:
    """Compute readability metrics on the RFP markdown text.

    Uses py-readability-metrics to calculate:
    - Flesch Reading Ease
    - Flesch-Kincaid Grade Level
    - Gunning Fog Index
    Plus basic text statistics.

    Args:
        markdown_text: The Markdown content of the RFP.

    Returns:
        Dict with readability metrics and text statistics.
    """
    from readability import Readability

    plain_text = extract_text_from_markdown(markdown_text)

    if not plain_text or len(plain_text.split()) < 20:
        logger.warning("Text too short for reliable readability metrics")
        return {
            "flesch_reading_ease": None,
            "flesch_kincaid_grade": None,
            "gunning_fog": None,
            "sentence_count": 0,
            "word_count": len(plain_text.split()) if plain_text else 0,
            "character_count": len(plain_text),
        }

    try:
        r = Readability(plain_text)
        flesch = r.flesch()
        fk = r.flesch_kincaid()
        gunning = r.gunning_fog()

        metrics = {
            "flesch_reading_ease": round(flesch.score, 2),
            "flesch_kincaid_grade": round(fk.grade_level, 2),
            "gunning_fog": round(gunning.score, 2),
            "sentence_count": flesch.sentence_count,
            "word_count": flesch.word_count,
            "character_count:": len(plain_text),
        }
        logger.info("Readability metrics computed: %s", metrics)
        return metrics
    except Exception as exc:
        logger.warning("Readability computation failed: %s", exc)
        return {
            "flesch_reading_ease": None,
            "flesch_kincaid_grade": None,
            "gunning_fog": None,
            "sentence_count": 0,
            "word_count": len(plain_text.split()) if plain_text else 0,
            "character_count": len(plain_text),
        }
