from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from core.geometry_schema import TaskDocument
from core.quality_gate import run_gate_1_checks, run_gate_2_checks, run_gate_3_checks, run_gate_4_checks
from core.release_manifest import write_release_manifest
from core.task_state import TOKEN_SYSTEM_RELEASE_RENDER, TaskState
from core.vision_pipeline import write_gate1_candidate_json

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class TaskRunResult:
    task_id: str
    released: bool
    outputs: list[Path]
    report: Path


def run_from_geometry(
    task_id: str,
    geometry_json: Path,
    output_root: Path = Path("result"),
    output_basename: str | None = None,
    output_package_dir: Path | None = None,
    review_mark: Path | None = None,
    run_tests: bool = True,
) -> TaskRunResult:
    payload = json.loads(geometry_json.read_text(encoding="utf-8"))
    task = TaskDocument.model_validate(
        {key: value for key, value in payload.items() if key in TaskDocument.model_fields}
    )
    state = TaskState(task_id)
    state.assert_gate_can_run("GATE_4")

    output_stem = output_basename or task_id
    package_dir = output_package_dir or output_root / output_stem
    svg_path = package_dir / f"{output_stem}.svg"
    dxf_path = package_dir / f"{output_stem}.dxf"
    png_path = package_dir / f"{output_stem}.png"
    pdf_path = package_dir / f"{output_stem}.pdf"
    report = package_dir / f"{output_stem}_audit_report.md"
    stage_root = Path(tempfile.mkdtemp(prefix=f"diagram_release_{_safe_path_name(task_id)}_"))
    stage_dir = stage_root / output_stem
    stage_svg_path = stage_dir / f"{output_stem}.svg"
    stage_dxf_path = stage_dir / f"{output_stem}.dxf"
    stage_png_path = stage_dir / f"{output_stem}.png"
    stage_pdf_path = stage_dir / f"{output_stem}.pdf"
    stage_report = stage_dir / f"{output_stem}_audit_report.md"
    from core.renderers.dxf_renderer import render_dxf
    from core.renderers.export_converter import svg_to_pdf, svg_to_png
    from core.renderers.svg_renderer import render_svg

    render_svg(task, stage_svg_path)
    render_dxf(task, stage_dxf_path)
    svg_to_png(stage_svg_path, stage_png_path, output_width=1200)
    svg_to_pdf(stage_svg_path, stage_pdf_path)

    pytest_passed, pytest_summary = _run_release_tests(run_tests)
    preflight = _write_report(
        task_id,
        stage_report,
        [],
        output_files=[stage_svg_path, stage_dxf_path, stage_png_path, stage_pdf_path],
        pytest_summary=pytest_summary,
        released=False,
    )
    result = run_gate_4_checks(
        task_id,
        [stage_svg_path, stage_dxf_path, stage_png_path, stage_pdf_path, preflight],
        pytest_passed=pytest_passed,
        pytest_summary=pytest_summary,
    )
    if not result.passed:
        _cleanup_stage_dir(stage_dir, stage_root)
        return TaskRunResult(task_id=task_id, released=False, outputs=[], report=preflight)

    _copy_release_files(
        [
            (stage_svg_path, svg_path),
            (stage_dxf_path, dxf_path),
            (stage_png_path, png_path),
            (stage_pdf_path, pdf_path),
        ]
    )
    report = _write_report(
        task_id,
        report,
        [result],
        output_files=[svg_path, dxf_path, png_path, pdf_path],
        pytest_summary=pytest_summary,
        released=state.has_token(TOKEN_SYSTEM_RELEASE_RENDER),
    )
    manifest_path = write_release_manifest(
        task_id,
        geometry_json,
        output_root=package_dir,
        output_basename=output_stem,
        review_mark=review_mark,
    )
    _cleanup_stage_dir(stage_dir, stage_root)
    return TaskRunResult(
        task_id=task_id,
        released=state.has_token(TOKEN_SYSTEM_RELEASE_RENDER),
        outputs=[svg_path, dxf_path, png_path, pdf_path, manifest_path],
        report=report,
    )


def _copy_release_files(pairs: list[tuple[Path, Path]]) -> None:
    for source, destination in pairs:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _cleanup_stage_dir(stage_dir: Path, staging_root: Path) -> None:
    release_staging_root = staging_root.resolve()
    resolved_stage = stage_dir.resolve()
    if release_staging_root not in resolved_stage.parents:
        raise ValueError(f"refusing to clean stage outside release staging root: {stage_dir}")
    for attempt in range(3):
        try:
            shutil.rmtree(resolved_stage, onerror=_make_writable_and_retry)
            break
        except FileNotFoundError:
            break
        except OSError:
            if attempt == 2:
                raise
            time.sleep(0.1)
    parent = resolved_stage.parent
    while release_staging_root == parent or release_staging_root in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            break
        if parent == release_staging_root:
            break
        parent = parent.parent


def _make_writable_and_retry(function, path, _exc_info) -> None:
    os.chmod(path, stat.S_IWRITE)
    function(path)


def _safe_path_name(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value)


def run_image_gate_1(
    task_id: str,
    image_path: Path,
    gate1_json: Path | None = None,
) -> Path:
    gate1_json = gate1_json or write_gate1_candidate_json(image_path, task_id)
    result = run_gate_1_checks(task_id, image_path, gate1_json)
    if not result.passed:
        raise RuntimeError("; ".join(result.messages))
    return gate1_json


def _run_release_tests(run_tests: bool) -> tuple[bool | None, str]:
    if not run_tests:
        return None, "disabled by caller"
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return None, "skipped inside pytest harness"
    env = os.environ | {"PYTHONPATH": str(PROJECT_ROOT)}
    completed = subprocess.run(
        [sys.executable, "-m", "pytest"],
        text=True,
        capture_output=True,
        check=False,
        cwd=PROJECT_ROOT,
        env=env,
    )
    summary = (completed.stdout + completed.stderr).strip().splitlines()
    return completed.returncode == 0, summary[-1] if summary else "no pytest output"


def _write_report(
    task_id: str,
    report_path: Path,
    gate_results,
    output_files: list[Path] | None = None,
    pytest_summary: str | None = None,
    released: bool = False,
) -> Path:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_files = output_files or []
    lines = [
        f"# Audit Report: {task_id}",
        "",
        "## Input Quality",
        "- Status: recorded by GATE 1 artifacts.",
        "",
        "## Requirement Recognition",
        "- Status: structured requirement reader output is recorded when available.",
        "",
        "## Geometry Extraction",
        "- Status: geometry JSON schema validation is enforced before release.",
        "",
        "## Projection Audit",
        "- Status: projection token is required before GATE 4.",
        "",
        "## Topology Audit",
        "- Status: topology token is required before GATE 4.",
        "",
        "## Output Files",
    ]
    lines.extend(f"- {path}" for path in output_files)
    lines.extend(
        [
            "",
            "## Unresolved Uncertainty",
            "- See task JSON `uncertain_fields` and failed gate logs.",
            "",
            "## Release Tests",
            f"- {pytest_summary or 'not run'}",
            "",
            "## Gate Results",
            f"- released={released}",
            "",
        ]
    )
    for result in gate_results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"## {result.gate}: {status}")
        lines.extend(f"- {message}" for message in result.messages)
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
