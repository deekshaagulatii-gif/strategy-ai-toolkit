import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class FakeLLM:
    """Stands in for the AI model so tests are free, fast and repeatable."""

    def __init__(self, reply: str):
        self.reply = reply
        self.prompts: list[str] = []

    def complete(self, prompt: str, max_tokens: int = 2000) -> str:
        self.prompts.append(prompt)
        return self.reply


@pytest.fixture
def fake_llm():
    return FakeLLM
