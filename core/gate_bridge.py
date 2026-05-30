from __future__ import annotations

import json
import math
from pathlib import Path

from core.geometry_schema import (
    CircleGeometry,
    PolylineGeometry,
    TaskDocument,
)
from core.projection_engine import audit_projection, derive_missing_width_lines
from core.section_boolean import compute_section_hatching


def bridge_gate1_to_gate2(
    gate1_json: Path,
    output_path: Path | None = None,
) -> Path:
    payload = json.loads(gate1_json.read_text(encoding="utf-8"))
    fields = set(TaskDocument.model_fields)
    task = TaskDocument.model_validate(
        {k: v for k, v in payload.items() if k in fields}
    )

    audit = audit_projection(task)
    derived = derive_missing_width_lines(task)

    payload["projection_audit"] = {
        "length_alignment_error": audit.length_alignment_error,
        "height_alignment_error": audit.height_alignment_error,
        "width_equality_error": audit.width_equality_error,
    }

    existing_ids = {g["id"] for g in payload.get("geometries", [])}
    for line in derived:
        dump = line.model_dump(mode="json")
        if dump["id"] not in existing_ids:
            payload["geometries"].append(dump)

    target = output_path or gate1_json.parent / gate1_json.name.replace(
        "_gate1.json", "_gate2.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target


def bridge_gate2_to_gate3(
    gate2_json: Path,
    output_path: Path | None = None,
) -> Path:
    payload = json.loads(gate2_json.read_text(encoding="utf-8"))
    fields = set(TaskDocument.model_fields)
    task = TaskDocument.model_validate(
        {k: v for k, v in payload.items() if k in fields}
    )

    outer_boundary, section_view_id = _extract_outer_boundary(task)
    holes = _extract_holes(task, section_view_id)

    if not outer_boundary:
        payload["topology_audit"] = {
            "hatch_hole_intersection_area": 0.0,
            "rib_hatch_intersection_area": 0.0,
            "waveline_air_intersection_length": 0.0,
        }
    else:
        try:
            result = compute_section_hatching(
                outer_boundary=outer_boundary,
                holes=holes,
                section_rule="FULL_SECTION",
            )
        except ValueError:
            payload["topology_audit"] = {
                "hatch_hole_intersection_area": 0.0,
                "rib_hatch_intersection_area": 0.0,
                "waveline_air_intersection_length": 0.0,
            }
            target = output_path or gate2_json.parent / gate2_json.name.replace(
                "_gate2.json", "_gate3.json"
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return target

        payload["topology_audit"] = {
            "hatch_hole_intersection_area": result.audit.hatch_hole_intersection_area,
            "rib_hatch_intersection_area": result.audit.rib_hatch_intersection_area,
            "waveline_air_intersection_length": result.audit.waveline_air_intersection_length,
        }
        if result.hatch_segments:
            hatch_id = _next_hatch_id(payload)
            payload.setdefault("geometries", []).append({
                "id": hatch_id,
                "type": "HATCH",
                "line_style": "HATCH_LINE",
                "source": "section_derived",
                "belongs_to_view": section_view_id or "SECTION",
                "confidence": 1.0,
                "reason": "auto-generated from section boolean computation",
                "segments": result.hatch_segments,
            })

    target = output_path or gate2_json.parent / gate2_json.name.replace(
        "_gate2.json", "_gate3.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target


def _extract_outer_boundary(
    task: TaskDocument,
) -> tuple[list[tuple[float, float]] | None, str | None]:
    for view in task.views:
        if view.type != "SECTION":
            continue
        section_geoms = [
            g for g in task.geometries
            if hasattr(g, "belongs_to_view") and g.belongs_to_view == view.id
        ]
        for geom in section_geoms:
            if isinstance(geom, PolylineGeometry) and geom.closed:
                return list(geom.points), view.id
    return None, None


def _extract_holes(
    task: TaskDocument,
    section_view_id: str | None,
) -> list[list[tuple[float, float]]]:
    holes: list[list[tuple[float, float]]] = []
    target_view = section_view_id
    for geom in task.geometries:
        view_id = getattr(geom, "belongs_to_view", None)
        if target_view and view_id != target_view:
            continue
        if isinstance(geom, CircleGeometry) and getattr(geom, "is_hole", False):
            cx, cy = geom.center
            r = geom.radius
            points = [
                (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
                for a in range(0, 360, 30)
            ]
            holes.append(points)
    return holes


def _next_hatch_id(payload: dict) -> str:
    existing = {g["id"] for g in payload.get("geometries", [])}
    index = 1
    while True:
        candidate = f"HATCH_SECTION_DERIVED_{index:03d}"
        if candidate not in existing:
            return candidate
        index += 1