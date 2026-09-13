"""Pipeline orchestrator: Document -> chunks -> LLM -> StudyNote."""


from ai_study_assistant.llm import LLMClient
from ai_study_assistant.parsers import Document

from .chunker import chunk_text
from .errors import EmptyContentError
from .notes import NoteSection, StudyNote
from .prompts import build_messages


class StudyPipeline:
    """Orchestrates the conversion of a :class:`Document` into a structured
    :class:`StudyNote` via chunking and an injected :class:`LLMClient`.
    """

    def __init__(self, client: LLMClient, *, chunk_size: int = 2000) -> None:
        self._client = client
        self._chunk_size = chunk_size

    def run(self, document: Document) -> StudyNote:
        """Run the pipeline on ``document`` and return a :class:`StudyNote`.

        Args:
            document: The parsed document to process.

        Raises:
            EmptyContentError: If ``document.content`` is empty or whitespace.
            LLMError: Propagated directly from the injected client.
        """
        content = document.content.strip()
        if not content:
            raise EmptyContentError("Document content is empty.")

        chunks = chunk_text(content, chunk_size=self._chunk_size)
        sections: list[NoteSection] = []
        for chunk in chunks:
            section_content = self._client.generate(build_messages(chunk.text))
            sections.append(NoteSection(index=chunk.index, content=section_content))

        return StudyNote(
            source=document.source,
            title=document.source.stem,
            sections=sections,
        )
