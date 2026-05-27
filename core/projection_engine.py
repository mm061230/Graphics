from __future__ import annotations

from dataclasses import dataclass, field

from core.geometry_schema import GeometrySource, LineGeometry, LineStyle, TaskDocument


@dataclass(frozen=True)
class ProjectionAudit:
    length_alignment_error: float
    height_alignment_error: float
    width_equality_error: float
    messages: list[str] = field(default_factory=list)


def audit_projection(task: TaskDocument) -> ProjectionAudit:
    front = _view(task, "FRONT")
    top = _view(task, "TOP")
    left = _view(task, "LEFT")

    length_error = 0.0
    height_error = 0.0
    width_error = 0.0
    messages: list[str] = []

    if front and top:
        length_error = max(
            abs(front.origin[0] - top.origin[0]),
            abs(front.width - top.width),
            abs(front.scale - top.scale),
        )
        messages.append(f"front_top_length_error={length_error}")
    if front and left:
        height_error = max(
            abs(front.origin[1] - left.origin[1]),
            abs(front.height - left.height),
            abs(front.scale - left.scale),
        )
        messages.append(f"front_left_height_error={height_error}")
    if top and left:
        width_error = abs(top.height - left.width)
        width_error = max(width_error, abs(top.scale - left.scale))
        messages.append(f"top_left_width_error={width_error}")

    return ProjectionAudit(
        length_alignment_error=length_error,
        height_alignment_error=height_error,
        width_equality_error=width_error,
        messages=messages,
    )


def width_to_left_x(y_top: float, y_top_center: float, x_left_center: float) -> float:
    delta = abs(y_top - y_top_center)
    if y_top > y_top_center:
        return x_left_center - delta
    if y_top < y_top_center:
        return x_left_center + delta
    return x_left_center


def derive_missing_width_lines(
    task: TaskDocument,
    tolerance: float = 1.0,
) -> list[LineGeometry]:
    top = _view(task, "TOP")
    left = _view(task, "LEFT")
    if not top or not left:
        return []

    top_horizontal_lines = [
        geom
        for geom in task.geometries
        if isinstance(geom, LineGeometry)
        and geom.belongs_to_view == top.id
        and abs(geom.coords[1] - geom.coords[3]) <= tolerance
    ]
    left_vertical_xs = {
        round(geom.coords[0], 3)
        for geom in task.geometries
        if isinstance(geom, LineGeometry)
        and geom.belongs_to_view == left.id
        and abs(geom.coords[0] - geom.coords[2]) <= tolerance
    }

    derived: list[LineGeometry] = []
    for index, top_line in enumerate(top_horizontal_lines, start=1):
        y_top = top_line.coords[1]
        expected_x = width_to_left_x(y_top, top.center[1], left.center[0])
        matched = any(abs(x - expected_x) <= tolerance for x in left_vertical_xs)
        if matched:
            continue
        derived.append(
            LineGeometry(
                id=f"LINE_LEFT_WIDTH_DERIVED_{index:03d}",
                line_style=LineStyle.HIDDEN_OUTLINE,
                source=GeometrySource.PROJECTION_DERIVED,
                belongs_to_view=left.id,
                reason=(
                    "Derived from top-view horizontal feature using width-equality "
                    "projection invariant"
                ),
                coords=(expected_x, left.origin[1], expected_x, left.origin[1] + left.height),
                confidence=1.0,
            )
        )
    return derived


def _view(task: TaskDocument, view_type: str):
    for view in task.views:
        if view.type == view_type:
            return view
    return None

