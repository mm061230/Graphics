import pytest
from pydantic import ValidationError

from core.geometry_schema import TaskDocument


def minimal_task() -> dict:
    return {
        "task_id": "schema_ok",
        "task_type": "UNKNOWN",
        "coordinate_system": {
            "unit": "normalized",
            "canvas_width": 1000,
            "canvas_height": 1000,
        },
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
                "id": "LINE_FRONT_001",
                "type": "LINE",
                "line_style": "VISIBLE_OUTLINE",
                "source": "manual_confirmed",
                "belongs_to_view": "FRONT",
                "coords": [100, 200, 300, 200],
            }
        ],
        "audit": {
            "gate_1": "PENDING",
            "gate_2": "PENDING",
            "gate_3": "PENDING",
            "gate_4": "PENDING",
        },
    }


def test_valid_minimal_task():
    document = TaskDocument.model_validate(minimal_task())
    assert document.task_id == "schema_ok"
    assert document.geometries[0].id == "LINE_FRONT_001"


def test_invalid_line_style_fails():
    data = minimal_task()
    data["geometries"][0]["line_style"] = "THICKISH"
    with pytest.raises(ValidationError):
        TaskDocument.model_validate(data)


def test_missing_geometry_id_fails():
    data = minimal_task()
    del data["geometries"][0]["id"]
    with pytest.raises(ValidationError):
        TaskDocument.model_validate(data)


def test_derived_line_requires_reason():
    data = minimal_task()
    data["geometries"][0]["source"] = "projection_derived"
    with pytest.raises(ValidationError):
        TaskDocument.model_validate(data)


def test_unknown_source_rejected():
    data = minimal_task()
    data["geometries"][0]["source"] = "dreamed_by_ai"
    with pytest.raises(ValidationError):
        TaskDocument.model_validate(data)


def test_unknown_view_reference_rejected():
    data = minimal_task()
    data["geometries"][0]["belongs_to_view"] = "MISSING_VIEW"
    with pytest.raises(ValidationError):
        TaskDocument.model_validate(data)

