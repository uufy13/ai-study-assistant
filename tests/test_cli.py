"""Tests for ai_study_assistant.cli."""

from pathlib import Path
from typing import Any

import pytest

from ai_study_assistant.cli import build_parser, main, run_pipeline
from ai_study_assistant.config import AppConfig, ResolvedLLM
from ai_study_assistant.llm import LLMClient
from ai_study_assistant.llm.client import Message
from ai_study_assistant.parsers import FileReadError, UnknownFormatError
from ai_study_assistant.pipeline import EmptyContentError, StudyNote


class FakeLLMClient:
    """Test-only LLMClient returning canned text."""

    def __init__(self, response: str = "fake note section") -> None:
        self.response = response
        self.calls: list[list[Message]] = []

    def generate(self, messages: list[Message], **overrides: Any) -> str:
        self.calls.append(messages)
        return self.response


def _write_input(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_run_pipeline_end_to_end(tmp_path: Path) -> None:
    """Case 1: full pipeline with injected fake client produces correct note."""
    input_path = _write_input(tmp_path, "hello.md", "# Hello\n\nWorld")
    output_dir = tmp_path / "notes"
    client = FakeLLMClient("Generated section")

    result = run_pipeline(str(input_path), str(output_dir), client=client)

    assert result == output_dir / "hello.md"
    assert result.exists()
    assert "# hello" in result.read_text(encoding="utf-8")
    assert "Generated section" in result.read_text(encoding="utf-8")
    assert isinstance(result, Path)


def test_run_pipeline_returns_expected_output_path(tmp_path: Path) -> None:
    """Case 2: returned path matches output_dir/{stem}.md."""
    input_path = _write_input(tmp_path, "my_doc.txt", "Some content")
    output_dir = tmp_path / "out"
    client = FakeLLMClient()

    result = run_pipeline(str(input_path), str(output_dir), client=client)

    assert result == output_dir / "my_doc.md"


def test_run_pipeline_file_not_found(tmp_path: Path) -> None:
    """Case 3: missing input file raises FileReadError."""
    missing = tmp_path / "missing.md"
    client = FakeLLMClient()

    with pytest.raises(FileReadError):
        run_pipeline(str(missing), str(tmp_path / "out"), client=client)


def test_run_pipeline_unknown_format(tmp_path: Path) -> None:
    """Case 4: unsupported extension raises UnknownFormatError."""
    input_path = _write_input(tmp_path, "data.xyz", "content")
    client = FakeLLMClient()

    with pytest.raises(UnknownFormatError):
        run_pipeline(str(input_path), str(tmp_path / "out"), client=client)


def test_run_pipeline_provider_switch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Case 5: --provider is forwarded to cfg.resolve."""
    input_path = _write_input(tmp_path, "switch.md", "text")
    output_dir = tmp_path / "out"

    resolved = ResolvedLLM(
        base_url="http://example.com",
        api_key="fake",
        model="kimi-model",
        temperature=0.5,
        max_tokens=100,
    )
    cfg = AppConfig(provider="default", providers={})
    resolve_calls: list[str | None] = []

    def fake_resolve(self: AppConfig, name: str | None = None) -> ResolvedLLM:
        resolve_calls.append(name)
        return resolved

    monkeypatch.setattr(AppConfig, "resolve", fake_resolve)

    def fake_load_config(path: str | None = None) -> AppConfig:
        return cfg

    def fake_create_client(resolved: ResolvedLLM) -> LLMClient:
        return FakeLLMClient()

    monkeypatch.setattr("ai_study_assistant.cli.load_config", fake_load_config)
    monkeypatch.setattr("ai_study_assistant.cli.create_client", fake_create_client)

    run_pipeline(str(input_path), str(output_dir), provider="kimi")

    assert resolve_calls == ["kimi"]


def test_build_parser() -> None:
    """Case 6: argparse handles input/output/provider/config."""
    parser = build_parser()
    args = parser.parse_args(["input.md", "-o", "notes", "--provider", "kimi", "--config", "cfg.yml"])

    assert args.input == "input.md"
    assert args.output == "notes"
    assert args.provider == "kimi"
    assert args.config == "cfg.yml"


def test_main_success_returns_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Case 7: main() returns 0 on success and prints the output path."""
    input_path = _write_input(tmp_path, "main.md", "content")
    output_dir = tmp_path / "generated"
    expected_path = output_dir / "main.md"

    def fake_run_pipeline(input_path: str, output_dir: str, *, provider: str | None = None, config_path: str | None = None, client: LLMClient | None = None) -> Path:
        return expected_path

    monkeypatch.setattr("ai_study_assistant.cli.run_pipeline", fake_run_pipeline)

    code = main([str(input_path), "-o", str(output_dir)])

    assert code == 0


def test_main_known_error_returns_one(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Domain errors return exit code 1 with a friendly message."""

    def fake_run_pipeline(*args: Any, **kwargs: Any) -> StudyNote:
        raise EmptyContentError("empty")

    monkeypatch.setattr("ai_study_assistant.cli.run_pipeline", fake_run_pipeline)

    code = main([str(tmp_path / "empty.md"), "-o", str(tmp_path)])

    assert code == 1
    captured = capsys.readouterr()
    assert "错误" in captured.out


def test_main_unknown_error_returns_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Unexpected errors return exit code 2 and print traceback."""

    def fake_run_pipeline(*args: Any, **kwargs: Any) -> StudyNote:
        raise RuntimeError("boom")

    monkeypatch.setattr("ai_study_assistant.cli.run_pipeline", fake_run_pipeline)

    code = main([str(tmp_path / "x.md"), "-o", str(tmp_path)])

    assert code == 2
    captured = capsys.readouterr()
    assert "RuntimeError" in captured.err
