from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from core.quality_gate import run_gate_2_checks, run_gate_3_checks
from core.release_manifest import verify_release_manifest
from core.task_runner import (
    build_package_temp_root,
    build_result_package_dir,
    prepare_two_task_page,
    run_from_geometry,
    run_image_gate_1,
)
from core.task_state import TaskState
from core import ALLOWED_IMAGE_SUFFIXES


def _validate_image_path(value: str) -> Path:
    path = Path(value)
    if path.suffix.lower() not in ALLOWED_IMAGE_SUFFIXES:
        raise argparse.ArgumentTypeError(
            f"unsupported image format: {path.suffix!r}. Allowed: {sorted(ALLOWED_IMAGE_SUFFIXES)}"
        )
    return path


def _validate_task_id(value: str) -> str:
    if not value or not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        raise argparse.ArgumentTypeError(
            f"task_id must contain only alphanumeric, underscore, hyphen: {value!r}"
        )
    if value.startswith('.'):
        raise argparse.ArgumentTypeError(f"task_id must not start with dot: {value!r}")
    return value


def _validate_output_basename(value: str) -> str:
    if not value or '\\' in value or '/' in value or '..' in value:
        raise argparse.ArgumentTypeError(
            f"output-basename must not contain path separators or traversal: {value!r}"
        )
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Plan1 military-gated mechanical drawing pipeline."
    )
    parser.add_argument("--image", type=_validate_image_path, help="Input phone/photo image path.")
    parser.add_argument("--task-id", default="task_001", type=_validate_task_id, help="Stable task id.")
    parser.add_argument("--task-type", default="UNKNOWN", help="Known task type if available.")
    parser.add_argument("--geometry-json", type=Path, help="Validated geometry JSON for rendering.")
    parser.add_argument("--verify-manifest", type=Path, help="Verify an existing release manifest.")
    parser.add_argument(
        "--split-page-halves",
        action="store_true",
        help="Normalize a two-task landscape page and write task25/task26 inputs into result/<source>/.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("result"),
        help="User-visible result directory.",
    )
    parser.add_argument(
        "--output-package-dir",
        type=Path,
        help="Exact package directory for final outputs, such as result/<source>/<task>/final.",
    )
    parser.add_argument("--review-mark", type=Path, help="Review mark file to bind into manifest.")
    parser.add_argument(
        "--output-basename",
        type=_validate_output_basename,
        help="Output file stem. Defaults to task id; use source image stem to preserve file names.",
    )
    parser.add_argument(
        "--gate",
        choices=["GATE_1", "GATE_2", "GATE_3", "GATE_4", "ALL"],
        default="ALL",
        help="Gate to run. Current bootstrap only validates ordering.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without running gates.")
    return parser


def _detect_temp_root(path: Path) -> Path | None:
    for parent in [path.parent, *path.parents]:
        if parent.name == "_temp":
            return parent
    return None


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.verify_manifest:
        manifest = verify_release_manifest(args.verify_manifest)
        print(f"manifest_verified=True task_id={manifest['task_id']}")
        return 0

    if args.split_page_halves:
        if not args.image:
            parser.error("--split-page-halves requires --image")
        prepared = prepare_two_task_page(args.image, output_root=args.output_root)
        print(f"package_root={prepared.package_root}")
        print(f"source_copy={prepared.source_copy}")
        print(f"normalized_image={prepared.normalized_image}")
        for task_input in prepared.task_inputs:
            print(f"task_input={task_input}")
        return 0

    if args.image and not args.image.exists():
        state = TaskState(args.task_id)
        state.ensure()
        state.fail_gate("GATE_1", f"input image does not exist: {args.image}")
        parser.error(f"input image does not exist: {args.image}")

    if args.dry_run:
        print(f"dry-run ok: task_id={args.task_id}, task_type={args.task_type}, gate={args.gate}")
        return 0

    if args.geometry_json:
        if not args.geometry_json.exists():
            parser.error(f"geometry json does not exist: {args.geometry_json}")
        temp_root = _detect_temp_root(args.geometry_json)
        state_root = temp_root / "state" if temp_root else Path("work/state")
        audit_root = temp_root / "audit_logs" if temp_root else Path("work/audit_logs")
        state = TaskState(args.task_id, root=state_root, audit_root=audit_root)
        state.ensure()
        output_package_dir = args.output_package_dir
        if temp_root and output_package_dir is None and args.gate == "GATE_4":
            output_package_dir = temp_root.parent
        if args.gate == "GATE_1":
            parser.error("GATE_1 requires --image input, not --geometry-json")
        if args.gate == "GATE_2":
            result = run_gate_2_checks(
                args.task_id,
                args.geometry_json,
                state_root=state_root,
                audit_root=audit_root,
            )
            print(f"{result.gate} passed={result.passed}")
            for message in result.messages:
                print(message)
            return 0 if result.passed else 1
        if args.gate == "GATE_3":
            result = run_gate_3_checks(
                args.task_id,
                args.geometry_json,
                state_root=state_root,
                audit_root=audit_root,
            )
            print(f"{result.gate} passed={result.passed}")
            for message in result.messages:
                print(message)
            return 0 if result.passed else 1
        result = run_from_geometry(
            args.task_id,
            args.geometry_json,
            output_root=args.output_root,
            output_basename=args.output_basename,
            output_package_dir=output_package_dir,
            review_mark=args.review_mark,
            state_root=state_root,
            audit_root=audit_root,
        )
        print(f"released={result.released}")
        for output in result.outputs:
            print(output)
        print(result.report)
        return 0 if result.released else 1

    if args.image and args.gate in {"GATE_1", "ALL"}:
        package_root = build_result_package_dir(args.image, output_root=args.output_root)
        temp_root = build_package_temp_root(args.image, output_root=args.output_root)
        state_root = temp_root / "state"
        audit_root = temp_root / "audit_logs"

        gate1_json = run_image_gate_1(
            args.task_id,
            args.image,
            work_root=temp_root,
            state_root=state_root,
            audit_root=audit_root,
        )
        print(f"package_root={package_root}")
        print(f"gate1_json={gate1_json}")
        if args.gate == "GATE_1":
            return 0

        from core.requirement_reader import run_structured_reader

        req_result = run_structured_reader(args.image)
        if req_result.task_type.value != "UNKNOWN" or req_result.problem_id:
            gate1_payload = json.loads(gate1_json.read_text(encoding="utf-8"))
            gate1_payload.update(req_result.to_payload())
            gate1_json.write_text(
                json.dumps(gate1_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"requirement={req_result.to_payload()}")

        from core.gate_bridge import bridge_gate1_to_gate2, bridge_gate2_to_gate3

        gate2_json = bridge_gate1_to_gate2(gate1_json)
        print(f"gate2_json={gate2_json}")
        gate2_result = run_gate_2_checks(
            args.task_id, gate2_json,
            state_root=state_root, audit_root=audit_root,
        )
        print(f"{gate2_result.gate} passed={gate2_result.passed}")
        for message in gate2_result.messages:
            print(message)
        if not gate2_result.passed:
            return 1

        gate3_json = bridge_gate2_to_gate3(gate2_json)
        print(f"gate3_json={gate3_json}")
        gate3_result = run_gate_3_checks(
            args.task_id, gate3_json,
            state_root=state_root, audit_root=audit_root,
        )
        print(f"{gate3_result.gate} passed={gate3_result.passed}")
        for message in gate3_result.messages:
            print(message)
        if not gate3_result.passed:
            return 1

        result = run_from_geometry(
            args.task_id, gate3_json,
            output_root=args.output_root,
            output_basename=args.output_basename,
            output_package_dir=package_root,
            review_mark=args.review_mark,
            state_root=state_root,
            audit_root=audit_root,
        )
        print(f"released={result.released}")
        for output in result.outputs:
            print(output)
        print(result.report)
        return 0 if result.released else 1

    if args.gate != "ALL":
        state = TaskState(args.task_id)
        state.ensure()
        state.assert_gate_can_run(args.gate)
        print(f"{args.gate} can run for task {args.task_id}")
        return 0

    print("no actionable arguments; use --help for usage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
