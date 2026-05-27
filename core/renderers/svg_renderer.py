from __future__ import annotations

import math
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from core.geometry_schema import (
    ArcGeometry,
    CircleGeometry,
    HatchGeometry,
    LineGeometry,
    PolylineGeometry,
    TaskDocument,
    TextGeometry,
)
from core.layer_config import LayerConfig, load_layer_config


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def render_svg(
    task: TaskDocument,
    output_path: Path,
    layer_config: LayerConfig | None = None,
) -> Path:
    layer_config = layer_config or load_layer_config()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    width = task.coordinate_system.canvas_width
    height = task.coordinate_system.canvas_height
    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "width": f"{width:g}",
            "height": f"{height:g}",
            "viewBox": f"0 0 {width:g} {height:g}",
            "version": "1.1",
        },
    )
    ET.SubElement(root, f"{{{SVG_NS}}}rect", {"width": "100%", "height": "100%", "fill": "#ffffff"})

    groups = {
        layer_name: ET.SubElement(root, f"{{{SVG_NS}}}g", {"id": f"layer_{layer_name}"})
        for layer_name in layer_config.render_order
    }

    for layer_name in layer_config.render_order:
        layer_geometries = [
            geometry for geometry in task.geometries if geometry.line_style.value == layer_name
        ]
        for geometry in layer_geometries:
            _render_geometry(groups[layer_name], geometry, layer_config)

    xml = ET.tostring(root, encoding="unicode")
    output_path.write_text(xml, encoding="utf-8")
    return output_path


def _render_geometry(parent: ET.Element, geometry, layer_config: LayerConfig) -> None:
    style = layer_config.style_for(geometry.line_style.value)
    common = {
        "id": geometry.id,
        "stroke": style.stroke,
        "stroke-width": f"{style.width:g}",
        "fill": "none",
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
    }
    if style.dash:
        common["stroke-dasharray"] = " ".join(f"{value:g}" for value in style.dash)

    if isinstance(geometry, LineGeometry):
        x1, y1, x2, y2 = geometry.coords
        ET.SubElement(
            parent,
            f"{{{SVG_NS}}}line",
            common | {"x1": f"{x1:g}", "y1": f"{y1:g}", "x2": f"{x2:g}", "y2": f"{y2:g}"},
        )
    elif isinstance(geometry, CircleGeometry):
        cx, cy = geometry.center
        ET.SubElement(
            parent,
            f"{{{SVG_NS}}}circle",
            common | {"cx": f"{cx:g}", "cy": f"{cy:g}", "r": f"{geometry.radius:g}"},
        )
    elif isinstance(geometry, ArcGeometry):
        ET.SubElement(parent, f"{{{SVG_NS}}}path", common | {"d": _arc_path(geometry)})
    elif isinstance(geometry, PolylineGeometry):
        points = " ".join(f"{x:g},{y:g}" for x, y in geometry.points)
        tag = "polygon" if geometry.closed else "polyline"
        ET.SubElement(parent, f"{{{SVG_NS}}}{tag}", common | {"points": points})
    elif isinstance(geometry, HatchGeometry):
        for index, segment in enumerate(geometry.segments):
            x1, y1, x2, y2 = segment
            ET.SubElement(
                parent,
                f"{{{SVG_NS}}}line",
                common
                | {
                    "id": f"{geometry.id}_{index:03d}",
                    "x1": f"{x1:g}",
                    "y1": f"{y1:g}",
                    "x2": f"{x2:g}",
                    "y2": f"{y2:g}",
                },
            )
    elif isinstance(geometry, TextGeometry):
        x, y = geometry.position
        text_element = ET.SubElement(
            parent,
            f"{{{SVG_NS}}}text",
            {
                "id": geometry.id,
                "x": f"{x:g}",
                "y": f"{y:g}",
                "fill": style.stroke,
                "font-size": f"{geometry.size:g}",
                "font-family": "SimSun, Noto Sans CJK SC, sans-serif",
            },
        )
        text_element.text = escape(geometry.text)
    else:
        raise TypeError(f"unsupported geometry type: {type(geometry)!r}")


def _arc_path(arc: ArcGeometry) -> str:
    start_rad = math.radians(arc.start_angle)
    end_rad = math.radians(arc.end_angle)
    sx = arc.center[0] + arc.radius * math.cos(start_rad)
    sy = arc.center[1] + arc.radius * math.sin(start_rad)
    ex = arc.center[0] + arc.radius * math.cos(end_rad)
    ey = arc.center[1] + arc.radius * math.sin(end_rad)
    delta = (arc.end_angle - arc.start_angle) % 360
    large_arc = 1 if delta > 180 else 0
    sweep = 1
    return (
        f"M {sx:g} {sy:g} "
        f"A {arc.radius:g} {arc.radius:g} 0 {large_arc} {sweep} {ex:g} {ey:g}"
    )

