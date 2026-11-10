from __future__ import annotations

from collections import Counter
from pathlib import Path
import math
import re
import unicodedata


_STOPWORDS = {
    "a", "al", "como", "con", "cual", "de", "del", "el", "en", "es",
    "la", "las", "lo", "los", "para", "por", "que", "se", "su", "un",
    "una", "y",
}
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_DEFAULT_SOURCE = Path(__file__).resolve().parents[3] / "CONTEXT.md"


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    ascii_text = "".join(
        character for character in normalized
        if not unicodedata.combining(character)
    )
    return [
        token
        for token in _TOKEN_PATTERN.findall(ascii_text)
        if token not in _STOPWORDS
    ]


def setup(source_path: str | Path | None = None) -> list[dict[str, str]]:
    """Load documented company facts as traceable Markdown chunks."""
    source = Path(source_path) if source_path else _DEFAULT_SOURCE
    if not source.is_file():
        raise FileNotFoundError("No se encontró la fuente de conocimiento.")

    chunks: list[dict[str, str]] = []
    section = source.stem
    for index, block in enumerate(
        re.split(r"\n\s*\n", source.read_text(encoding="utf-8"))
    ):
        text = block.strip()
        if not text:
            continue
        heading = re.match(r"^#{1,6}\s+(.+)$", text)
        if heading:
            section = heading.group(1).strip()
            text = re.sub(r"^#{1,6}\s+.+$", "", text, count=1).strip()
            if not text:
                continue
        chunks.append({
            "id": f"{source.stem}-{index:04d}",
            "source": source.name,
            "section": section,
            "text": f"{section}\n{text}",
        })
    return chunks


def embed(chunks: list[dict[str, str]]) -> list[dict[str, object]]:
    """Create sparse term-frequency vectors without external model calls."""
    indexed: list[dict[str, object]] = []
    for chunk in chunks:
        indexed.append({
            **chunk,
            "embedding": dict(Counter(_tokens(chunk["text"]))),
        })
    return indexed


def retrieve(
    question: str,
    knowledge_base: list[dict[str, object]],
    *,
    top_k: int = 3,
    threshold: float = 0.12,
) -> list[dict[str, object]]:
    """Rank chunks by cosine similarity and omit weak matches."""
    query_vector = Counter(_tokens(question))
    if not query_vector:
        return []
    query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
    ranked: list[tuple[float, dict[str, object]]] = []

    for chunk in knowledge_base:
        vector = chunk["embedding"]
        dot_product = sum(
            count * int(vector.get(token, 0))
            for token, count in query_vector.items()
        )
        if not dot_product:
            continue
        chunk_norm = math.sqrt(sum(int(value) ** 2 for value in vector.values()))
        score = dot_product / (query_norm * chunk_norm)
        if score >= threshold:
            ranked.append((score, chunk))

    ranked.sort(key=lambda result: (-result[0], str(result[1]["id"])))
    return [
        {
            key: value
            for key, value in chunk.items()
            if key != "embedding"
        } | {"score": round(score, 4)}
        for score, chunk in ranked[:top_k]
    ]


def generate_answer(
    question: str,
    context: list[dict[str, object]] | str,
) -> str:
    """Return only retrieved evidence, with its source attached."""
    del question
    if isinstance(context, str):
        chunks = [{"source": "fuente proporcionada", "text": context}]
    else:
        chunks = context
    if not chunks:
        return "No tengo información suficiente en la base de conocimiento de Nexova."

    passages = []
    for chunk in chunks:
        text = str(chunk["text"]).strip()
        source = str(chunk["source"])
        passages.append(f"{text}\nFuente: {source}")
    return "\n\n".join(passages)


def query(
    question: str,
    knowledge_base: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Run retrieval and generation for callers outside the agent graph."""
    index = knowledge_base if knowledge_base is not None else embed(setup())
    chunks = retrieve(question, index)
    return {
        "answer": generate_answer(question, chunks),
        "chunks": chunks,
    }