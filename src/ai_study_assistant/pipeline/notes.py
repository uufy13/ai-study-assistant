"""Structured note models produced by the study pipeline."""

from pathlib import Path

from pydantic import BaseModel


class NoteSection(BaseModel):
    """A generated note corresponding to one source chunk."""

    index: int
    content: str


class StudyNote(BaseModel):
    """Structured study note assembled from one or more chunks."""

    source: Path
    title: str
    sections: list[NoteSection]

    def to_markdown(self) -> str:
        """Merge all sections into a single Markdown document."""
        parts = [f"# {self.title}"]
        for section in self.sections:
            parts.append(section.content)
        return "\n\n".join(parts)
