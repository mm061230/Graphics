import json
from pathlib import Path

import pytest

from core.release_manifest import (
    assert_release_complete,
    build_release_manifest,
    verify_release_manifest,
    write_release_manifest,
)
from core.task_runner import run_from_geometry
from core.task_state import (
    TOKEN_GEOM_EXTRACT_PASS,
    TOKEN_PROJ_ALIGN_PASS,
    TOKEN_SYSTEM_RELEASE_RENDER,
    TOKEN_TOPO_SECTION_PASS,
    TaskState,
)
from tests.test_svg_renderer import render_task


def test_run_from_geometry_writes_complete_release_manifest(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps(render_task().model_dump(mode="json")), encoding="utf-8")
    state = TaskState("manifest_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)

    result = run_from_geometry("manifest_case", geometry, output_root=Path("result"))

    manifest_path = tmp_path / "result/manifest_case/manifest_case_release_manifest.json"
    assert manifest_path.exists()
    assert manifest_path.resolve() in {path.resolve() for path in result.outputs}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["release_complete"] is True
    assert manifest["geometry_schema_valid"] is True
    assert manifest["required_tokens"]["TOKEN_SYSTEM_RELEASE_RENDER"]["present"] is True
    assert manifest["required_outputs"][".png"]["sha256"]
    assert_release_complete(manifest)


def test_release_manifest_detects_missing_release_token(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps(render_task().model_dump(mode="json")), encoding="utf-8")
    state = TaskState("missing_token_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)
    result_root = tmp_path / "result"
    result_root.mkdir()
    for suffix in [".svg", ".dxf", ".png", ".pdf", "_audit_report.md"]:
        (result_root / f"missing_token_case{suffix}").write_text("artifact", encoding="utf-8")

    manifest = build_release_manifest("missing_token_case", geometry, output_root=result_root)

    assert manifest["release_complete"] is False
    assert "TOKEN_SYSTEM_RELEASE_RENDER" in manifest["missing_tokens"]
    with pytest.raises(ValueError):
        assert_release_complete(manifest)


def test_release_manifest_detects_missing_required_output(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps(render_task().model_dump(mode="json")), encoding="utf-8")
    state = TaskState("missing_output_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)
    state.write_token(TOKEN_SYSTEM_RELEASE_RENDER)
    result_root = tmp_path / "result"
    result_root.mkdir()
    for suffix in [".svg", ".dxf", ".pdf", "_audit_report.md"]:
        (result_root / f"missing_output_case{suffix}").write_text("artifact", encoding="utf-8")

    manifest = build_release_manifest("missing_output_case", geometry, output_root=result_root)

    assert manifest["release_complete"] is False
    assert ".png" in manifest["missing_outputs"]
    with pytest.raises(ValueError):
        assert_release_complete(manifest)


def test_verify_release_manifest_passes_for_unchanged_release(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps(render_task().model_dump(mode="json")), encoding="utf-8")
    state = TaskState("verify_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)

    run_from_geometry("verify_case", geometry, output_root=Path("result"))
    manifest_path = tmp_path / "result/verify_case/verify_case_release_manifest.json"

    manifest = verify_release_manifest(manifest_path)

    assert manifest["release_complete"] is True


def test_verify_release_manifest_detects_tampered_output(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps(render_task().model_dump(mode="json")), encoding="utf-8")
    state = TaskState("tampered_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)

    run_from_geometry("tampered_case", geometry, output_root=Path("result"))
    manifest_path = tmp_path / "result/tampered_case/tampered_case_release_manifest.json"
    (tmp_path / "result/tampered_case/tampered_case.png").write_bytes(b"tampered")

    with pytest.raises(ValueError, match="required_outputs\\.\\.png sha256 changed"):
        verify_release_manifest(manifest_path)


def test_verify_release_manifest_detects_missing_review_mark(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps(render_task().model_dump(mode="json")), encoding="utf-8")
    state = TaskState("review_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)
    state.write_token(TOKEN_SYSTEM_RELEASE_RENDER)
    result_root = tmp_path / "result"
    result_root.mkdir()
    for suffix in [".svg", ".dxf", ".png", ".pdf", "_audit_report.md"]:
        (result_root / f"review_case{suffix}").write_text("artifact", encoding="utf-8")
    review_mark = tmp_path / "work/review_marks/review_case.md"
    review_mark.parent.mkdir(parents=True)
    review_mark.write_text("review", encoding="utf-8")
    manifest_path = write_release_manifest(
        "review_case",
        geometry,
        output_root=result_root,
        review_mark=review_mark,
    )
    review_mark.unlink()

    with pytest.raises(ValueError, match="review_mark missing"):
        verify_release_manifest(manifest_path)


def test_run_from_geometry_binds_review_mark_in_manifest(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    geometry = tmp_path / "geometry.json"
    geometry.write_text(json.dumps(render_task().model_dump(mode="json")), encoding="utf-8")
    review_mark = tmp_path / "work/review_marks/review_case.md"
    review_mark.parent.mkdir(parents=True)
    review_mark.write_text("review", encoding="utf-8")
    state = TaskState("bound_review_case")
    state.write_token(TOKEN_GEOM_EXTRACT_PASS)
    state.write_token(TOKEN_PROJ_ALIGN_PASS)
    state.write_token(TOKEN_TOPO_SECTION_PASS)

    run_from_geometry("bound_review_case", geometry, output_root=Path("result"), review_mark=review_mark)

    manifest_path = tmp_path / "result/bound_review_case/bound_review_case_release_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["review_mark"]["exists"] is True
    assert manifest["review_mark"]["sha256"]
