"""Text chunking utilities for the study pipeline."""

from dataclasses import dataclass


@dataclass
class Chunk:
    """A single text chunk produced by the chunker."""

    index: int
    text: str


def chunk_text(text: str, *, chunk_size: int = 2000) -> list[Chunk]:
    """Split ``text`` into paragraph-aligned chunks.

    The algorithm greedily aggregates paragraphs (separated by ``\\n\\n``)
    until adding the next paragraph would exceed ``chunk_size``. Paragraphs
    longer than ``chunk_size`` are hard-split at the character boundary.
    Leading whitespace of paragraphs (e.g. indented code blocks) is preserved.

    Args:
        text: Source text to chunk.
        chunk_size: Maximum character length of a chunk. Must be positive.

    Returns:
        A list of :class:`Chunk` instances, which is empty when ``text`` is
        empty or contains only whitespace.

    Raises:
        ValueError: If ``chunk_size`` is not a positive integer.
    """
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")

    if not text.strip():
        return []

    paragraphs = text.split("\n\n")
    chunks: list[Chunk] = []
    current_parts: list[str] = []
    current_length = 0
    index = 0

    def flush() -> None:
        nonlocal current_parts, current_length, index
        if not current_parts:
            return
        chunks.append(Chunk(index=index, text="\n\n".join(current_parts)))
        index += 1
        current_parts = []
        current_length = 0

    for para in paragraphs:
        if not para.strip():
            continue
        para_len = len(para)

        if para_len > chunk_size:
            flush()
            start = 0
            while start < para_len:
                end = min(start + chunk_size, para_len)
                chunks.append(Chunk(index=index, text=para[start:end]))
                index += 1
                start = end
            continue

        separator = 2 if current_parts else 0
        if current_length + separator + para_len > chunk_size:
            flush()
            separator = 0

        current_parts.append(para)
        current_length += para_len + separator

    flush()
    return chunks
