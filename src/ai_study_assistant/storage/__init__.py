"""Storage public surface: persist StudyNote to Markdown files."""

from pathlib import Path

from ai_study_assistant.pipeline import StudyNote

from .errors import OutputDirectoryError, StorageError, WriteError
from .writer import MarkdownWriter

__all__ = [
    "MarkdownWriter",
    "OutputDirectoryError",
    "StorageError",
    "WriteError",
    "save",
]


def save(note: StudyNote, output_dir: Path) -> Path:
    """Persist a StudyNote to a Markdown file in the given directory.

    Args:
        note: The StudyNote to persist.
        output_dir: Directory where the Markdown file will be written.

    Returns:
        The path of the written Markdown file.
    """
    writer = MarkdownWriter(output_dir)
    return writer.save(note)
