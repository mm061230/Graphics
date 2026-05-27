from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from core.geometry_schema import TaskType


STRUCTURED_READER_PROMPT_TEMPLATE = """\
Return JSON only. Use OCR text, image summary, and candidate metadata to infer:
problem_id, task_type, target_view, section_label, confidence, uncertain_fields.
Do not modify final geometry. Mark uncertain fields instead of guessing.

OCR_TEXT:
{ocr_text}

IMAGE_SUMMARY:
{image_summary}

CANDIDATE_METADATA:
{candidate_metadata}
"""


@dataclass(frozen=True)
class OCRResult:
    text: str
    engine: str = "tesseract"
    engine_available: bool = False
    error: str | None = None


@dataclass(frozen=True)
class RequirementResult:
    problem_id: str | None = None
    task_type: TaskType = TaskType.UNKNOWN
    target_view: str | None = None
    section_label: str | None = None
    confidence: float = 0.0
    uncertain_fields: list[str] = field(default_factory=list)

    def to_payload(self) -> dict:
        return {
            "problem_id": self.problem_id,
            "task_type": self.task_type.value,
            "target_view": self.target_view,
            "section_label": self.section_label,
            "confidence": self.confidence,
            "uncertain_fields": self.uncertain_fields,
        }


def infer_requirement_from_text(text: str) -> RequirementResult:
    normalized = text.strip().upper()
    uncertain: list[str] = []
    task_type = TaskType.UNKNOWN
    confidence = 0.2 if normalized else 0.0
    problem_id = _detect_problem_id(text)

    if any(keyword in normalized for keyword in ["补线", "MISSING LINE"]):
        task_type = TaskType.MISSING_LINE
        confidence = 0.75
    elif any(keyword in normalized for keyword in ["半剖", "HALF SECTION"]):
        task_type = TaskType.HALF_SECTION
        confidence = 0.75
    elif any(keyword in normalized for keyword in ["全剖", "FULL SECTION"]):
        task_type = TaskType.FULL_SECTION
        confidence = 0.75
    elif any(keyword in normalized for keyword in ["局部剖", "LOCAL SECTION"]):
        task_type = TaskType.LOCAL_SECTION
        confidence = 0.75
    elif any(keyword in normalized for keyword in ["旋转剖", "ROTATED SECTION"]):
        task_type = TaskType.ROTATED_SECTION
        confidence = 0.75
    elif any(keyword in normalized for keyword in ["阶梯剖", "STEPPED SECTION"]):
        task_type = TaskType.STEPPED_SECTION
        confidence = 0.75
    elif any(keyword in normalized for keyword in ["断面", "CROSS SECTION"]):
        task_type = TaskType.CROSS_SECTION
        confidence = 0.7
    else:
        uncertain.append("task_type")

    section_label = None
    for label in ["A-A", "B-B", "C-C"]:
        if label in normalized:
            section_label = label
            break
    if task_type in {
        TaskType.FULL_SECTION,
        TaskType.HALF_SECTION,
        TaskType.LOCAL_SECTION,
        TaskType.ROTATED_SECTION,
        TaskType.STEPPED_SECTION,
    } and not section_label:
        uncertain.append("section_label")

    return RequirementResult(
        problem_id=problem_id,
        task_type=task_type,
        target_view=_detect_target_view(text),
        section_label=section_label,
        confidence=confidence,
        uncertain_fields=uncertain,
    )


def build_structured_reader_prompt(
    ocr_text: str,
    image_summary: dict,
    candidate_metadata: dict,
) -> str:
    return STRUCTURED_READER_PROMPT_TEMPLATE.format(
        ocr_text=ocr_text,
        image_summary=json.dumps(image_summary, ensure_ascii=False, sort_keys=True),
        candidate_metadata=json.dumps(candidate_metadata, ensure_ascii=False, sort_keys=True),
    )


def parse_structured_requirement_output(raw_output: str) -> RequirementResult:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ValueError("structured reader output must be JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("structured reader output must be a JSON object")
    try:
        task_type = TaskType(payload.get("task_type", "UNKNOWN"))
    except ValueError as exc:
        raise ValueError(f"unknown task_type: {payload.get('task_type')}") from exc
    uncertain_fields = payload.get("uncertain_fields", [])
    if not isinstance(uncertain_fields, list) or not all(
        isinstance(value, str) for value in uncertain_fields
    ):
        raise ValueError("uncertain_fields must be a list of strings")
    confidence = float(payload.get("confidence", 0.0))
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    return RequirementResult(
        problem_id=payload.get("problem_id"),
        task_type=task_type,
        target_view=payload.get("target_view"),
        section_label=payload.get("section_label"),
        confidence=confidence,
        uncertain_fields=uncertain_fields,
    )


def _detect_problem_id(text: str) -> str | None:
    patterns = [
        r"第\s*([0-9]+(?:[-.][0-9]+)?)\s*[题題]",
        r"(?:题号|題號|PROBLEM|NO\.?)\s*[:：]?\s*([0-9]+(?:[-.][0-9]+)?)",
        r"^\s*([0-9]+(?:[-.][0-9]+)?)\s*[.、)]",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _detect_target_view(text: str) -> str | None:
    normalized = text.upper()
    if any(keyword in normalized for keyword in ["左视", "LEFT VIEW"]):
        return "LEFT"
    if any(keyword in normalized for keyword in ["俯视", "TOP VIEW"]):
        return "TOP"
    if any(keyword in normalized for keyword in ["主视", "FRONT VIEW"]):
        return "FRONT"
    return None


def extract_text_from_image(image_path: Path, languages: str = "chi_sim+eng") -> OCRResult:
    executable = shutil.which("tesseract")
    if executable is None:
        return OCRResult(text="", engine_available=False, error="tesseract executable not found")
    completed = subprocess.run(
        [executable, str(image_path), "stdout", "-l", languages],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return OCRResult(
            text="",
            engine_available=True,
            error=completed.stderr.strip() or "tesseract failed",
        )
    return OCRResult(text=completed.stdout.strip(), engine_available=True)


def read_requirement_from_image(image_path: Path) -> tuple[OCRResult, RequirementResult]:
    ocr = extract_text_from_image(image_path)
    requirement = infer_requirement_from_text(ocr.text)
    if not ocr.engine_available and "ocr_engine" not in requirement.uncertain_fields:
        requirement = RequirementResult(
            problem_id=requirement.problem_id,
            task_type=requirement.task_type,
            target_view=requirement.target_view,
            section_label=requirement.section_label,
            confidence=requirement.confidence,
            uncertain_fields=[*requirement.uncertain_fields, "ocr_engine"],
        )
    return ocr, requirement
