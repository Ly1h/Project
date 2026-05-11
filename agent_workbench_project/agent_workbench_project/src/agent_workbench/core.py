from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol


class LLMProvider(Protocol):
    def complete(self, system: str, user: str, *, temperature: float = 0.2) -> str:
        """Return a model response."""


@dataclass
class AgentMessage:
    role: str
    content: str
    ts: float = field(default_factory=time.time)


@dataclass
class AgentState:
    run_id: str
    workspace: Path
    goal: str
    phase: str = "created"
    messages: List[AgentMessage] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(AgentMessage(role=role, content=content))


@dataclass
class ToolResult:
    ok: bool
    output: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., ToolResult]] = {}

    def register(self, name: str, fn: Callable[..., ToolResult]) -> None:
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        self._tools[name] = fn

    def call(self, name: str, **kwargs: Any) -> ToolResult:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name](**kwargs)

    def names(self) -> List[str]:
        return sorted(self._tools)


class MemoryStore:
    """Small SQLite-backed memory for audit logs, checkpoints and artifacts."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    run_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )

    def log(self, run_id: str, phase: str, event_type: str, payload: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), run_id, phase, event_type, json.dumps(payload, ensure_ascii=False), time.time()),
            )

    def checkpoint(self, state: AgentState) -> None:
        payload = {
            "run_id": state.run_id,
            "workspace": str(state.workspace),
            "goal": state.goal,
            "phase": state.phase,
            "messages": [asdict(m) for m in state.messages],
            "artifacts": state.artifacts,
            "metrics": state.metrics,
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO checkpoints(run_id, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at
                """,
                (state.run_id, json.dumps(payload, ensure_ascii=False), time.time()),
            )

    def load_checkpoint(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.execute("SELECT payload FROM checkpoints WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if not row:
                return None
            return json.loads(row[0])


@dataclass
class Agent:
    name: str
    system_prompt: str
    provider: LLMProvider
    memory: MemoryStore

    def run(self, state: AgentState, instruction: str, *, temperature: float = 0.2) -> str:
        user = (
            f"Goal:\n{state.goal}\n\n"
            f"Current phase: {state.phase}\n"
            f"Known artifacts: {json.dumps(state.artifacts, ensure_ascii=False, indent=2)}\n\n"
            f"Instruction:\n{instruction}"
        )
        self.memory.log(state.run_id, state.phase, f"{self.name}.input", {"instruction": instruction})
        response = self.provider.complete(self.system_prompt, user, temperature=temperature)
        state.add_message(self.name, response)
        self.memory.log(state.run_id, state.phase, f"{self.name}.output", {"response": response})
        return response
