from __future__ import annotations

import shutil
import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from core.geometry_schema import TaskDocument
from core import ALLOWED_IMAGE_SUFFIXES


def _validate_image_suffix(path: Path) -> None:
    if path.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
        raise ValueError(
            f"unsupported image format: {path.suffix!r}. "
            f"Allowed: {sorted(ALLOWED_IMAGE_SUFFIXES)}"
        )


@dataclass(frozen=True)
class ImageQualityMetrics:
    width: int
    height: int
    gray_contrast: float
    rotation_theta_deg: float
    detected_line_count: int
    detected_circle_count: int


@dataclass(frozen=True)
class VisionResult:
    original_copy: Path
    corrected_image: Path
    enhanced_image: Path
    metrics: ImageQualityMetrics
    line_candidates: list[tuple[float, float, float, float]]
    circle_candidates: list[tuple[float, float, float]]
    contour_candidates: list[tuple[float, float, float, float]]
    view_box_candidates: list[tuple[float, float, float, float]]
    centerline_candidates: list[tuple[float, float, float, float]]

    def to_payload(self, task_id: str) -> dict:
        view_id = "IMAGE"
        geometries = []
        for index, (x1, y1, x2, y2) in enumerate(self.line_candidates, start=1):
            geometries.append(
                {
                    "id": f"LINE_CAND_{index:03d}",
                    "type": "LINE",
                    "line_style": "VISIBLE_OUTLINE",
                    "source": "opencv_candidate",
                    "belongs_to_view": view_id,
                    "confidence": 0.5,
                    "coords": [x1, y1, x2, y2],
                }
            )
        for index, (cx, cy, radius) in enumerate(self.circle_candidates, start=1):
            geometries.append(
                {
                    "id": f"CIRCLE_CAND_{index:03d}",
                    "type": "CIRCLE",
                    "line_style": "VISIBLE_OUTLINE",
                    "source": "opencv_candidate",
                    "belongs_to_view": view_id,
                    "confidence": 0.5,
                    "center": [cx, cy],
                    "radius": radius,
                    "is_hole": False,
                }
            )

        payload = {
            "task_id": task_id,
            "task_type": "UNKNOWN",
            "coordinate_system": {
                "unit": "px",
                "canvas_width": self.metrics.width,
                "canvas_height": self.metrics.height,
            },
            "views": [
                {
                    "id": view_id,
                    "type": "UNKNOWN",
                    "origin": [0, 0],
                    "center": [self.metrics.width / 2, self.metrics.height / 2],
                    "width": self.metrics.width,
                    "height": self.metrics.height,
                    "scale": 1.0,
                }
            ],
            "geometries": geometries,
            "audit": {
                "gate_1": "PENDING",
                "gate_2": "PENDING",
                "gate_3": "PENDING",
                "gate_4": "PENDING",
            },
            "image_metrics": {
                "width": self.metrics.width,
                "height": self.metrics.height,
                "gray_contrast": self.metrics.gray_contrast,
                "rotation_theta_deg": self.metrics.rotation_theta_deg,
                "detected_line_count": self.metrics.detected_line_count,
                "detected_circle_count": self.metrics.detected_circle_count,
            },
            "vision_artifacts": {
                "original_copy": str(self.original_copy),
                "corrected_image": str(self.corrected_image),
                "enhanced_image": str(self.enhanced_image),
            },
            "raw_features": {
                "line_candidates_count": len(self.line_candidates),
                "circle_candidates_count": len(self.circle_candidates),
                "contour_candidates": self.contour_candidates,
                "view_box_candidates": self.view_box_candidates,
                "centerline_candidates": self.centerline_candidates,
            },
        }
        TaskDocument.model_validate(
            {key: value for key, value in payload.items() if key in TaskDocument.model_fields}
        )
        return payload


@dataclass(frozen=True)
class PageSplitResult:
    normalized_image: Path
    task_images: list[Path]


def process_image(
    image_path: Path,
    task_id: str,
    work_root: Path = Path("work"),
) -> VisionResult:
    if not image_path.exists():
        raise FileNotFoundError(f"input image does not exist: {image_path}")
    _validate_image_suffix(image_path)

    original_dir = work_root / "original"
    corrected_dir = work_root / "corrected"
    enhanced_dir = work_root / "enhanced"
    original_dir.mkdir(parents=True, exist_ok=True)
    corrected_dir.mkdir(parents=True, exist_ok=True)
    enhanced_dir.mkdir(parents=True, exist_ok=True)

    original_copy = original_dir / f"{task_id}{image_path.suffix.lower()}"
    shutil.copy2(image_path, original_copy)

    image = _read_image(image_path)
    if image is None:
        raise ValueError(f"OpenCV could not read image: {image_path}")

    corrected = _deskew_image(_perspective_correct(image))
    gray = cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY)
    enhanced = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        21,
        8,
    )

    corrected_image = corrected_dir / f"{task_id}_corrected.png"
    enhanced_image = enhanced_dir / f"{task_id}_enhanced.png"
    _write_image(corrected_image, corrected)
    _write_image(enhanced_image, enhanced)

    lines = _detect_lines(enhanced)
    circles = _detect_circles(gray)
    contours = _detect_contour_boxes(enhanced)
    view_boxes = _detect_view_boxes(contours, image.shape[1], image.shape[0])
    centerlines = _estimate_centerline_candidates(lines)
    metrics = ImageQualityMetrics(
        width=int(image.shape[1]),
        height=int(image.shape[0]),
        gray_contrast=float(gray.std()),
        rotation_theta_deg=_estimate_rotation_deg(image),
        detected_line_count=len(lines),
        detected_circle_count=len(circles),
    )
    return VisionResult(
        original_copy=original_copy,
        corrected_image=corrected_image,
        enhanced_image=enhanced_image,
        metrics=metrics,
        line_candidates=lines,
        circle_candidates=circles,
        contour_candidates=contours,
        view_box_candidates=view_boxes,
        centerline_candidates=centerlines,
    )


def write_gate1_candidate_json(
    image_path: Path,
    task_id: str,
    work_root: Path = Path("work"),
) -> Path:
    result = process_image(image_path, task_id, work_root=work_root)
    output_dir = work_root / "geometry_json"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{task_id}_gate1.json"
    output_path.write_text(
        json.dumps(result.to_payload(task_id), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def normalize_landscape_page(image_path: Path, output_path: Path) -> Path:
    image = _read_image(image_path)
    if image is None:
        raise ValueError(f"OpenCV could not read image: {image_path}")
    normalized = _normalize_landscape_orientation(image)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_image(output_path, normalized)
    return output_path


def split_landscape_page_halves(
    image_path: Path,
    output_dir: Path,
    output_stem: str | None = None,
) -> PageSplitResult:
    image = _read_image(image_path)
    if image is None:
        raise ValueError(f"OpenCV could not read image: {image_path}")
    normalized = _normalize_landscape_orientation(image)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_stem or image_path.stem

    normalized_path = output_dir / f"{stem}_normalized.png"
    _write_image(normalized_path, normalized)

    split_x = _detect_vertical_page_split(normalized)
    left = normalized[:, :split_x]
    right = normalized[:, split_x:]

    task_images = [
        output_dir / f"{stem}_task25.png",
        output_dir / f"{stem}_task26.png",
    ]
    _write_image(task_images[0], left)
    _write_image(task_images[1], right)
    return PageSplitResult(normalized_image=normalized_path, task_images=task_images)


def _detect_lines(binary_image) -> list[tuple[float, float, float, float]]:
    edges = cv2.Canny(binary_image, 50, 150, apertureSize=3)
    raw = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=40,
        minLineLength=30,
        maxLineGap=5,
    )
    if raw is None:
        return []
    return [tuple(float(value) for value in line[0]) for line in raw[:200]]


def _normalize_landscape_orientation(image):
    if image.shape[0] > image.shape[1]:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    return image


def _detect_vertical_page_split(image) -> int:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 210, 255, cv2.THRESH_BINARY_INV)
    height, width = binary.shape
    center_min = int(width * 0.35)
    center_max = int(width * 0.65)
    column_scores = binary[:, center_min:center_max].sum(axis=0)
    if column_scores.size == 0:
        return width // 2
    center = width / 2
    candidates = np.arange(center_min, center_max)
    distance_penalty = np.abs(candidates - center) * 255 * 0.15
    weighted_scores = column_scores - distance_penalty
    candidate = int(weighted_scores.argmax()) + center_min
    score = int(column_scores[candidate - center_min])
    if score < height * 255 * 0.2:
        return width // 2
    return max(int(width * 0.2), min(int(width * 0.8), candidate))


def _detect_circles(gray_image) -> list[tuple[float, float, float]]:
    blurred = cv2.medianBlur(gray_image, 5)
    raw = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=20,
        param1=80,
        param2=30,
        minRadius=5,
        maxRadius=0,
    )
    if raw is None:
        return []
    circles = np.round(raw[0, :]).astype(float)
    return [tuple(circle) for circle in circles[:100]]


def _detect_contour_boxes(binary_image) -> list[tuple[float, float, float, float]]:
    inverted = cv2.bitwise_not(binary_image)
    contours, _ = cv2.findContours(inverted, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: list[tuple[float, float, float, float]] = []
    image_area = binary_image.shape[0] * binary_image.shape[1]
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < image_area * 0.001:
            continue
        boxes.append((float(x), float(y), float(w), float(h)))
    boxes.sort(key=lambda box: box[2] * box[3], reverse=True)
    return boxes[:50]


def _detect_view_boxes(
    contour_boxes: list[tuple[float, float, float, float]],
    image_width: int,
    image_height: int,
) -> list[tuple[float, float, float, float]]:
    min_area = image_width * image_height * 0.01
    max_area = image_width * image_height * 0.8
    candidates = [
        box
        for box in contour_boxes
        if min_area <= box[2] * box[3] <= max_area and box[2] > 30 and box[3] > 30
    ]
    return candidates[:12]


def _estimate_centerline_candidates(
    lines: list[tuple[float, float, float, float]],
) -> list[tuple[float, float, float, float]]:
    centerlines = []
    for line in lines:
        x1, y1, x2, y2 = line
        length = float(np.hypot(x2 - x1, y2 - y1))
        if length < 80:
            continue
        is_horizontal = abs(y2 - y1) <= 2
        is_vertical = abs(x2 - x1) <= 2
        if is_horizontal or is_vertical:
            centerlines.append(line)
    return centerlines[:50]


def _estimate_rotation_deg(image) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    raw = cv2.HoughLines(edges, 1, np.pi / 180, 120)
    if raw is None:
        return 0.0
    angles = []
    for rho_theta in raw[:50]:
        _, theta = rho_theta[0]
        deg = theta * 180 / np.pi
        normalized = ((deg + 45) % 90) - 45
        angles.append(normalized)
    return float(np.median(angles)) if angles else 0.0


def _deskew_image(image):
    angle = _estimate_rotation_deg(image)
    if abs(angle) < 0.1:
        return image
    height, width = image.shape[:2]
    center = (width / 2, height / 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_LINEAR, borderValue=(255, 255, 255))


def _perspective_correct(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return image

    image_area = image.shape[0] * image.shape[1]
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    for contour in contours[:10]:
        area = cv2.contourArea(contour)
        if area < image_area * 0.15:
            continue
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) != 4:
            continue
        points = _order_quad_points(approx.reshape(4, 2).astype("float32"))
        width_a = np.linalg.norm(points[2] - points[3])
        width_b = np.linalg.norm(points[1] - points[0])
        height_a = np.linalg.norm(points[1] - points[2])
        height_b = np.linalg.norm(points[0] - points[3])
        max_width = int(max(width_a, width_b))
        max_height = int(max(height_a, height_b))
        if max_width < 50 or max_height < 50:
            continue
        destination = np.array(
            [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
            dtype="float32",
        )
        matrix = cv2.getPerspectiveTransform(points, destination)
        return cv2.warpPerspective(image, matrix, (max_width, max_height), borderValue=(255, 255, 255))
    return image


def _order_quad_points(points):
    rect = np.zeros((4, 2), dtype="float32")
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1)
    rect[0] = points[np.argmin(sums)]
    rect[2] = points[np.argmax(sums)]
    rect[1] = points[np.argmin(diffs)]
    rect[3] = points[np.argmax(diffs)]
    return rect


def _read_image(path: Path):
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    return image


def _write_image(path: Path, image) -> None:
    suffix = path.suffix or ".png"
    ok, encoded = cv2.imencode(suffix, image)
    if not ok:
        raise ValueError(f"OpenCV could not encode image: {path}")
    path.write_bytes(encoded.tobytes())
