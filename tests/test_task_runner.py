import json
from pathlib import Path

from core.task_runner import run_image_gate_1
from core.task_runner import run_from_geometry
from core.task_state import (
    TOKEN_GEOM_EXTRACT_PASS,
    TOKEN_PROJ_ALIGN_PASS,
    TOKEN_TOPO_SECTION_PASS,
    TaskState,
)
from tests.test_gate_1_input import create_sample_image
from tests.test_svg_renderer import render_task


def test_run_from_geometry_releases_full_output_package(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = render_task().model_dump(mode="json")
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps(payload), encoding="utf-8")
    state = TaskState("runner_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)

    result = run_from_geometry("runner_case", geometry, output_root=Path("result"))

    assert result.released
    assert (tmp_path / "result/runner_case/runner_case.svg").exists()
    assert (tmp_path / "result/runner_case/runner_case.dxf").exists()
    assert (tmp_path / "result/runner_case/runner_case.png").exists()
    assert (tmp_path / "result/runner_case/runner_case.pdf").exists()
    assert (tmp_path / "result/runner_case/runner_case_release_manifest.json").exists()
    assert result.report.exists()


def test_run_from_geometry_can_preserve_source_basename(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = render_task().model_dump(mode="json")
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps(payload), encoding="utf-8")
    state = TaskState("source_name_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)

    result = run_from_geometry(
        "source_name_case",
        geometry,
        output_root=Path("result"),
        output_basename="1 (1)",
    )

    assert result.released
    assert (tmp_path / "result/1 (1)/1 (1).svg").exists()
    assert (tmp_path / "result/1 (1)/1 (1).png").exists()


def test_run_from_geometry_can_write_to_explicit_package_directory(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload = render_task().model_dump(mode="json")
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps(payload), encoding="utf-8")
    state = TaskState("explicit_package_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)

    result = run_from_geometry(
        "explicit_package_case",
        geometry,
        output_root=Path("result"),
        output_basename="1 (1)_task25_final",
        output_package_dir=Path("result/1 (1)/task25/final"),
    )

    assert result.released
    assert (tmp_path / "result/1 (1)/task25/final/1 (1)_task25_final.svg").exists()
    assert (
        tmp_path
        / "result/1 (1)/task25/final/1 (1)_task25_final_release_manifest.json"
    ).exists()


def test_run_from_geometry_keeps_final_outputs_blocked_when_release_tests_fail(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    payload = render_task().model_dump(mode="json")
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps(payload), encoding="utf-8")
    state = TaskState("failed_release_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)
    monkeypatch.setattr(
        "core.task_runner._run_release_tests",
        lambda run_tests: (False, "simulated pytest failure"),
    )

    result = run_from_geometry("failed_release_case", geometry, output_root=Path("result"))

    assert not result.released
    assert result.outputs == []
    assert not (tmp_path / "result/failed_release_case/failed_release_case.svg").exists()
    assert not (tmp_path / "result/failed_release_case/failed_release_case_release_manifest.json").exists()


def test_run_image_gate_1_writes_candidate_json_and_token(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    image = create_sample_image(tmp_path / "sample.png")

    gate1_json = run_image_gate_1("image_runner_case", image)

    assert gate1_json.exists()
    assert TaskState("image_runner_case").has_token(TOKEN_GEOM_EXTRACT_PASS)
