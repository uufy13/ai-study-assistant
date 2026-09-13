"""Tests for the storage module."""

from pathlib import Path

import pytest

from ai_study_assistant.pipeline import NoteSection, StudyNote
from ai_study_assistant.storage import (
    MarkdownWriter,
    OutputDirectoryError,
    WriteError,
    save,
)


def _make_note(title: str = "sample") -> StudyNote:
    source = Path("docs") / f"{title}.txt"
    return StudyNote(
        source=source,
        title=title,
        sections=[
            NoteSection(index=0, content="First section."),
            NoteSection(index=1, content="Second section."),
        ],
    )


def test_save_returns_expected_path(tmp_path: Path) -> None:
    """UC1: save returns output_dir / {title}.md."""
    note = _make_note("return-path")
    output_path = save(note, tmp_path)
    assert output_path == tmp_path / "return-path.md"


def test_saved_file_content_matches_note_markdown(tmp_path: Path) -> None:
    """UC2: file content equals note.to_markdown()."""
    note = _make_note("content-match")
    output_path = save(note, tmp_path)
    assert output_path.read_text(encoding="utf-8") == note.to_markdown()


def test_save_creates_output_directory_if_missing(tmp_path: Path) -> None:
    """UC3: directory is created automatically when it does not exist."""
    output_dir = tmp_path / "missing" / "nested"
    assert not output_dir.exists()
    note = _make_note("auto-dir")
    save(note, output_dir)
    assert output_dir.exists()
    assert (output_dir / "auto-dir.md").exists()


def test_save_works_when_directory_already_exists(tmp_path: Path) -> None:
    """UC4: writing to an existing directory succeeds."""
    output_dir = tmp_path / "exists"
    output_dir.mkdir(parents=True, exist_ok=True)
    note = _make_note("exist-ok")
    output_path = save(note, output_dir)
    assert output_path.exists()


def test_save_overwrites_existing_file(tmp_path: Path) -> None:
    """UC5: saving twice overwrites the file with latest content."""
    output_dir = tmp_path
    note1 = _make_note("overwrite")
    note2 = note1.model_copy(
        update={"sections": [NoteSection(index=0, content="Updated content.")]}
    )

    save(note1, output_dir)
    save(note2, output_dir)

    assert (output_dir / "overwrite.md").read_text(encoding="utf-8") == note2.to_markdown()


def test_save_empty_sections_writes_only_title(tmp_path: Path) -> None:
    """UC6: empty sections produce a file containing only the H1 title."""
    note = StudyNote(
        source=Path("docs/empty.txt"),
        title="empty-sections",
        sections=[],
    )
    output_path = save(note, tmp_path)
    assert output_path.read_text(encoding="utf-8") == "# empty-sections"


def test_mkdir_failure_raises_output_directory_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """UC7: OSError during mkdir is mapped to OutputDirectoryError."""

    def fake_mkdir(*args, **kwargs) -> None:
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    note = _make_note("mkdir-fail")
    writer = MarkdownWriter(tmp_path)
    with pytest.raises(OutputDirectoryError):
        writer.save(note)


def test_write_text_failure_raises_write_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """UC8: OSError during write_text is mapped to WriteError."""

    def fake_write_text(self, *args, **kwargs) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", fake_write_text)

    note = _make_note("write-fail")
    writer = MarkdownWriter(tmp_path)
    with pytest.raises(WriteError):
        writer.save(note)
