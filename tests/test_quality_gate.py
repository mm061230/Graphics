import json
from pathlib import Path

from core.quality_gate import (
    run_gate_1_checks,
    run_gate_2_checks,
    run_gate_3_checks,
    run_gate_4_checks,
)
from core.task_state import (
    TOKEN_GEOM_EXTRACT_PASS,
    TOKEN_PROJ_ALIGN_PASS,
    TOKEN_SYSTEM_RELEASE_RENDER,
    TOKEN_TOPO_SECTION_PASS,
    TaskState,
)
from tests.test_schema import minimal_task


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_gate_1_passes_and_writes_token(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    image = tmp_path / "input.png"
    image.write_bytes(b"fake image bytes")
    geometry = write_json(tmp_path / "gate1.json", minimal_task())

    result = run_gate_1_checks("gate1_case", image, geometry)

    assert result.passed
    assert TaskState("gate1_case").has_token(TOKEN_GEOM_EXTRACT_PASS)


def test_gate_1_missing_image_fails(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    geometry = write_json(tmp_path / "gate1.json", minimal_task())

    result = run_gate_1_checks("gate1_missing_image", tmp_path / "missing.png", geometry)

    assert not result.passed
    assert Path("work/audit_logs/gate1_missing_image_gate_1_failed.md").exists()


def test_gate_2_requires_gate_1_token(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = minimal_task() | {
        "projection_audit": {
            "length_alignment_error": 0.0,
            "height_alignment_error": 0.0,
            "width_equality_error": 0.0,
        }
    }
    geometry = write_json(tmp_path / "gate2.json", payload)

    result = run_gate_2_checks("gate2_no_token", geometry)

    assert not result.passed


def test_gate_2_passes_with_projection_errors_zero(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    state = TaskState("gate2_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    payload = minimal_task() | {
        "projection_audit": {
            "length_alignment_error": 0.0,
            "height_alignment_error": 0.0,
            "width_equality_error": 0.0,
        }
    }
    geometry = write_json(tmp_path / "gate2.json", payload)

    result = run_gate_2_checks("gate2_case", geometry)

    assert result.passed
    assert state.has_token(TOKEN_PROJ_ALIGN_PASS)


def test_gate_2_requires_explicit_projection_audit(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    state = TaskState("gate2_missing_audit")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    geometry = write_json(tmp_path / "gate2.json", minimal_task())

    result = run_gate_2_checks("gate2_missing_audit", geometry)

    assert not result.passed
    assert "projection_audit is required" in result.messages[0]
    assert not state.has_token(TOKEN_PROJ_ALIGN_PASS)


def test_gate_2_requires_complete_projection_audit(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    state = TaskState("gate2_incomplete_audit")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    payload = minimal_task() | {"projection_audit": {"length_alignment_error": 0.0}}
    geometry = write_json(tmp_path / "gate2.json", payload)

    result = run_gate_2_checks("gate2_incomplete_audit", geometry)

    assert not result.passed
    assert "projection_audit missing required fields" in result.messages[0]
    assert not state.has_token(TOKEN_PROJ_ALIGN_PASS)


def test_gate_2_rejects_negative_projection_audit_value(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    state = TaskState("gate2_negative_audit")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    payload = minimal_task() | {
        "projection_audit": {
            "length_alignment_error": -1.0,
            "height_alignment_error": 0.0,
            "width_equality_error": 0.0,
        }
    }
    geometry = write_json(tmp_path / "gate2.json", payload)

    result = run_gate_2_checks("gate2_negative_audit", geometry)

    assert not result.passed
    assert "projection_audit.length_alignment_error must be non-negative" in result.messages[0]
    assert not state.has_token(TOKEN_PROJ_ALIGN_PASS)


def test_gate_3_fails_nonzero_topology(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    state = TaskState("gate3_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    payload = minimal_task() | {
        "topology_audit": {
            "hatch_hole_intersection_area": 1.0,
            "rib_hatch_intersection_area": 0.0,
            "waveline_air_intersection_length": 0.0,
        }
    }
    geometry = write_json(tmp_path / "gate3.json", payload)

    result = run_gate_3_checks("gate3_case", geometry)

    assert not result.passed


def test_gate_3_requires_explicit_topology_audit(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    state = TaskState("gate3_missing_audit")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    geometry = write_json(tmp_path / "gate3.json", minimal_task())

    result = run_gate_3_checks("gate3_missing_audit", geometry)

    assert not result.passed
    assert "topology_audit is required" in result.messages[0]
    assert not state.has_token(TOKEN_TOPO_SECTION_PASS)


def test_gate_4_release_requires_outputs(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    state = TaskState("gate4_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)
    output = tmp_path / "answer.svg"
    output.write_text("<svg />", encoding="utf-8")

    result = run_gate_4_checks("gate4_case", [output])

    assert result.passed
    assert state.has_token(TOKEN_SYSTEM_RELEASE_RENDER)


def test_gate_4_requires_pytest_status_outside_pytest_harness(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    state = TaskState("gate4_missing_pytest_status")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)
    output = tmp_path / "answer.svg"
    output.write_text("<svg />", encoding="utf-8")

    result = run_gate_4_checks("gate4_missing_pytest_status", [output])

    assert not result.passed
    assert "pytest status missing" in result.messages[0]
    assert not state.has_token(TOKEN_SYSTEM_RELEASE_RENDER)
