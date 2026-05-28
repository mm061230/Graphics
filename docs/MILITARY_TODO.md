# Military TODO

## Status Legend

```text
[ ] Not started
[~] In progress
[x] Done
[!] Blocked
```

## Phase 0: Bootstrap

### 0.1 Project Directories

- [x] Create `input_images/`.
- [x] Create `work/original/`.
- [x] Create `work/corrected/`.
- [x] Create `work/enhanced/`.
- [x] Create `work/extracted/`.
- [x] Create `work/geometry_json/`.
- [x] Create `work/review_marks/`.
- [x] Create `work/state/`.
- [x] Create `work/audit_logs/`.
- [x] Create canonical `result/` output root.
- [x] Organize outputs by source image directory.
- [x] Organize task outputs by `input/`, `gate1/`, and `final/`.
- [x] Create `config/`.
- [x] Create `core/`.
- [x] Create `core/renderers/`.
- [x] Create `tests/`.

Acceptance:

```text
All required directories exist.
No output directory is manually skipped.
```

### 0.2 Python Project Setup

- [x] Create `pyproject.toml`.
- [x] Add runtime dependencies:
  - `opencv-python`
  - `numpy`
  - `pydantic`
  - `shapely`
  - `ezdxf`
  - `drawsvg` or `svgwrite`
  - `cairosvg`
  - `pillow`
  - `pytest`
- [x] Add optional OCR dependency:
  - `paddleocr` or `pytesseract`
- [x] Add developer scripts:
  - `pytest`
  - `run-task`

Acceptance:

```text
python -m pytest can run.
python run_task.py --help can run.
```

### 0.3 Layer Config

- [x] Create `config/layers_config.json`.
- [x] Define `VISIBLE_OUTLINE`.
- [x] Define `HIDDEN_OUTLINE`.
- [x] Define `CENTERLINE`.
- [x] Define `HATCH_LINE`.
- [x] Define `WAVE_LINE`.
- [x] Define `TEXT_SYMBOL`.
- [x] Define render order.
- [x] Define line width.
- [x] Define color.
- [x] Define dash pattern.

Acceptance:

```text
Layer config loads successfully.
Unknown layer names are rejected.
Render order is deterministic.
```

## Phase 1: Schema and State Machine

### 1.1 Geometry Schema

- [x] Create `core/geometry_schema.py`.
- [x] Define `TaskDocument`.
- [x] Define `CoordinateSystem`.
- [x] Define `ViewBox`.
- [x] Define `LineGeometry`.
- [x] Define `CircleGeometry`.
- [x] Define `ArcGeometry`.
- [x] Define `PolylineGeometry`.
- [x] Define `HatchGeometry`.
- [x] Define `TextGeometry`.
- [x] Define allowed `line_style`.
- [x] Define allowed `source`.
- [x] Require every geometry to have `id`.
- [x] Require every geometry to have `belongs_to_view` when applicable.
- [x] Require derived geometries to have `reason`.

Acceptance:

```text
Invalid JSON fails validation.
Unknown line style fails validation.
Derived geometry without reason fails validation.
```

### 1.2 Schema Tests

- [x] Create `tests/test_schema.py`.
- [x] Test valid minimal task.
- [x] Test invalid line style.
- [x] Test missing geometry id.
- [x] Test missing reason for derived line.
- [x] Test unknown source rejection.

Acceptance:

```text
pytest tests/test_schema.py passes.
```

### 1.3 Task State

- [x] Create `core/task_state.py`.
- [x] Create task state directory per task.
- [x] Implement `write_token(task_id, token)`.
- [x] Implement `has_token(task_id, token)`.
- [x] Implement `fail_gate(task_id, gate, reason)`.
- [x] Implement `prevent_gate_skip`.
- [x] Persist state as JSON.

Acceptance:

```text
GATE 2 cannot run without GATE 1 token.
GATE 3 cannot run without GATE 2 token.
GATE 4 cannot run without GATE 3 token.
```

## Phase 2: Deterministic Renderer

### 2.1 SVG Renderer

- [x] Create `core/renderers/svg_renderer.py`.
- [x] Load layer config.
- [x] Render line.
- [x] Render circle.
- [x] Render arc.
- [x] Render polyline.
- [x] Render hatch lines.
- [x] Render text.
- [x] Apply layer order.
- [x] Apply dash patterns.
- [x] Output white background.

Acceptance:

```text
Given sample geometry JSON, SVG is generated.
SVG contains expected layer groups.
Visible outline renders above centerline/hatch.
```

### 2.2 DXF Renderer

- [x] Create `core/renderers/dxf_renderer.py`.
- [x] Create DXF document.
- [x] Create layers.
- [x] Render lines.
- [x] Render circles.
- [x] Render arcs.
- [x] Render polylines.
- [x] Assign lineweight where supported.
- [x] Save DXF.

Acceptance:

```text
DXF opens in QCAD/LibreCAD.
Layers are visible and named consistently.
```

### 2.3 Export Converter

- [x] Create `core/renderers/export_converter.py`.
- [x] Convert SVG to PNG.
- [x] Convert SVG to PDF.
- [x] Validate output file exists.
- [x] Validate PNG dimensions.

Acceptance:

```text
SVG, PNG, PDF are generated from same geometry.
PNG has white background and readable lines.
```

### 2.4 Render Tests

- [x] Create `tests/test_render_outputs.py`.
- [x] Test SVG generation.
- [x] Test DXF generation.
- [x] Test PNG generation.
- [x] Test PDF generation.
- [x] Test layer names.

Acceptance:

```text
pytest tests/test_render_outputs.py passes.
```

## Phase 3: Quality Gate Engine

### 3.1 Gate Runner

- [x] Create `core/quality_gate.py`.
- [x] Implement `run_gate_1_checks`.
- [x] Implement `run_gate_2_checks`.
- [x] Implement `run_gate_3_checks`.
- [x] Implement `run_gate_4_checks`.
- [x] Write pass tokens only from code.
- [x] Write fail reports.

Acceptance:

```text
No gate can pass via AI text.
Only code can create token files.
```

### 3.2 CLI Entry

- [x] Create `run_task.py`.
- [x] Add `--image`.
- [x] Add `--task-id`.
- [x] Add `--task-type`.
- [x] Add `--gate`.
- [x] Add `--dry-run`.
- [x] Add `--help`.

Acceptance:

```text
python run_task.py --help works.
Invalid image path fails at GATE 1.
```

## Phase 4: Topology Engine

### 4.1 Section Boolean

- [x] Create `core/section_boolean.py`.
- [x] Convert geometry JSON to Shapely objects.
- [x] Build outer material polygons.
- [x] Build hole polygons.
- [x] Compute material region by difference.
- [x] Generate 45 degree hatch candidate lines.
- [x] Clip hatch lines to material region.
- [x] Return hatch geometry.

Acceptance:

```text
Hatch lines exist only inside material region.
Hatch lines do not enter holes.
```

### 4.2 Section Rules

- [x] Implement full section rule.
- [x] Implement half section rule.
- [x] Implement local section rule.
- [x] Implement rib exclusion hook.
- [x] Implement wave line air intersection check.

Acceptance:

```text
Hole intersection area is zero.
Rib hatch intersection area is zero when ribs are tagged.
```

### 4.3 Topology Tests

- [x] Create `tests/test_gate_3_section.py`.
- [x] Test simple rectangle hatch.
- [x] Test rectangle with circular hole.
- [x] Test rib exclusion.
- [x] Test invalid polygon failure.

Acceptance:

```text
pytest tests/test_gate_3_section.py passes.
```

## Phase 5: Projection Engine

### 5.1 View Coordinate Models

- [x] Create `core/projection_engine.py`.
- [x] Represent front view.
- [x] Represent top view.
- [x] Represent left view.
- [x] Store center anchors.
- [x] Store scale.
- [x] Validate same scale across views.

Acceptance:

```text
Views with inconsistent scale fail.
Missing view anchors fail when projection requires them.
```

### 5.2 Projection Audits

- [x] Implement length alignment check.
- [x] Implement height alignment check.
- [x] Implement width equality check.
- [x] Implement tolerance config.
- [x] Generate projection error report.

Acceptance:

```text
Known aligned sample passes.
Known misaligned sample fails with numeric error.
```

### 5.3 Missing Line Candidate

- [x] Detect unmatched projected features.
- [x] Generate missing line candidate.
- [x] Assign line style.
- [x] Attach reason.
- [x] Attach source `projection_derived`.

Acceptance:

```text
Every added line has reason.
No candidate can be added without projection basis.
```

### 5.4 Projection Tests

- [x] Create `tests/test_gate_2_projection.py`.
- [x] Test length alignment pass.
- [x] Test height alignment pass.
- [x] Test width equality pass.
- [x] Test misalignment failure.
- [x] Test derived line reason required.

Acceptance:

```text
pytest tests/test_gate_2_projection.py passes.
```

## Phase 6: Vision Intake

### 6.1 Image Pipeline

- [x] Create `core/vision_pipeline.py`.
- [x] Load image.
- [x] Backup original.
- [x] Compute resolution metrics.
- [x] Compute contrast metrics.
- [x] Estimate rotation.
- [x] Correct rotation.
- [x] Attempt perspective correction.
- [x] Save corrected image.
- [x] Save enhanced image.

Acceptance:

```text
Given a valid image, corrected and enhanced outputs exist.
Invalid image path fails cleanly.
```

### 6.2 Candidate Extraction

- [x] Detect line candidates.
- [x] Detect circle candidates.
- [x] Detect contour candidates.
- [x] Detect possible view boxes.
- [x] Estimate centerlines.
- [x] Store confidence scores.
- [x] Output gate1 candidate JSON.

Acceptance:

```text
Candidate JSON validates as GATE 1 candidate format.
Low confidence is recorded, not hidden.
```

### 6.3 Vision Tests

- [x] Create `tests/test_gate_1_input.py`.
- [x] Test missing image fails.
- [x] Test sample image produces corrected file.
- [x] Test candidate JSON schema.
- [x] Test multi-task split child images validate GATE 1 schema.

Acceptance:

```text
pytest tests/test_gate_1_input.py passes.
```

## Phase 7: Requirement Reader

### 7.1 OCR Integration

- [x] Create `core/requirement_reader.py`.
- [x] Extract text from corrected image.
- [x] Detect problem id.
- [x] Detect task type keywords.
- [x] Detect section labels.
- [x] Detect uncertain text.

Acceptance:

```text
Requirement reader returns structured JSON.
Unclear text is represented as uncertain, not guessed.
```

### 7.2 AI Structured Reader

- [x] Define prompt template.
- [x] Input only OCR text + low-res image summary + candidate metadata.
- [x] Output only JSON.
- [x] Reject non-JSON output.
- [x] Record confidence.
- [x] Record uncertain fields.

Acceptance:

```text
AI output cannot directly change final geometry.
AI output only updates requirement metadata or candidate patch.
```

## Phase 8: End-to-End

### 8.1 Task Runner

- [x] Create `core/task_runner.py`.
- [x] Run GATE 1.
- [x] Stop if GATE 1 fails.
- [x] Run GATE 2.
- [x] Stop if GATE 2 fails.
- [x] Run GATE 3.
- [x] Stop if GATE 3 fails.
- [x] Run GATE 4.
- [x] Output final package only after release token.

Acceptance:

```text
End-to-end never jumps gates.
Final files only exist after TOKEN_SYSTEM_RELEASE_RENDER.
```

### 8.2 Audit Report

- [x] Generate input quality section.
- [x] Generate requirement recognition section.
- [x] Generate geometry extraction section.
- [x] Generate projection audit section.
- [x] Generate topology audit section.
- [x] Generate output file section.
- [x] Generate unresolved uncertainty section.

Acceptance:

```text
Every final output has report.
Report contains pass/fail status for all gates.
```

### 8.3 First Real Image Drill

- [x] Choose one clear image from `_ref`.
- [x] Run GATE 1.
- [x] Inspect candidates.
- [x] Create or correct geometry JSON.
- [x] Run GATE 2.
- [x] Run GATE 3.
- [x] Run GATE 4.
- [x] Verify outputs visually.
- [x] Record all failures and fixes.

Acceptance:

```text
One complete task package exists in result.
All gate logs exist.
All tests pass for the task.
```

### 8.4 Second Real Image Drill

- [x] Choose accepted split image `result/1 (1)/task26/input/1 (1)_task26.png`.
- [x] Run GATE 1.
- [x] Inspect candidates.
- [x] Create or correct geometry JSON.
- [x] Run GATE 2.
- [x] Run GATE 3.
- [x] Run GATE 4.
- [x] Verify outputs visually.
- [x] Record all failures and fixes.

Acceptance:

```text
One complete task 26 package exists in result.
All gate tokens exist for task 26.
All tests pass for the task.
```

### 8.5 Release Manifest Hardening

- [x] Create `core/release_manifest.py`.
- [x] Validate release geometry JSON schema before manifesting.
- [x] Require all four gate tokens in release manifest.
- [x] Require SVG, DXF, PNG, PDF, and audit report in release manifest.
- [x] Record SHA-256 hashes for geometry and release outputs.
- [x] Link review mark when available.
- [x] Generate release manifest automatically from GATE 4 runner.
- [x] Add tests for complete release manifest.
- [x] Add tests for missing release token detection.
- [x] Generate manifests for task 25 and task 26 release packages.

Acceptance:

```text
Every release package can be machine-audited from a manifest.
Missing release token fails manifest completeness.
Existing task 25 and task 26 manifests report release_complete=true.
```

### 8.6 Global Audit V2

- [x] Commit v1 baseline locally.
- [x] Tag baseline as `v1.0.0`.
- [x] Switch to next-version branch `v2/global-audit`.
- [x] Audit final-output release ordering.
- [x] Fix final outputs being written before release token.
- [x] Add regression for failed release tests leaking no final outputs.
- [x] Audit CLI gate routing.
- [x] Fix `--geometry-json --gate GATE_1` fall-through.
- [x] Add regression for GATE 1 geometry JSON rejection.
- [x] Record global audit in `docs/GLOBAL_AUDIT_V2.md`.

Acceptance:

```text
GATE 4 writes user-visible final outputs only after release token.
GATE 1 cannot be entered through the geometry rendering path.
Global regression passes.
```

### 8.7 Audit Data Hardening

- [x] Audit GATE 2 projection audit defaults.
- [x] Reject missing `projection_audit`.
- [x] Reject incomplete `projection_audit`.
- [x] Audit GATE 3 topology audit defaults.
- [x] Reject missing `topology_audit`.
- [x] Reject incomplete or non-numeric topology audit values.
- [x] Add regression for missing GATE 2 audit.
- [x] Add regression for incomplete GATE 2 audit.
- [x] Add regression for missing GATE 3 audit.
- [x] Add regression for release manifest missing required output.

Acceptance:

```text
GATE 2 cannot pass without explicit projection audit evidence.
GATE 3 cannot pass without explicit topology audit evidence.
Release manifest cannot complete with any required output missing.
```

### 8.8 GATE 4 Pytest Evidence Hardening

- [x] Audit direct GATE 4 release path.
- [x] Reject missing pytest status outside pytest harness.
- [x] Preserve pytest harness recursion guard.
- [x] Add regression proving no release token is written without pytest status.

Acceptance:

```text
Production GATE 4 cannot release without pytest evidence.
Unit tests can still avoid recursive pytest execution.
```

### 8.9 Audit Numeric Hardening

- [x] Audit projection and topology numeric value semantics.
- [x] Reject negative audit values.
- [x] Add regression for negative GATE 2 projection audit value.

Acceptance:

```text
Audit values must be numeric and non-negative.
Negative projection errors cannot pass GATE 2.
```

### 8.10 Result Directory Discipline

- [x] Audit flat `result/` layout.
- [x] Write release packages into per-output directories.
- [x] Use system temporary release staging instead of persistent workspace staging.
- [x] Clean release staging after success.
- [x] Clean release staging after failed release tests.
- [x] Reorganize existing `result/` under source image directory.
- [x] Regenerate task 25 manifest at new path.
- [x] Regenerate task 26 manifest at new path.
- [x] Verify task 25 manifest at new path.
- [x] Verify task 26 manifest at new path.
- [x] Add `--output-package-dir` for direct per-task final package output.
- [x] Add regression for direct per-task final package output.
- [x] Add `--review-mark` for direct manifest review binding.
- [x] Add regression for runner review mark binding.
- [x] Add regression for CLI review mark binding.

Acceptance:

```text
result/ top level contains source-image directories, not flat mixed artifacts.
Each task has separate input, gate1, and final directories.
Temporary release staging is cleaned after each release attempt.
```

### 8.11 Publish Scope Hardening

- [x] Audit publish history for local-only runtime directories.
- [x] Rewrite `.gitignore` so `_ref/`, `input_images/`, `work/`, `result/`, and `output_results/` stay local-only.
- [x] Move long-lived text references into `docs/references/`.
- [x] Rebuild clean git history without images or generated outputs.
- [x] Push clean code-only snapshot to `origin/main`.
- [x] Fix release-time pytest execution to run from repository root.
- [x] Add regression for repository publish-scope hygiene.
- [x] Add regression for rooted release-time pytest execution.
- [x] Update audit docs to reflect pushed clean publish state.

Acceptance:

```text
Release-time pytest evidence is collected from the repository root.
Git-tracked publish history excludes local runtime directories and images.
Remote main contains the clean code-only snapshot.
```

## Absolute Stop Rules

- [x] Stop if final rendering is attempted before GATE 4.
- [x] Stop if AI generates a pass token.
- [x] Stop if geometry source is missing.
- [x] Stop if derived line has no reason.
- [x] Stop if hatch intersects hole.
- [x] Stop release token if pytest failed.
- [x] Stop if image is unreadable and no user confirmation exists.

## Current Test Baseline

```text
2026-05-28
.venv\Scripts\python -m pytest
71 passed
```
