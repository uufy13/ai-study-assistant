"""Tests for the study pipeline module.

All LLM calls are handled by FakeLLMClient; no real API or network access is
used.
"""

from pathlib import Path
from typing import Any

import pytest

from ai_study_assistant.llm import LLMError, Message
from ai_study_assistant.parsers import Document
from ai_study_assistant.pipeline import (
    EmptyContentError,
    NoteSection,
    StudyNote,
    StudyPipeline,
    chunk_text,
    run,
)
from ai_study_assistant.pipeline.prompts import SYSTEM_PROMPT


class FakeLLMClient:
    """Pure-Python LLMClient implementation that records calls and returns
    deterministic canned text.
    """

    def __init__(self, responses: list[str] | None = None) -> None:
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.responses = responses or []
        self._index = 0
        self._should_raise: LLMError | None = None

    def generate(self, messages: list[Message], **overrides: Any) -> str:
        self.calls.append((messages, overrides))
        if self._should_raise is not None:
            raise self._should_raise
        response = self.responses[self._index % len(self.responses)]
        self._index += 1
        return response

    def raise_on_call(self, exc: LLMError) -> None:
        self._should_raise = exc


# ---------------------------------------------------------------------------
# Chunking tests (cases 1-5)
# ---------------------------------------------------------------------------


def make_paragraphs(count: int, words_per_para: int = 5) -> str:
    return "\n\n".join(
        " ".join(f"word{i*words_per_para+j}" for j in range(words_per_para))
        for i in range(count)
    )


def test_short_text_yields_single_chunk():
    text = make_paragraphs(2)
    chunks = chunk_text(text, chunk_size=2000)
    assert len(chunks) == 1
    assert chunks[0].index == 0
    assert chunks[0].text == text


def test_long_text_yields_multiple_chunks():
    text = make_paragraphs(20, words_per_para=50)
    chunks = chunk_text(text, chunk_size=200)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 200


def test_chunk_split_respects_paragraph_boundaries():
    para1 = "alpha " * 10
    para2 = "beta " * 10
    para3 = "gamma " * 10
    text = f"{para1}\n\n{para2}\n\n{para3}"
    chunks = chunk_text(text, chunk_size=len(para1) + len(para2) + 10)
    assert len(chunks) == 2
    assert chunks[0].text.startswith(para1.rstrip())
    assert para2.rstrip() in chunks[0].text
    assert chunks[1].text.strip() == para3.strip()
    assert "\n\n" in chunks[0].text


def test_long_paragraph_is_hard_split():
    para = "x" * 500
    chunks = chunk_text(para, chunk_size=200)
    total = sum(len(chunk.text) for chunk in chunks)
    assert total == 500
    for chunk in chunks:
        assert len(chunk.text) <= 200
    assert len(chunks) == 3


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_chunk_size_must_be_positive():
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=0)
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=-1)


def test_preserves_paragraph_indentation():
    text = "    indented code\n\nnormal paragraph"
    chunks = chunk_text(text, chunk_size=2000)
    assert len(chunks) == 1
    assert chunks[0].text.startswith("    indented code")


def test_aggregated_chunks_respect_chunk_size():
    paras = ["x" * 10] * 6
    text = "\n\n".join(paras)
    chunks = chunk_text(text, chunk_size=32)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 32


# ---------------------------------------------------------------------------
# Pipeline run tests (cases 6-12)
# ---------------------------------------------------------------------------


def _doc(content: str, name: str = "sample.md") -> Document:
    return Document(source=Path(f"/tmp/{name}"), format="markdown", content=content)


def test_run_single_chunk_makes_one_llm_call():
    client = FakeLLMClient(["## Section 1\n\nSummary A"])
    pipeline = StudyPipeline(client, chunk_size=2000)
    doc = _doc(make_paragraphs(2))
    note = pipeline.run(doc)
    assert len(client.calls) == 1
    assert len(note.sections) == 1
    assert note.sections[0].content == "## Section 1\n\nSummary A"


def test_run_multiple_chunks_makes_matching_sections():
    responses = [f"## Note {i}\n\ncontent {i}" for i in range(3)]
    client = FakeLLMClient(responses)
    pipeline = StudyPipeline(client, chunk_size=700)
    doc = _doc(make_paragraphs(6, words_per_para=40))
    note = pipeline.run(doc)
    assert len(client.calls) == len(note.sections)
    assert len(note.sections) == 3
    for i, section in enumerate(note.sections):
        assert section.index == i
        assert section.content == responses[i]


def test_run_records_prompt_messages():
    client = FakeLLMClient(["note"])
    pipeline = StudyPipeline(client, chunk_size=2000)
    doc = _doc("Important concept.")
    pipeline.run(doc)

    messages, _overrides = client.calls[0]
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[0].content == SYSTEM_PROMPT
    assert messages[1].role == "user"
    assert "Important concept." in messages[1].content
    assert messages[1].content.startswith("请根据以下学习材料生成学习笔记：")


def test_study_note_assembly_uses_source_stem():
    client = FakeLLMClient(["body"])
    pipeline = StudyPipeline(client)
    doc = _doc("content", name="my-notes.md")
    note = pipeline.run(doc)
    assert note.source == doc.source
    assert note.title == "my-notes"
    assert len(note.sections) == 1


def test_to_markdown_joins_sections():
    sections = [
        NoteSection(index=0, content="## A\n\nbody a"),
        NoteSection(index=1, content="## B\n\nbody b"),
    ]
    note = StudyNote(source=Path("/tmp/x.md"), title="x", sections=sections)
    md = note.to_markdown()
    assert md.startswith("# x")
    assert "## A" in md
    assert "## B" in md
    assert md == "# x\n\n## A\n\nbody a\n\n## B\n\nbody b"


def test_empty_document_raises_empty_content_error():
    client = FakeLLMClient(["never"])
    pipeline = StudyPipeline(client)
    doc = _doc("   \n\n  ")
    with pytest.raises(EmptyContentError):
        pipeline.run(doc)
    assert len(client.calls) == 0


def test_llm_error_propagates_unchanged():
    client = FakeLLMClient(["ignored"])
    exc = LLMError("boom")
    client.raise_on_call(exc)
    pipeline = StudyPipeline(client, chunk_size=10)
    doc = _doc("word " * 50)
    with pytest.raises(LLMError, match="boom"):
        pipeline.run(doc)


# ---------------------------------------------------------------------------
# Public run() convenience function
# ---------------------------------------------------------------------------


def test_run_convenience_accepts_document():
    client = FakeLLMClient(["convenience"])
    doc = _doc("hello")
    note = run(doc, client)
    assert note.title == "sample"
    assert note.sections[0].content == "convenience"
