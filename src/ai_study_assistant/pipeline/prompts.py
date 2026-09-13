"""Prompt construction for the study pipeline."""

from ai_study_assistant.llm import Message

SYSTEM_PROMPT: str = """你是一个专业的学习助手。请根据用户提供的学习材料生成结构化 Markdown 笔记。

要求：
- 使用标题、列表、代码块等 Markdown 元素组织内容。
- 客观准确地总结材料，不编造材料以外的信息。
- 输出语言为中文。
"""


def build_messages(chunk_text: str) -> list[Message]:
    """Build the system/user message pair for a single chunk."""
    return [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=f"请根据以下学习材料生成学习笔记：\n\n{chunk_text}"),
    ]
