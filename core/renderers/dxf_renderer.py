from __future__ import annotations

from pathlib import Path

import ezdxf

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


def render_dxf(
    task: TaskDocument,
    output_path: Path,
    layer_config: LayerConfig | None = None,
) -> Path:
    layer_config = layer_config or load_layer_config()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = ezdxf.new("R2010")
    _create_layers(doc, layer_config)
    msp = doc.modelspace()

    for layer_name in layer_config.render_order:
        for geometry in task.geometries:
            if geometry.line_style.value != layer_name:
                continue
            _render_geometry(msp, geometry, layer_name)

    doc.saveas(output_path)
    return output_path


def _create_layers(doc, layer_config: LayerConfig) -> None:
    for layer_name in layer_config.render_order:
        style = layer_config.style_for(layer_name)
        color = 1 if style.stroke.lower() == "#ff0000" else 5 if style.stroke.lower() == "#0000ff" else 7
        lineweight = _lineweight_from_width(style.width)
        if layer_name not in doc.layers:
            doc.layers.add(layer_name, color=color, lineweight=lineweight)


def _render_geometry(msp, geometry, layer_name: str) -> None:
    attrs = {"layer": layer_name, "lineweight": -1}
    if isinstance(geometry, LineGeometry):
        x1, y1, x2, y2 = geometry.coords
        msp.add_line((x1, y1), (x2, y2), dxfattribs=attrs)
    elif isinstance(geometry, CircleGeometry):
        msp.add_circle(geometry.center, geometry.radius, dxfattribs=attrs)
    elif isinstance(geometry, ArcGeometry):
        msp.add_arc(
            geometry.center,
            geometry.radius,
            start_angle=geometry.start_angle,
            end_angle=geometry.end_angle,
            dxfattribs=attrs,
        )
    elif isinstance(geometry, PolylineGeometry):
        points = list(geometry.points)
        if geometry.closed and points[0] != points[-1]:
            points.append(points[0])
        msp.add_lwpolyline(points, dxfattribs=attrs)
    elif isinstance(geometry, HatchGeometry):
        for segment in geometry.segments:
            x1, y1, x2, y2 = segment
            msp.add_line((x1, y1), (x2, y2), dxfattribs=attrs)
    elif isinstance(geometry, TextGeometry):
        entity = msp.add_text(geometry.text, height=geometry.size, dxfattribs=attrs)
        entity.dxf.insert = geometry.position
    else:
        raise TypeError(f"unsupported geometry type: {type(geometry)!r}")


def _lineweight_from_width(width_mm: float) -> int:
    return max(0, min(211, round(width_mm * 100)))
