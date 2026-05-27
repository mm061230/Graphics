from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LineStyle(str, Enum):
    VISIBLE_OUTLINE = "VISIBLE_OUTLINE"
    HIDDEN_OUTLINE = "HIDDEN_OUTLINE"
    CENTERLINE = "CENTERLINE"
    HATCH_LINE = "HATCH_LINE"
    WAVE_LINE = "WAVE_LINE"
    TEXT_SYMBOL = "TEXT_SYMBOL"


class GeometrySource(str, Enum):
    OPENCV_CANDIDATE = "opencv_candidate"
    AI_CANDIDATE = "ai_candidate"
    MANUAL_CONFIRMED = "manual_confirmed"
    PROJECTION_DERIVED = "projection_derived"
    SECTION_DERIVED = "section_derived"
    RENDERER_GENERATED = "renderer_generated"


class TaskType(str, Enum):
    UNKNOWN = "UNKNOWN"
    MISSING_LINE = "MISSING_LINE"
    FULL_SECTION = "FULL_SECTION"
    HALF_SECTION = "HALF_SECTION"
    LOCAL_SECTION = "LOCAL_SECTION"
    ROTATED_SECTION = "ROTATED_SECTION"
    STEPPED_SECTION = "STEPPED_SECTION"
    CROSS_SECTION = "CROSS_SECTION"


class CoordinateSystem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit: Literal["normalized", "px", "mm"] = "normalized"
    canvas_width: float = Field(gt=0, default=1000.0)
    canvas_height: float = Field(gt=0, default=1000.0)


class ViewBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: Literal["FRONT", "TOP", "LEFT", "SECTION", "AUXILIARY", "UNKNOWN"]
    origin: tuple[float, float]
    center: tuple[float, float]
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    scale: float = Field(gt=0, default=1.0)


class BaseGeometry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: str
    line_style: LineStyle
    source: GeometrySource
    belongs_to_view: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reason: str | None = None

    @model_validator(mode="after")
    def require_reason_for_derived_geometry(self) -> "BaseGeometry":
        derived_sources = {
            GeometrySource.PROJECTION_DERIVED,
            GeometrySource.SECTION_DERIVED,
            GeometrySource.RENDERER_GENERATED,
        }
        if self.source in derived_sources and not self.reason:
            raise ValueError("derived geometries must include a reason")
        return self


class LineGeometry(BaseGeometry):
    type: Literal["LINE"] = "LINE"
    coords: tuple[float, float, float, float]


class CircleGeometry(BaseGeometry):
    type: Literal["CIRCLE"] = "CIRCLE"
    center: tuple[float, float]
    radius: float = Field(gt=0)
    is_hole: bool = False


class ArcGeometry(BaseGeometry):
    type: Literal["ARC"] = "ARC"
    center: tuple[float, float]
    radius: float = Field(gt=0)
    start_angle: float
    end_angle: float


class PolylineGeometry(BaseGeometry):
    type: Literal["POLYLINE"] = "POLYLINE"
    points: list[tuple[float, float]] = Field(min_length=2)
    closed: bool = False


class HatchGeometry(BaseGeometry):
    type: Literal["HATCH"] = "HATCH"
    segments: list[tuple[float, float, float, float]] = Field(min_length=1)


class TextGeometry(BaseGeometry):
    type: Literal["TEXT"] = "TEXT"
    line_style: LineStyle = LineStyle.TEXT_SYMBOL
    position: tuple[float, float]
    text: str = Field(min_length=1)
    size: float = Field(gt=0, default=14.0)


Geometry = Annotated[
    Union[
        LineGeometry,
        CircleGeometry,
        ArcGeometry,
        PolylineGeometry,
        HatchGeometry,
        TextGeometry,
    ],
    Field(discriminator="type"),
]


class GateAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_1: Literal["PENDING", "PASS", "FAIL"] = "PENDING"
    gate_2: Literal["PENDING", "PASS", "FAIL"] = "PENDING"
    gate_3: Literal["PENDING", "PASS", "FAIL"] = "PENDING"
    gate_4: Literal["PENDING", "PASS", "FAIL"] = "PENDING"


class TaskDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    task_type: TaskType = TaskType.UNKNOWN
    coordinate_system: CoordinateSystem = Field(default_factory=CoordinateSystem)
    views: list[ViewBox] = Field(default_factory=list)
    geometries: list[Geometry] = Field(default_factory=list)
    audit: GateAudit = Field(default_factory=GateAudit)
    uncertain_fields: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_geometry_views(self) -> "TaskDocument":
        view_ids = {view.id for view in self.views}
        for geometry in self.geometries:
            if geometry.belongs_to_view and geometry.belongs_to_view not in view_ids:
                raise ValueError(
                    f"geometry {geometry.id} references unknown view {geometry.belongs_to_view}"
                )
        return self


def validate_task_document(data: dict) -> TaskDocument:
    return TaskDocument.model_validate(data)

