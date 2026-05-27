import pytest

from core.section_boolean import (
    compute_material_region,
    compute_section_hatching,
    task_document_to_shapely,
)
from tests.test_svg_renderer import render_task


def rectangle():
    return [(0, 0), (120, 0), (120, 80), (0, 80)]


def hole():
    return [(40, 20), (80, 20), (80, 60), (40, 60)]


def rib():
    return [(10, 10), (30, 10), (30, 70), (10, 70)]


def test_simple_rectangle_hatch_segments_exist():
    result = compute_section_hatching(rectangle(), spacing=10)
    assert result.audit.section_region_is_valid
    assert result.hatch_segments


def test_hatch_does_not_enter_hole():
    result = compute_section_hatching(rectangle(), holes=[hole()], spacing=8)
    assert result.audit.hatch_hole_intersection_area == pytest.approx(0.0)


def test_rib_exclusion_has_zero_hatch_intersection():
    result = compute_section_hatching(rectangle(), rib_exclusions=[rib()], spacing=8)
    assert result.audit.rib_hatch_intersection_area == pytest.approx(0.0)


def test_wave_line_crossing_hole_is_detected():
    result = compute_section_hatching(
        rectangle(),
        holes=[hole()],
        wave_lines=[[(0, 40), (120, 40)]],
        spacing=8,
    )
    assert result.audit.waveline_air_intersection_length > 0


def test_invalid_outer_polygon_fails():
    with pytest.raises(ValueError):
        compute_material_region([(0, 0), (1, 1), (2, 2)])


def test_geometry_json_converts_to_shapely_objects():
    shapes = task_document_to_shapely(render_task())
    assert shapes["OUTLINE_001"].length > 0
    assert shapes["CIRCLE_001"].area > 0


def test_half_section_rule_clips_material_region():
    result = compute_section_hatching(rectangle(), spacing=10, section_rule="HALF_SECTION")
    assert result.material_region.area == pytest.approx(120 * 80 / 2)


def test_local_section_rule_clips_to_local_boundary():
    result = compute_section_hatching(
        rectangle(),
        spacing=10,
        section_rule="LOCAL_SECTION",
        local_boundary=[(20, 20), (60, 20), (60, 60), (20, 60)],
    )
    assert result.material_region.area == pytest.approx(40 * 40)
