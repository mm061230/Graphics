# Project Rules

## User-Visible Results

```text
Canonical result directory: result/
```

Rules:

- Track only source code, tests, config, and long-lived docs in git.
- Keep `_ref/`, `input_images/`, `work/`, `result/`, and `output_results/` as local-only directories.
- User-facing output packages go under `result/`.
- Each source image owns one date-stamped package directory under `result/`.
- Each package directory contains exactly one `_temp/` subtree for non-final artifacts.
- Use `--output-package-dir` when a final package must land directly in a task `final/` directory.
- Use `--review-mark` for released tasks so the manifest binds the human review record.
- Preserve the source file stem when possible.
- Use the source extension only for the copied original; generated artifacts use their own extension.
- Add functional suffixes only for intermediate or audit artifacts, such as `_corrected`, `_enhanced`, `_gate1`, and `_audit_report`.
- Keep package-local `_temp/` for internal gate state, candidates, and audit scratch files.
- Keep GATE 1 candidate JSON, review marks, state tokens, and failure reports in `_temp/`, not beside final outputs.
- If one source image contains multiple tasks, first create normalized and per-task split images under `_temp/split/`, then run gates on the selected single-task image.
- Multi-task split images require visual acceptance before GATE 2. Failed split attempts must be treated as GATE 1 drill failures, not as final geometry.

Example for `1 (1).jpg`:

```text
result/1 (1)_20260528/_temp/original/1 (1).jpg
result/1 (1)_20260528/_temp/split/1 (1)_normalized.png
result/1 (1)_20260528/_temp/split/1 (1)_task25.png
result/1 (1)_20260528/_temp/geometry_json/1 (1)_task25_manual.json
result/1 (1)_20260528/1 (1)_task25_final.svg
result/1 (1)_20260528/1 (1)_task25_final.dxf
result/1 (1)_20260528/1 (1)_task25_final.png
result/1 (1)_20260528/1 (1)_task25_final.pdf
result/1 (1)_20260528/1 (1)_task25_final_audit_report.md
result/1 (1)_20260528/1 (1)_task25_final_release_manifest.json
```

Two-task page preparation command:

```text
python run_task.py --image "input_images/1 (1).jpg" --split-page-halves
```

Example release command:

```text
python run_task.py --task-id "1 (1)_task25" --geometry-json "result/1 (1)_20260528/_temp/geometry_json/1 (1)_task25_manual.json" --gate GATE_4 --output-basename "1 (1)_task25_final"
python run_task.py --verify-manifest "result/1 (1)_20260528/1 (1)_task25_final_release_manifest.json"
```
