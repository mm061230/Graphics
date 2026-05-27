from pathlib import Path

import pytest

from core.renderers.dxf_renderer import render_dxf
from core.renderers.export_converter import (
    ExportDependencyError,
    png_dimensions,
    svg_to_pdf,
    svg_to_png,
)
from core.renderers.svg_renderer import render_svg
from tests.test_svg_renderer import render_task


def test_dxf_generation(tmp_path: Path):
    output = render_dxf(render_task(), tmp_path / "answer.dxf")
    assert output.exists()
    content = output.read_text(encoding="utf-8", errors="ignore")
    assert "VISIBLE_OUTLINE" in content
    assert "CENTERLINE" in content
    assert "370" in content


def test_png_and_pdf_generation(tmp_path: Path):
    svg = render_svg(render_task(), tmp_path / "answer.svg")
    png = svg_to_png(svg, tmp_path / "answer.png", output_width=1200)
    pdf = svg_to_pdf(svg, tmp_path / "answer.pdf")

    assert png.exists()
    assert pdf.exists()
    width, height = png_dimensions(png)
    assert width == 1200
    assert height > 0
