from core.geometry_schema import TaskType
from core.requirement_reader import (
    build_structured_reader_prompt,
    extract_text_from_image,
    infer_requirement_from_text,
    parse_structured_requirement_output,
)


def test_infer_half_section_with_label():
    result = infer_requirement_from_text("求 A-A 半剖视图")
    assert result.task_type == TaskType.HALF_SECTION
    assert result.section_label == "A-A"
    assert result.confidence > 0.7
    assert not result.uncertain_fields


def test_unknown_text_records_uncertain_task_type():
    result = infer_requirement_from_text("请完成下图")
    assert result.task_type == TaskType.UNKNOWN
    assert "task_type" in result.uncertain_fields


def test_missing_ocr_engine_is_reported(monkeypatch, tmp_path):
    monkeypatch.setattr("core.requirement_reader.shutil.which", lambda _: None)
    result = extract_text_from_image(tmp_path / "missing.png")
    assert not result.engine_available
    assert result.error


def test_problem_id_and_target_view_are_detected():
    result = infer_requirement_from_text("第12题 求 A-A 全剖左视图")
    assert result.problem_id == "12"
    assert result.target_view == "LEFT"
    assert result.task_type == TaskType.FULL_SECTION


def test_structured_reader_prompt_limits_ai_authority():
    prompt = build_structured_reader_prompt(
        "第3题 求半剖",
        {"width": 1200},
        {"line_candidates_count": 10},
    )
    assert "Return JSON only" in prompt
    assert "Do not modify final geometry" in prompt


def test_structured_reader_rejects_non_json():
    try:
        parse_structured_requirement_output("task_type: HALF_SECTION")
    except ValueError as exc:
        assert "must be JSON" in str(exc)
    else:
        raise AssertionError("non-json output should fail")


def test_structured_reader_records_confidence_and_uncertain_fields():
    result = parse_structured_requirement_output(
        '{"problem_id":"7","task_type":"HALF_SECTION","confidence":0.62,'
        '"uncertain_fields":["section_label"]}'
    )
    assert result.problem_id == "7"
    assert result.confidence == 0.62
    assert result.uncertain_fields == ["section_label"]
