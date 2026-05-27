from __future__ import annotations

import hashlib
import json
from pathlib import Path

from core.geometry_schema import TaskDocument
from core.task_state import (
    TOKEN_GEOM_EXTRACT_PASS,
    TOKEN_PROJ_ALIGN_PASS,
    TOKEN_SYSTEM_RELEASE_RENDER,
    TOKEN_TOPO_SECTION_PASS,
    TaskState,
)


REQUIRED_RELEASE_TOKENS = [
    TOKEN_GEOM_EXTRACT_PASS,
    TOKEN_PROJ_ALIGN_PASS,
    TOKEN_TOPO_SECTION_PASS,
    TOKEN_SYSTEM_RELEASE_RENDER,
]

REQUIRED_RELEASE_SUFFIXES = [".svg", ".dxf", ".png", ".pdf", "_audit_report.md"]


def write_release_manifest(
    task_id: str,
    geometry_json: Path,
    output_root: Path = Path("result"),
    output_basename: str | None = None,
    review_mark: Path | None = None,
    state_root: Path = Path("work/state"),
) -> Path:
    output_stem = output_basename or task_id
    output_path = output_root / f"{output_stem}_release_manifest.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_release_manifest(
        task_id=task_id,
        geometry_json=geometry_json,
        output_root=output_root,
        output_basename=output_basename,
        review_mark=review_mark,
        state_root=state_root,
    )
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def build_release_manifest(
    task_id: str,
    geometry_json: Path,
    output_root: Path = Path("result"),
    output_basename: str | None = None,
    review_mark: Path | None = None,
    state_root: Path = Path("work/state"),
) -> dict:
    output_stem = output_basename or task_id
    geometry_payload = _load_valid_geometry(geometry_json)
    state = TaskState(task_id, root=state_root)
    tokens = {
        token: {
            "present": state.has_token(token),
            "path": str(state.token_path(token)),
        }
        for token in REQUIRED_RELEASE_TOKENS
    }
    files = {
        suffix: _file_record(output_root / f"{output_stem}{suffix}")
        for suffix in REQUIRED_RELEASE_SUFFIXES
    }
    review_record = _file_record(review_mark) if review_mark else None
    missing_tokens = [token for token, record in tokens.items() if not record["present"]]
    missing_files = [suffix for suffix, record in files.items() if not record["exists"]]
    schema_valid = bool(geometry_payload)
    return {
        "task_id": task_id,
        "output_basename": output_stem,
        "geometry_json": _file_record(geometry_json),
        "geometry_schema_valid": schema_valid,
        "required_tokens": tokens,
        "required_outputs": files,
        "review_mark": review_record,
        "uncertain_fields": geometry_payload.uncertain_fields,
        "release_complete": not missing_tokens and not missing_files and schema_valid,
        "missing_tokens": missing_tokens,
        "missing_outputs": missing_files,
    }


def assert_release_complete(manifest: dict) -> None:
    if manifest.get("release_complete") is True:
        return
    missing_tokens = manifest.get("missing_tokens", [])
    missing_outputs = manifest.get("missing_outputs", [])
    raise ValueError(
        "release manifest is incomplete: "
        f"missing_tokens={missing_tokens}, missing_outputs={missing_outputs}"
    )


def verify_release_manifest(manifest_path: Path) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert_release_complete(manifest)
    errors: list[str] = []
    _verify_record("geometry_json", manifest.get("geometry_json"), errors)
    for suffix, record in manifest.get("required_outputs", {}).items():
        _verify_record(f"required_outputs.{suffix}", record, errors)
    review_mark = manifest.get("review_mark")
    if review_mark:
        _verify_record("review_mark", review_mark, errors)
    for token, record in manifest.get("required_tokens", {}).items():
        path = Path(record.get("path", ""))
        if not path.exists():
            errors.append(f"required_tokens.{token} missing at {path}")
    if errors:
        raise ValueError("release manifest verification failed: " + "; ".join(errors))
    return manifest


def _load_valid_geometry(path: Path) -> TaskDocument:
    payload = json.loads(path.read_text(encoding="utf-8"))
    fields = set(TaskDocument.model_fields)
    return TaskDocument.model_validate({key: value for key, value in payload.items() if key in fields})


def _file_record(path: Path | None) -> dict:
    if path is None:
        return {"exists": False, "path": None, "size": 0, "sha256": None}
    if not path.exists() or not path.is_file():
        return {"exists": False, "path": str(path), "size": 0, "sha256": None}
    data = path.read_bytes()
    return {
        "exists": True,
        "path": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _verify_record(label: str, record: dict | None, errors: list[str]) -> None:
    if not record or not record.get("path"):
        errors.append(f"{label} missing record")
        return
    current = _file_record(Path(record["path"]))
    if not current["exists"]:
        errors.append(f"{label} missing at {record['path']}")
        return
    if current["size"] != record.get("size"):
        errors.append(f"{label} size changed")
    if current["sha256"] != record.get("sha256"):
        errors.append(f"{label} sha256 changed")
