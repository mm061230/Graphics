from pathlib import Path

import pytest

from core.task_state import (
    GateOrderError,
    TOKEN_GEOM_EXTRACT_PASS,
    TOKEN_PROJ_ALIGN_PASS,
    TaskState,
)


def test_gate_order_blocks_skipping(tmp_path: Path):
    state = TaskState("order_case", root=tmp_path)
    with pytest.raises(GateOrderError):
        state.assert_gate_can_run("GATE_2")


def test_token_allows_next_gate(tmp_path: Path):
    state = TaskState("token_case", root=tmp_path)
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.assert_gate_can_run("GATE_2")


def test_gate_three_requires_gate_two_token(tmp_path: Path):
    state = TaskState("gate_three_case", root=tmp_path)
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    with pytest.raises(GateOrderError):
        state.assert_gate_can_run("GATE_3")
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.assert_gate_can_run("GATE_3")


def test_fail_gate_writes_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    state = TaskState("failure_case", root=Path("work/state"))
    report = state.fail_gate("GATE_1", "missing input image")
    assert report.exists()
    assert "missing input image" in report.read_text(encoding="utf-8")

