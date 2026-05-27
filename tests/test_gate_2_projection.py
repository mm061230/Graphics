from core.geometry_schema import TaskDocument
from core.projection_engine import audit_projection, derive_missing_width_lines, width_to_left_x


def projection_task(include_left_width_line: bool = True) -> TaskDocument:
    geometries = [
        {
            "id": "TOP_WIDTH_FEATURE",
            "type": "LINE",
            "line_style": "VISIBLE_OUTLINE",
            "source": "manual_confirmed",
            "belongs_to_view": "TOP",
            "coords": [100, 260, 500, 260],
        }
    ]
    if include_left_width_line:
        geometries.append(
            {
                "id": "LEFT_MATCHING_WIDTH",
                "type": "LINE",
                "line_style": "HIDDEN_OUTLINE",
                "source": "manual_confirmed",
                "belongs_to_view": "LEFT",
                "coords": [340, 100, 340, 400],
            }
        )
    return TaskDocument.model_validate(
        {
            "task_id": "projection_case",
            "views": [
                {
                    "id": "FRONT",
                    "type": "FRONT",
                    "origin": [100, 100],
                    "center": [300, 250],
                    "width": 400,
                    "height": 300,
                    "scale": 1,
                },
                {
                    "id": "TOP",
                    "type": "TOP",
                    "origin": [100, 500],
                    "center": [300, 300],
                    "width": 400,
                    "height": 200,
                    "scale": 1,
                },
                {
                    "id": "LEFT",
                    "type": "LEFT",
                    "origin": [600, 100],
                    "center": [300, 250],
                    "width": 200,
                    "height": 300,
                    "scale": 1,
                },
            ],
            "geometries": geometries,
        }
    )


def test_width_mapping_above_center_goes_left():
    assert width_to_left_x(260, 300, 300) == 340
    assert width_to_left_x(340, 300, 300) == 260


def test_projection_audit_passes_for_aligned_views():
    audit = audit_projection(projection_task())
    assert audit.length_alignment_error == 0
    assert audit.height_alignment_error == 0
    assert audit.width_equality_error == 0


def test_projection_audit_detects_misalignment():
    task = projection_task()
    task.views[1].width = 410
    audit = audit_projection(task)
    assert audit.length_alignment_error == 10


def test_no_missing_line_when_width_feature_exists():
    assert derive_missing_width_lines(projection_task(include_left_width_line=True)) == []


def test_missing_width_line_is_derived_with_reason():
    derived = derive_missing_width_lines(projection_task(include_left_width_line=False))
    assert len(derived) == 1
    assert derived[0].source.value == "projection_derived"
    assert derived[0].reason
