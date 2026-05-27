from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from shapely.geometry import LineString, MultiLineString, Point, Polygon, box
from shapely.ops import unary_union

from core.geometry_schema import (
    ArcGeometry,
    CircleGeometry,
    HatchGeometry,
    LineGeometry,
    PolylineGeometry,
    TaskDocument,
    TextGeometry,
)


SectionRule = Literal["FULL_SECTION", "HALF_SECTION", "LOCAL_SECTION"]


@dataclass(frozen=True)
class SectionAudit:
    hatch_hole_intersection_area: float
    rib_hatch_intersection_area: float
    waveline_air_intersection_length: float
    section_region_is_valid: bool


@dataclass(frozen=True)
class SectionResult:
    material_region: Polygon
    hatch_segments: list[tuple[float, float, float, float]]
    audit: SectionAudit


def compute_material_region(
    outer_boundary: list[tuple[float, float]],
    holes: list[list[tuple[float, float]]] | None = None,
    rib_exclusions: list[list[tuple[float, float]]] | None = None,
) -> Polygon:
    outer = Polygon(outer_boundary)
    if not outer.is_valid or outer.area <= 0:
        raise ValueError("outer boundary must be a valid polygon with positive area")

    hole_polygons = _valid_polygons(holes or [])
    rib_polygons = _valid_polygons(rib_exclusions or [])

    material = outer
    if hole_polygons:
        material = material.difference(unary_union(hole_polygons))
    if rib_polygons:
        material = material.difference(unary_union(rib_polygons))

    if material.is_empty:
        raise ValueError("material region is empty after boolean subtraction")
    return material


def task_document_to_shapely(task: TaskDocument) -> dict[str, object]:
    shapes: dict[str, object] = {}
    for geometry in task.geometries:
        shapes[geometry.id] = geometry_to_shapely(geometry)
    return shapes


def geometry_to_shapely(geometry):
    if isinstance(geometry, LineGeometry):
        x1, y1, x2, y2 = geometry.coords
        return LineString([(x1, y1), (x2, y2)])
    if isinstance(geometry, CircleGeometry):
        return Point(geometry.center).buffer(geometry.radius, quad_segs=64)
    if isinstance(geometry, ArcGeometry):
        return _arc_to_linestring(geometry)
    if isinstance(geometry, PolylineGeometry):
        if geometry.closed:
            return Polygon(geometry.points)
        return LineString(geometry.points)
    if isinstance(geometry, HatchGeometry):
        lines = [LineString([(x1, y1), (x2, y2)]) for x1, y1, x2, y2 in geometry.segments]
        return unary_union(lines) if lines else LineString()
    if isinstance(geometry, TextGeometry):
        return Point(geometry.position)
    raise TypeError(f"unsupported geometry for shapely conversion: {type(geometry)!r}")


def apply_section_rule(
    material_region,
    rule: SectionRule = "FULL_SECTION",
    local_boundary: list[tuple[float, float]] | None = None,
    half_axis: Literal["vertical", "horizontal"] = "vertical",
    half_side: Literal["positive", "negative"] = "positive",
    center: tuple[float, float] | None = None,
):
    if rule == "FULL_SECTION":
        return material_region
    if rule == "LOCAL_SECTION":
        if not local_boundary:
            raise ValueError("local section requires local_boundary")
        local_polygon = Polygon(local_boundary)
        if not local_polygon.is_valid or local_polygon.area <= 0:
            raise ValueError("local_boundary must be a valid polygon with positive area")
        return material_region.intersection(local_polygon)
    if rule == "HALF_SECTION":
        minx, miny, maxx, maxy = material_region.bounds
        cx, cy = center or ((minx + maxx) / 2, (miny + maxy) / 2)
        if half_axis == "vertical":
            clip = box(cx, miny, maxx, maxy) if half_side == "positive" else box(minx, miny, cx, maxy)
        else:
            clip = box(minx, cy, maxx, maxy) if half_side == "positive" else box(minx, miny, maxx, cy)
        return material_region.intersection(clip)
    raise ValueError(f"unknown section rule: {rule}")


def generate_hatch_segments(
    material_region,
    spacing: float = 6.0,
    angle_degrees: float = 45.0,
) -> list[tuple[float, float, float, float]]:
    if angle_degrees != 45.0:
        raise NotImplementedError("only 45 degree hatch generation is currently supported")

    minx, miny, maxx, maxy = material_region.bounds
    span = (maxx - minx) + (maxy - miny) + spacing * 4
    start = int((miny - maxx - span) // spacing) * spacing
    end = int((maxy - minx + span) // spacing + 1) * spacing

    segments: list[tuple[float, float, float, float]] = []
    offset = start
    while offset <= end:
        candidate = LineString([(minx - span, minx - span + offset), (maxx + span, maxx + span + offset)])
        clipped = candidate.intersection(material_region)
        segments.extend(_segments_from_geometry(clipped))
        offset += spacing
    return segments


def compute_section_hatching(
    outer_boundary: list[tuple[float, float]],
    holes: list[list[tuple[float, float]]] | None = None,
    rib_exclusions: list[list[tuple[float, float]]] | None = None,
    wave_lines: list[list[tuple[float, float]]] | None = None,
    spacing: float = 6.0,
    section_rule: SectionRule = "FULL_SECTION",
    local_boundary: list[tuple[float, float]] | None = None,
    half_axis: Literal["vertical", "horizontal"] = "vertical",
    half_side: Literal["positive", "negative"] = "positive",
    center: tuple[float, float] | None = None,
) -> SectionResult:
    hole_polygons = _valid_polygons(holes or [])
    rib_polygons = _valid_polygons(rib_exclusions or [])
    material = apply_section_rule(
        compute_material_region(outer_boundary, holes, rib_exclusions),
        rule=section_rule,
        local_boundary=local_boundary,
        half_axis=half_axis,
        half_side=half_side,
        center=center,
    )
    if material.is_empty:
        raise ValueError("section rule produced an empty material region")
    hatch_segments = generate_hatch_segments(material, spacing=spacing)
    hatch_lines = [LineString([(x1, y1), (x2, y2)]) for x1, y1, x2, y2 in hatch_segments]
    hatch_union = unary_union(hatch_lines) if hatch_lines else LineString()
    holes_union = unary_union(hole_polygons) if hole_polygons else Polygon()
    ribs_union = unary_union(rib_polygons) if rib_polygons else Polygon()

    waveline_air_intersection = 0.0
    if wave_lines and hole_polygons:
        air = holes_union
        for points in wave_lines:
            if len(points) >= 2:
                waveline_air_intersection += LineString(points).intersection(air).length

    hole_interior = holes_union.buffer(-0.001) if hole_polygons else Polygon()
    rib_interior = ribs_union.buffer(-0.001) if rib_polygons else Polygon()

    audit = SectionAudit(
        hatch_hole_intersection_area=hatch_union.intersection(hole_interior).length
        if hole_polygons and not hole_interior.is_empty
        else 0.0,
        rib_hatch_intersection_area=hatch_union.intersection(rib_interior).length
        if rib_polygons and not rib_interior.is_empty
        else 0.0,
        waveline_air_intersection_length=waveline_air_intersection,
        section_region_is_valid=material.is_valid and not material.is_empty,
    )
    return SectionResult(material_region=material, hatch_segments=hatch_segments, audit=audit)


def _valid_polygons(boundaries: list[list[tuple[float, float]]]) -> list[Polygon]:
    polygons = []
    for boundary in boundaries:
        if len(boundary) < 3:
            continue
        polygon = Polygon(boundary)
        if not polygon.is_valid or polygon.area <= 0:
            raise ValueError("invalid polygon supplied for boolean section operation")
        polygons.append(polygon)
    return polygons


def _segments_from_geometry(geometry) -> list[tuple[float, float, float, float]]:
    if geometry.is_empty:
        return []
    if isinstance(geometry, LineString):
        coords = list(geometry.coords)
        if len(coords) < 2:
            return []
        return [(coords[0][0], coords[0][1], coords[-1][0], coords[-1][1])]
    if isinstance(geometry, MultiLineString):
        segments = []
        for subline in geometry.geoms:
            segments.extend(_segments_from_geometry(subline))
        return segments
    if hasattr(geometry, "geoms"):
        segments = []
        for part in geometry.geoms:
            segments.extend(_segments_from_geometry(part))
        return segments
    return []


def _arc_to_linestring(arc: ArcGeometry, segments: int = 32) -> LineString:
    delta = (arc.end_angle - arc.start_angle) % 360
    if delta == 0:
        delta = 360
    step_count = max(2, int(segments * delta / 360))
    points = []
    for index in range(step_count + 1):
        angle = math.radians(arc.start_angle + delta * index / step_count)
        points.append(
            (
                arc.center[0] + arc.radius * math.cos(angle),
                arc.center[1] + arc.radius * math.sin(angle),
            )
        )
    return LineString(points)
