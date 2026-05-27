from pathlib import Path
import json

import cv2
import numpy as np
import pytest

from core.geometry_schema import TaskDocument
from core.vision_pipeline import (
    normalize_landscape_page,
    process_image,
    split_landscape_page_halves,
    write_gate1_candidate_json,
)


def create_sample_image(path: Path) -> Path:
    image = np.full((220, 320, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (40, 50), (260, 170), (0, 0, 0), 2)
    cv2.line(image, (40, 110), (260, 110), (0, 0, 0), 1)
    cv2.circle(image, (150, 110), 30, (0, 0, 0), 2)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    path.write_bytes(encoded.tobytes())
    return path


def test_missing_image_fails(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        process_image(tmp_path / "missing.png", "missing_case", work_root=tmp_path / "work")


def test_sample_image_produces_outputs_and_candidates(tmp_path: Path):
    image = create_sample_image(tmp_path / "sample.png")
    result = process_image(image, "sample_case", work_root=tmp_path / "work")

    assert result.original_copy.exists()
    assert result.corrected_image.exists()
    assert result.enhanced_image.exists()
    assert result.metrics.width == 320
    assert result.metrics.height == 220
    assert result.metrics.gray_contrast > 0
    assert result.line_candidates
    assert result.contour_candidates
    assert result.centerline_candidates


def test_gate1_candidate_json_validates_schema(tmp_path: Path):
    image = create_sample_image(tmp_path / "sample.png")
    output = write_gate1_candidate_json(image, "candidate_case", work_root=tmp_path / "work")

    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    task_payload = {key: value for key, value in payload.items() if key in TaskDocument.model_fields}
    document = TaskDocument.model_validate(task_payload)
    assert document.task_id == "candidate_case"
    assert document.views
    assert document.geometries
    assert "image_metrics" in payload
    assert "raw_features" in payload
    assert payload["raw_features"]["contour_candidates"]


def test_perspective_like_page_still_processes(tmp_path: Path):
    image = np.full((260, 360, 3), 255, dtype=np.uint8)
    points = np.array([[60, 40], [310, 60], [290, 220], [40, 210]], dtype=np.int32)
    cv2.polylines(image, [points], isClosed=True, color=(0, 0, 0), thickness=3)
    cv2.line(image, (90, 100), (250, 110), (0, 0, 0), 2)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    path = tmp_path / "skewed.png"
    path.write_bytes(encoded.tobytes())

    result = process_image(path, "skewed_case", work_root=tmp_path / "work")

    assert result.corrected_image.exists()
    assert result.metrics.width == 360


def test_landscape_page_normalization_and_split(tmp_path: Path):
    image = np.full((400, 260, 3), 255, dtype=np.uint8)
    cv2.rectangle(image, (20, 20), (240, 380), (0, 0, 0), 2)
    cv2.line(image, (130, 20), (130, 380), (0, 0, 0), 2)
    cv2.circle(image, (75, 200), 30, (0, 0, 0), 2)
    cv2.rectangle(image, (165, 170), (220, 230), (0, 0, 0), 2)
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    source = tmp_path / "page.png"
    source.write_bytes(encoded.tobytes())

    normalized = normalize_landscape_page(source, tmp_path / "normalized.png")
    split = split_landscape_page_halves(source, tmp_path / "result", output_stem="page")

    normalized_data = np.fromfile(str(normalized), dtype=np.uint8)
    normalized_image = cv2.imdecode(normalized_data, cv2.IMREAD_COLOR)
    assert normalized_image.shape[1] > normalized_image.shape[0]
    assert split.normalized_image.exists()
    assert len(split.task_images) == 2
    assert all(path.exists() for path in split.task_images)

    for index, task_image in enumerate(split.task_images, start=1):
        gate1_json = write_gate1_candidate_json(
            task_image,
            f"split_task_{index}",
            work_root=tmp_path / f"work_{index}",
        )
        payload = json.loads(gate1_json.read_text(encoding="utf-8"))
        TaskDocument.model_validate(
            {key: value for key, value in payload.items() if key in TaskDocument.model_fields}
        )
