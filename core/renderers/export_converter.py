from __future__ import annotations

import math
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


class ExportDependencyError(RuntimeError):
    """Raised when an optional external export dependency is unavailable."""


def svg_to_png(svg_path: Path, png_path: Path, output_width: int | None = None) -> Path:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        cairosvg = _load_cairosvg()
        kwargs = {"url": str(svg_path), "write_to": str(png_path)}
        if output_width:
            kwargs["output_width"] = output_width
        cairosvg.svg2png(**kwargs)
    except ExportDependencyError:
        _fallback_svg_to_image(svg_path, png_path, output_width)
    _assert_file(png_path)
    return png_path


def svg_to_pdf(svg_path: Path, pdf_path: Path) -> Path:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        cairosvg = _load_cairosvg()
        cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path))
    except ExportDependencyError:
        image = _fallback_svg_to_image(svg_path)
        image.save(pdf_path, "PDF", resolution=300.0)
    _assert_file(pdf_path)
    return pdf_path


def png_dimensions(png_path: Path) -> tuple[int, int]:
    with Image.open(png_path) as image:
        return image.size


def _assert_file(path: Path) -> None:
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"expected output file was not created: {path}")


def _load_cairosvg():
    try:
        import cairosvg

        return cairosvg
    except OSError as exc:
        raise ExportDependencyError(
            "CairoSVG is installed, but the native cairo runtime is missing"
        ) from exc
    except ImportError as exc:
        raise ExportDependencyError("CairoSVG is not installed") from exc


def _fallback_svg_to_image(
    svg_path: Path,
    png_path: Path | None = None,
    output_width: int | None = None,
) -> Image.Image:
    root = ET.fromstring(svg_path.read_text(encoding="utf-8"))
    width, height = _svg_dimensions(root)
    scale = (output_width / width) if output_width else 1.0
    image = Image.new("RGB", (round(width * scale), round(height * scale)), "white")
    draw = ImageDraw.Draw(image)

    for element in root.iter():
        tag = _local_name(element.tag)
        if tag in {"svg", "g"}:
            continue
        if tag == "rect":
            _draw_rect(draw, element, scale)
        elif tag == "line":
            _draw_line(draw, element, scale)
        elif tag == "circle":
            _draw_circle(draw, element, scale)
        elif tag in {"polyline", "polygon"}:
            _draw_poly(draw, element, scale, closed=tag == "polygon")
        elif tag == "path":
            _draw_arc_path(draw, element, scale)
        elif tag == "text":
            _draw_text(draw, element, scale)

    if png_path:
        image.save(png_path)
    return image


def _svg_dimensions(root: ET.Element) -> tuple[float, float]:
    view_box = root.attrib.get("viewBox")
    if view_box:
        parts = [float(part) for part in view_box.replace(",", " ").split()]
        if len(parts) == 4:
            return parts[2], parts[3]
    return _float(root.attrib.get("width", "1000")), _float(root.attrib.get("height", "1000"))


def _style(element: ET.Element, scale: float) -> tuple[str, int]:
    color = element.attrib.get("stroke") or element.attrib.get("fill") or "#000000"
    width = max(1, round(_float(element.attrib.get("stroke-width", "1")) * scale))
    return color, width


def _draw_rect(draw: ImageDraw.ImageDraw, element: ET.Element, scale: float) -> None:
    fill = element.attrib.get("fill")
    if not fill:
        return
    width = element.attrib.get("width")
    height = element.attrib.get("height")
    if width == "100%" or height == "100%":
        draw.rectangle((0, 0, draw.im.size[0], draw.im.size[1]), fill=fill)
        return
    x = _float(element.attrib.get("x", "0")) * scale
    y = _float(element.attrib.get("y", "0")) * scale
    w = _float(width or "0") * scale
    h = _float(height or "0") * scale
    draw.rectangle((x, y, x + w, y + h), fill=fill)


def _draw_line(draw: ImageDraw.ImageDraw, element: ET.Element, scale: float) -> None:
    color, width = _style(element, scale)
    points = (
        _float(element.attrib["x1"]) * scale,
        _float(element.attrib["y1"]) * scale,
        _float(element.attrib["x2"]) * scale,
        _float(element.attrib["y2"]) * scale,
    )
    draw.line(points, fill=color, width=width)


def _draw_circle(draw: ImageDraw.ImageDraw, element: ET.Element, scale: float) -> None:
    color, width = _style(element, scale)
    cx = _float(element.attrib["cx"]) * scale
    cy = _float(element.attrib["cy"]) * scale
    radius = _float(element.attrib["r"]) * scale
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=color, width=width)


def _draw_poly(
    draw: ImageDraw.ImageDraw,
    element: ET.Element,
    scale: float,
    closed: bool,
) -> None:
    color, width = _style(element, scale)
    points = [
        tuple(float(value) * scale for value in pair.split(",", 1))
        for pair in element.attrib.get("points", "").split()
    ]
    if closed and points:
        points.append(points[0])
    if len(points) >= 2:
        draw.line(points, fill=color, width=width)


def _draw_arc_path(draw: ImageDraw.ImageDraw, element: ET.Element, scale: float) -> None:
    match = re.fullmatch(
        r"M\s+([\d.+-]+)\s+([\d.+-]+)\s+A\s+([\d.+-]+)\s+([\d.+-]+)\s+0\s+([01])\s+([01])\s+([\d.+-]+)\s+([\d.+-]+)",
        element.attrib.get("d", ""),
    )
    if not match:
        return
    sx, sy, rx, _ry, large_arc, sweep, ex, ey = match.groups()
    sx_f, sy_f = float(sx), float(sy)
    ex_f, ey_f = float(ex), float(ey)
    radius = float(rx)
    chord = math.hypot(ex_f - sx_f, ey_f - sy_f)
    if chord == 0 or chord > radius * 2:
        return
    midpoint = ((sx_f + ex_f) / 2, (sy_f + ey_f) / 2)
    height = math.sqrt(max(radius * radius - (chord / 2) ** 2, 0.0))
    normal = (-(ey_f - sy_f) / chord, (ex_f - sx_f) / chord)
    centers = [
        (midpoint[0] + normal[0] * height, midpoint[1] + normal[1] * height),
        (midpoint[0] - normal[0] * height, midpoint[1] - normal[1] * height),
    ]
    center = _select_arc_center(centers, sx_f, sy_f, ex_f, ey_f, bool(int(large_arc)), bool(int(sweep)))
    if center is None:
        return
    start = math.degrees(math.atan2(sy_f - center[1], sx_f - center[0]))
    end = math.degrees(math.atan2(ey_f - center[1], ex_f - center[0]))
    color, width = _style(element, scale)
    bbox = (
        (center[0] - radius) * scale,
        (center[1] - radius) * scale,
        (center[0] + radius) * scale,
        (center[1] + radius) * scale,
    )
    draw.arc(bbox, start=start, end=end, fill=color, width=width)


def _draw_text(draw: ImageDraw.ImageDraw, element: ET.Element, scale: float) -> None:
    color = element.attrib.get("fill", "#000000")
    size = max(1, round(_float(element.attrib.get("font-size", "14")) * scale))
    try:
        font = ImageFont.truetype("arial.ttf", size)
    except OSError:
        font = ImageFont.load_default()
    draw.text(
        (_float(element.attrib.get("x", "0")) * scale, _float(element.attrib.get("y", "0")) * scale),
        element.text or "",
        fill=color,
        font=font,
    )


def _select_arc_center(
    centers: list[tuple[float, float]],
    sx: float,
    sy: float,
    ex: float,
    ey: float,
    large_arc: bool,
    sweep: bool,
) -> tuple[float, float] | None:
    for center in centers:
        start = math.atan2(sy - center[1], sx - center[0])
        end = math.atan2(ey - center[1], ex - center[0])
        delta = (end - start) % (2 * math.pi)
        if not sweep:
            delta = (start - end) % (2 * math.pi)
        if (delta > math.pi) == large_arc:
            return center
    return centers[0] if centers else None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _float(value: str) -> float:
    return float(value.rstrip("px"))
