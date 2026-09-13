"""Markdown writer: persist StudyNote to local file system."""

from pathlib import Path

from ai_study_assistant.pipeline import StudyNote

from .errors import OutputDirectoryError, WriteError


class MarkdownWriter:
    """Write a StudyNote to a Markdown file under a fixed output directory."""

    def __init__(self, output_dir: Path) -> None:
        """Initialize the writer with the destination directory.

        Args:
            output_dir: Directory where Markdown files will be written.
        """
        self.output_dir = output_dir

    def save(self, note: StudyNote) -> Path:
        """Render note to Markdown and write it to output_dir/{title}.md.

        Args:
            note: The StudyNote to persist.

        Returns:
            The path of the written Markdown file.

        Raises:
            OutputDirectoryError: If the output directory cannot be created.
            WriteError: If the file cannot be written.
        """
        content = note.to_markdown()
        output_path = self.output_dir / f"{note.title}.md"

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as exc:
            raise OutputDirectoryError(
                f"Failed to create output directory: {self.output_dir}"
            ) from exc

        try:
            output_path.write_text(content, encoding="utf-8")
        except (OSError, PermissionError) as exc:
            raise WriteError(f"Failed to write file: {output_path}") from exc

        return output_path
