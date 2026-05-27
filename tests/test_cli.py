import json
import os
import subprocess
import sys
from pathlib import Path

from core.task_state import TOKEN_GEOM_EXTRACT_PASS, TOKEN_PROJ_ALIGN_PASS, TOKEN_TOPO_SECTION_PASS, TaskState
from tests.test_schema import minimal_task


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_cli_gate_2_runs_with_geometry_json(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    task_id = "cli_gate2_case"
    state = TaskState(task_id)
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    payload = minimal_task() | {
        "projection_audit": {
            "length_alignment_error": 0,
            "height_alignment_error": 0,
            "width_equality_error": 0,
        }
    }
    geometry = tmp_path / "gate2.json"
    geometry.write_text(json.dumps(payload), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_task.py"),
            "--task-id",
            task_id,
            "--geometry-json",
            str(geometry),
            "--gate",
            "GATE_2",
        ],
        cwd=tmp_path,
        env=os.environ | {"PYTHONPATH": str(PROJECT_ROOT)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "GATE_2 passed=True" in completed.stdout


def test_cli_gate_4_renders_after_tokens(tmp_path: Path, monkeypatch):
    from tests.test_svg_renderer import render_task

    monkeypatch.chdir(tmp_path)
    task_id = "cli_gate4_case"
    state = TaskState(task_id)
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)
    geometry = tmp_path / "gate4.json"
    geometry.write_text(json.dumps(render_task().model_dump(mode="json")), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_task.py"),
            "--task-id",
            task_id,
            "--geometry-json",
            str(geometry),
            "--gate",
            "GATE_4",
        ],
        cwd=tmp_path,
        env=os.environ | {"PYTHONPATH": str(PROJECT_ROOT)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "released=True" in completed.stdout


def test_cli_gate_1_rejects_geometry_json_without_rendering(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    task_id = "cli_gate1_geometry_case"
    geometry = tmp_path / "gate1.json"
    geometry.write_text(json.dumps(minimal_task()), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_task.py"),
            "--task-id",
            task_id,
            "--geometry-json",
            str(geometry),
            "--gate",
            "GATE_1",
        ],
        cwd=tmp_path,
        env=os.environ | {"PYTHONPATH": str(PROJECT_ROOT)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "GATE_1 requires --image input" in completed.stderr
    assert not (tmp_path / "result/cli_gate1_geometry_case.svg").exists()


def test_cli_verify_manifest(tmp_path: Path, monkeypatch):
    from core.task_runner import run_from_geometry
    from tests.test_svg_renderer import render_task

    monkeypatch.chdir(tmp_path)
    task_id = "cli_manifest_case"
    state = TaskState(task_id)
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps(render_task().model_dump(mode="json")), encoding="utf-8")
    run_from_geometry(task_id, geometry, output_root=Path("result"))
    manifest = tmp_path / "result/cli_manifest_case/cli_manifest_case_release_manifest.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_task.py"),
            "--verify-manifest",
            str(manifest),
        ],
        cwd=tmp_path,
        env=os.environ | {"PYTHONPATH": str(PROJECT_ROOT)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "manifest_verified=True task_id=cli_manifest_case" in completed.stdout


def test_cli_gate_4_can_write_to_explicit_package_directory(tmp_path: Path, monkeypatch):
    from tests.test_svg_renderer import render_task

    monkeypatch.chdir(tmp_path)
    task_id = "cli_package_dir_case"
    state = TaskState(task_id)
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)
    geometry = tmp_path / "gate4.json"
    geometry.write_text(json.dumps(render_task().model_dump(mode="json")), encoding="utf-8")
    package_dir = Path("result/1 (1)/task25/final")
    review_mark = tmp_path / "work/review_marks/review.md"
    review_mark.parent.mkdir(parents=True)
    review_mark.write_text("review", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "run_task.py"),
            "--task-id",
            task_id,
            "--geometry-json",
            str(geometry),
            "--gate",
            "GATE_4",
            "--output-basename",
            "1 (1)_task25_final",
            "--output-package-dir",
            str(package_dir),
            "--review-mark",
            str(review_mark),
        ],
        cwd=tmp_path,
        env=os.environ | {"PYTHONPATH": str(PROJECT_ROOT)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0
    assert (tmp_path / package_dir / "1 (1)_task25_final.svg").exists()
    manifest = tmp_path / package_dir / "1 (1)_task25_final_release_manifest.json"
    assert manifest.exists()
    assert json.loads(manifest.read_text(encoding="utf-8"))["review_mark"]["exists"] is True
