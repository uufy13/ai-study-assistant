"""Command-line entry point for ai-study-assistant."""

import argparse
import traceback
from pathlib import Path

from ai_study_assistant.config import ConfigError, load_config
from ai_study_assistant.llm import LLMClient, LLMError, create_client
from ai_study_assistant.parsers import ParserError, parse_file
from ai_study_assistant.pipeline import PipelineError, StudyPipeline
from ai_study_assistant.storage import StorageError, save


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="ai-study-assistant",
        description="使用 AI 将学习资料整理为结构化笔记。",
    )
    parser.add_argument(
        "input",
        help="输入文件路径（.md/.txt 等）。",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="./output",
        help="输出目录（默认：./output）。",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="覆盖默认 LLM provider。",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="配置文件路径。",
    )
    return parser


def run_pipeline(
    input_path: str,
    output_dir: str,
    *,
    provider: str | None = None,
    config_path: str | None = None,
    client: LLMClient | None = None,
) -> Path:
    """Run the full study pipeline and return the path of the saved note.

    If ``client`` is provided it is used directly (useful for tests); otherwise
    a client is built from the resolved configuration.
    """
    if client is None:
        cfg = load_config(config_path)
        resolved = cfg.resolve(name=provider)
        client = create_client(resolved)

    document = parse_file(input_path)
    note = StudyPipeline(client).run(document)
    return save(note, Path(output_dir))


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run the pipeline and return an exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        output_path = run_pipeline(
            args.input,
            args.output,
            provider=args.provider,
            config_path=args.config,
        )
    except (ConfigError, ParserError, LLMError, PipelineError, StorageError) as exc:
        print(f"错误：{exc}")
        return 1
    except Exception:  # noqa: BLE001 - CLI catches unknown errors for user-friendly exit code 2
        traceback.print_exc()
        return 2

    print(f"已生成笔记：{output_path}")
    return 0
