from __future__ import annotations

import os
from typing import Dict


class MockLLMProvider:
    """Deterministic provider for local demos and unit tests."""

    def complete(self, system: str, user: str, *, temperature: float = 0.2) -> str:
        sys_low = system.lower()
        if "planner" in sys_low:
            return (
                "Milestones:\n"
                "1. Clarify project goal and measurable success criteria.\n"
                "2. Scan existing files, data, tests and constraints.\n"
                "3. Build a staged implementation plan with checkpoints.\n"
                "4. Generate artifacts, run evaluation, and record risks.\n"
                "5. Produce a final report with next actions.\n"
            )
        if "evaluator" in sys_low:
            return (
                "Evaluation summary:\n"
                "- Repository/static checks completed where available.\n"
                "- Missing tests and data assumptions were flagged.\n"
                "- Next step: connect real model/API and replace mock scoring with task-specific metrics.\n"
            )
        if "reviewer" in sys_low:
            return (
                "Review:\n"
                "The workflow is structurally complete. It has role separation, tool calls, checkpoints, "
                "artifacts and evaluation logs. Production hardening should add stronger sandboxing, "
                "secret redaction, CI integration and human approval before file modifications."
            )
        return (
            "Normalized requirement:\n"
            "Build a multi-agent workflow that decomposes the task, invokes tools, records evidence, "
            "generates artifacts, evaluates outputs and writes an auditable report."
        )


class OpenAIProvider:
    """Optional real provider. Falls back only if openai package and API key are available."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("AGENT_MODEL", "gpt-4.1-mini")
        try:
            from openai import OpenAI  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("Install openai package or use MockLLMProvider.") from exc
        self.client = OpenAI()

    def complete(self, system: str, user: str, *, temperature: float = 0.2) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""


def build_provider():
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIProvider()
    return MockLLMProvider()
