from pathlib import Path

from core.geometry_schema import TaskDocument
from core.layer_config import load_layer_config
from core.renderers.svg_renderer import render_svg


def render_task() -> TaskDocument:
    return TaskDocument.model_validate(
        {
            "task_id": "render_case",
            "views": [
                {
                    "id": "FRONT",
                    "type": "FRONT",
                    "origin": [100, 100],
                    "center": [300, 300],
                    "width": 400,
                    "height": 300,
                    "scale": 1.0,
                }
            ],
            "geometries": [
                {
                    "id": "CENTER_001",
                    "type": "LINE",
                    "line_style": "CENTERLINE",
                    "source": "manual_confirmed",
                    "belongs_to_view": "FRONT",
                    "coords": [100, 300, 500, 300],
                },
                {
                    "id": "HATCH_001",
                    "type": "HATCH",
                    "line_style": "HATCH_LINE",
                    "source": "section_derived",
                    "belongs_to_view": "FRONT",
                    "reason": "test hatch generated inside material",
                    "segments": [[150, 250, 200, 300], [180, 250, 230, 300]],
                },
                {
                    "id": "OUTLINE_001",
                    "type": "LINE",
                    "line_style": "VISIBLE_OUTLINE",
                    "source": "manual_confirmed",
                    "belongs_to_view": "FRONT",
                    "coords": [100, 200, 500, 200],
                },
                {
                    "id": "CIRCLE_001",
                    "type": "CIRCLE",
                    "line_style": "VISIBLE_OUTLINE",
                    "source": "manual_confirmed",
                    "belongs_to_view": "FRONT",
                    "center": [300, 300],
                    "radius": 50,
                    "is_hole": True,
                },
                {
                    "id": "ARC_001",
                    "type": "ARC",
                    "line_style": "VISIBLE_OUTLINE",
                    "source": "manual_confirmed",
                    "belongs_to_view": "FRONT",
                    "center": [300, 300],
                    "radius": 80,
                    "start_angle": 0,
                    "end_angle": 90,
                },
                {
                    "id": "TEXT_001",
                    "type": "TEXT",
                    "line_style": "TEXT_SYMBOL",
                    "source": "manual_confirmed",
                    "belongs_to_view": "FRONT",
                    "position": [100, 80],
                    "text": "A-A",
                    "size": 16,
                },
            ],
        }
    )


def test_layer_config_loads():
    config = load_layer_config()
    assert config.render_order[0] == "CENTERLINE"
    assert "VISIBLE_OUTLINE" in config.layers


def test_svg_generation(tmp_path: Path):
    output = render_svg(render_task(), tmp_path / "answer.svg")
    content = output.read_text(encoding="utf-8")
    assert output.exists()
    assert "layer_CENTERLINE" in content
    assert "layer_VISIBLE_OUTLINE" in content
    assert "OUTLINE_001" in content
    assert "CIRCLE_001" in content
    assert "ARC_001" in content
    assert "HATCH_001_000" in content


def test_visible_outline_layer_renders_after_centerline(tmp_path: Path):
    output = render_svg(render_task(), tmp_path / "answer.svg")
    content = output.read_text(encoding="utf-8")
    assert content.index("layer_CENTERLINE") < content.index("layer_VISIBLE_OUTLINE")
