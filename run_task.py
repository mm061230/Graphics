from __future__ import annotations

import argparse
from pathlib import Path

from core.quality_gate import run_gate_2_checks, run_gate_3_checks
from core.release_manifest import verify_release_manifest
from core.task_runner import run_from_geometry, run_image_gate_1
from core.task_state import TaskState


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Plan1 military-gated mechanical drawing pipeline."
    )
    parser.add_argument("--image", type=Path, help="Input phone/photo image path.")
    parser.add_argument("--task-id", default="task_001", help="Stable task id.")
    parser.add_argument("--task-type", default="UNKNOWN", help="Known task type if available.")
    parser.add_argument("--geometry-json", type=Path, help="Validated geometry JSON for rendering.")
    parser.add_argument("--verify-manifest", type=Path, help="Verify an existing release manifest.")
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


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.verify_manifest:
        manifest = verify_release_manifest(args.verify_manifest)
        print(f"manifest_verified=True task_id={manifest['task_id']}")
        return 0

    state = TaskState(args.task_id)
    state.ensure()

    if args.image and not args.image.exists():
        state.fail_gate("GATE_1", f"input image does not exist: {args.image}")
        parser.error(f"input image does not exist: {args.image}")

    if args.dry_run:
        print(f"dry-run ok: task_id={args.task_id}, task_type={args.task_type}, gate={args.gate}")
        return 0

    if args.geometry_json:
        if not args.geometry_json.exists():
            parser.error(f"geometry json does not exist: {args.geometry_json}")
        if args.gate == "GATE_1":
            parser.error("GATE_1 requires --image input, not --geometry-json")
        if args.gate == "GATE_2":
            result = run_gate_2_checks(args.task_id, args.geometry_json)
            print(f"{result.gate} passed={result.passed}")
            for message in result.messages:
                print(message)
            return 0 if result.passed else 1
        if args.gate == "GATE_3":
            result = run_gate_3_checks(args.task_id, args.geometry_json)
            print(f"{result.gate} passed={result.passed}")
            for message in result.messages:
                print(message)
            return 0 if result.passed else 1
        result = run_from_geometry(
            args.task_id,
            args.geometry_json,
            output_root=args.output_root,
            output_basename=args.output_basename,
            output_package_dir=args.output_package_dir,
            review_mark=args.review_mark,
        )
        print(f"released={result.released}")
        for output in result.outputs:
            print(output)
        print(result.report)
        return 0 if result.released else 1

    if args.image and args.gate in {"GATE_1", "ALL"}:
        gate1_json = run_image_gate_1(args.task_id, args.image)
        print(f"gate1_json={gate1_json}")
        if args.gate == "GATE_1":
            return 0

    if args.gate != "ALL":
        state.assert_gate_can_run(args.gate)
        print(f"{args.gate} can run for task {args.task_id}")
        return 0

    print("bootstrap ready: full gate execution will be implemented in later phases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
