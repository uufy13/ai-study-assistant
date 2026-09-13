"""Pipeline public surface: orchestrate Document -> StudyNote."""

from ai_study_assistant.llm import LLMClient
from ai_study_assistant.parsers import Document

from .chunker import Chunk, chunk_text
from .errors import EmptyContentError, PipelineError
from .notes import NoteSection, StudyNote
from .prompts import SYSTEM_PROMPT, build_messages
from .runner import StudyPipeline

__all__ = [
    "SYSTEM_PROMPT",
    "Chunk",
    "EmptyContentError",
    "LLMClient",
    "NoteSection",
    "PipelineError",
    "StudyNote",
    "StudyPipeline",
    "build_messages",
    "chunk_text",
    "run",
]


def run(
    document: Document,
    client: LLMClient,
    *,
    chunk_size: int = 2000,
) -> StudyNote:
    """Run the pipeline on a parsed Document and return a StudyNote.

    Args:
        document: The parsed document to process.
        client: An LLMClient implementation.
        chunk_size: Maximum character length of a chunk.

    Returns:
        The generated StudyNote.
    """
    pipeline = StudyPipeline(client, chunk_size=chunk_size)
    return pipeline.run(document)
