from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


TOKEN_GEOM_EXTRACT_PASS = "TOKEN_GEOM_EXTRACT_PASS"
TOKEN_PROJ_ALIGN_PASS = "TOKEN_PROJ_ALIGN_PASS"
TOKEN_TOPO_SECTION_PASS = "TOKEN_TOPO_SECTION_PASS"
TOKEN_SYSTEM_RELEASE_RENDER = "TOKEN_SYSTEM_RELEASE_RENDER"

GATE_PREREQUISITES = {
    "GATE_1": None,
    "GATE_2": TOKEN_GEOM_EXTRACT_PASS,
    "GATE_3": TOKEN_PROJ_ALIGN_PASS,
    "GATE_4": TOKEN_TOPO_SECTION_PASS,
}


class GateOrderError(RuntimeError):
    """Raised when a gate is attempted before its prerequisite token exists."""


@dataclass(frozen=True)
class TaskState:
    task_id: str
    root: Path = Path("work/state")
    audit_root: Path = Path("work/audit_logs")

    _SAFE_TASK_ID = re.compile(r'^[A-Za-z0-9_-]+$')

    def __post_init__(self) -> None:
        if not self._SAFE_TASK_ID.match(self.task_id):
            raise ValueError(f"invalid task_id: {self.task_id!r}")

    @property
    def task_dir(self) -> Path:
        return self.root / self.task_id

    @property
    def state_file(self) -> Path:
        return self.task_dir / "state.json"

    def ensure(self) -> None:
        self.task_dir.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self._write_state({"task_id": self.task_id, "tokens": [], "failures": []})

    def token_path(self, token: str) -> Path:
        return self.task_dir / token

    def has_token(self, token: str) -> bool:
        return self.token_path(token).exists()

    def write_token(self, token: str) -> Path:
        self.ensure()
        token_path = self.token_path(token)
        token_path.write_text(self._timestamp(), encoding="utf-8")
        state = self._read_state()
        if token not in state["tokens"]:
            state["tokens"].append(token)
        self._write_state(state)
        return token_path

    def assert_gate_can_run(self, gate: str) -> None:
        self.ensure()
        if gate not in GATE_PREREQUISITES:
            raise ValueError(f"unknown gate: {gate}")
        required_token = GATE_PREREQUISITES[gate]
        if required_token and not self.has_token(required_token):
            raise GateOrderError(f"{gate} requires {required_token}")

    def fail_gate(self, gate: str, reason: str) -> Path:
        self.ensure()
        state = self._read_state()
        failure = {"gate": gate, "reason": reason, "timestamp": self._timestamp()}
        state["failures"].append(failure)
        self._write_state(state)
        report = self.audit_root / f"{self.task_id}_{gate.lower()}_failed.md"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            f"# {gate} Failed\n\n"
            f"- Task: `{self.task_id}`\n"
            f"- Time: `{failure['timestamp']}`\n"
            f"- Reason: {reason}\n",
            encoding="utf-8",
        )
        return report

    def _read_state(self) -> dict:
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def _write_state(self, state: dict) -> None:
        self.task_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()
