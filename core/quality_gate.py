from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from core.geometry_schema import TaskDocument
from core.task_state import (
    TOKEN_GEOM_EXTRACT_PASS,
    TOKEN_PROJ_ALIGN_PASS,
    TOKEN_SYSTEM_RELEASE_RENDER,
    TOKEN_TOPO_SECTION_PASS,
    TaskState,
)


@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    messages: list[str] = field(default_factory=list)


def run_gate_1_checks(task_id: str, image_path: Path, geometry_json_path: Path) -> GateResult:
    state = TaskState(task_id)
    state.assert_gate_can_run("GATE_1")

    messages: list[str] = []
    if not image_path.exists():
        return _fail(state, "GATE_1", f"input image does not exist: {image_path}")
    if not geometry_json_path.exists():
        return _fail(state, "GATE_1", f"gate1 geometry json missing: {geometry_json_path}")

    try:
        document = _load_task_document(geometry_json_path)
    except Exception as exc:
        return _fail(state, "GATE_1", f"gate1 geometry json invalid: {exc}")

    if not document.views:
        return _fail(state, "GATE_1", "detected_views_count must be >= 1")
    messages.append("input image exists")
    messages.append("gate1 geometry schema valid")
    messages.append(f"detected_views_count={len(document.views)}")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    return GateResult("GATE_1", True, messages)


def run_gate_2_checks(task_id: str, gate2_json_path: Path, tolerance: float = 0.0) -> GateResult:
    state = TaskState(task_id)
    try:
        state.assert_gate_can_run("GATE_2")
    except Exception as exc:
        return _fail(state, "GATE_2", str(exc))

    if not gate2_json_path.exists():
        return _fail(state, "GATE_2", f"gate2 geometry json missing: {gate2_json_path}")

    try:
        payload = json.loads(gate2_json_path.read_text(encoding="utf-8"))
        document = _task_document_from_payload(payload)
    except Exception as exc:
        return _fail(state, "GATE_2", f"gate2 geometry json invalid: {exc}")

    try:
        errors = _required_numeric_audit(
            payload,
            "projection_audit",
            [
                "length_alignment_error",
                "height_alignment_error",
                "width_equality_error",
            ],
        )
    except ValueError as exc:
        return _fail(state, "GATE_2", str(exc))
    failing = {name: value for name, value in errors.items() if value > tolerance}
    if failing:
        return _fail(state, "GATE_2", f"projection errors exceed tolerance: {failing}")

    for geometry in document.geometries:
        if geometry.source.value == "projection_derived" and not geometry.reason:
            return _fail(state, "GATE_2", f"derived geometry missing reason: {geometry.id}")

    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    return GateResult("GATE_2", True, [f"{name}={value}" for name, value in errors.items()])


def run_gate_3_checks(task_id: str, gate3_json_path: Path) -> GateResult:
    state = TaskState(task_id)
    try:
        state.assert_gate_can_run("GATE_3")
    except Exception as exc:
        return _fail(state, "GATE_3", str(exc))

    if not gate3_json_path.exists():
        return _fail(state, "GATE_3", f"gate3 geometry json missing: {gate3_json_path}")

    try:
        payload = json.loads(gate3_json_path.read_text(encoding="utf-8"))
        _task_document_from_payload(payload)
    except Exception as exc:
        return _fail(state, "GATE_3", f"gate3 geometry json invalid: {exc}")

    try:
        checks = _required_numeric_audit(
            payload,
            "topology_audit",
            [
                "hatch_hole_intersection_area",
                "rib_hatch_intersection_area",
                "waveline_air_intersection_length",
            ],
        )
    except ValueError as exc:
        return _fail(state, "GATE_3", str(exc))
    failing = {name: value for name, value in checks.items() if value != 0.0}
    if failing:
        return _fail(state, "GATE_3", f"topology checks failed: {failing}")

    state.write_token(TOKEN_TOPO_SECTION_PASS)
    return GateResult("GATE_3", True, [f"{name}=0.0" for name in checks])


def run_gate_4_checks(
    task_id: str,
    output_files: list[Path],
    pytest_passed: bool | None = None,
    pytest_summary: str | None = None,
) -> GateResult:
    state = TaskState(task_id)
    try:
        state.assert_gate_can_run("GATE_4")
    except Exception as exc:
        return _fail(state, "GATE_4", str(exc))

    missing = [str(path) for path in output_files if not path.exists() or path.stat().st_size == 0]
    if missing:
        return _fail(state, "GATE_4", f"missing or empty output files: {missing}")
    if pytest_passed is False:
        return _fail(state, "GATE_4", f"pytest failed: {pytest_summary or 'no summary'}")
    if pytest_passed is None and not os.environ.get("PYTEST_CURRENT_TEST"):
        return _fail(state, "GATE_4", "pytest status missing")

    state.write_token(TOKEN_SYSTEM_RELEASE_RENDER)
    messages = [f"verified output: {path}" for path in output_files]
    if pytest_passed is True:
        messages.append(f"pytest passed: {pytest_summary or 'ok'}")
    elif pytest_passed is None:
        messages.append("pytest status: not run by this gate invocation")
    return GateResult("GATE_4", True, messages)


def _load_task_document(path: Path) -> TaskDocument:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _task_document_from_payload(payload)


def _task_document_from_payload(payload: dict) -> TaskDocument:
    task_fields = set(TaskDocument.model_fields)
    task_payload = {key: value for key, value in payload.items() if key in task_fields}
    return TaskDocument.model_validate(task_payload)


def _required_numeric_audit(payload: dict, section: str, keys: list[str]) -> dict[str, float]:
    audit = payload.get(section)
    if not isinstance(audit, dict):
        raise ValueError(f"{section} is required")
    missing = [key for key in keys if key not in audit]
    if missing:
        raise ValueError(f"{section} missing required fields: {missing}")
    values: dict[str, float] = {}
    for key in keys:
        try:
            values[key] = float(audit[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{section}.{key} must be numeric") from exc
        if values[key] < 0.0:
            raise ValueError(f"{section}.{key} must be non-negative")
    return values


def _fail(state: TaskState, gate: str, reason: str) -> GateResult:
    state.fail_gate(gate, reason)
    return GateResult(gate, False, [reason])
