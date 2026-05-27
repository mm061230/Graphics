# Global Audit V2

Date: 2026-05-27

## Version Line

- Baseline commit: `a2ed8f5 baseline military diagram pipeline`
- Baseline tag: `v1.0.0`
- Active next-version branch: `v2/global-audit`
- Push status: blocked by missing remote and missing GitHub authentication.

## Design Contract Checked

- Final user-visible files must not exist before `TOKEN_SYSTEM_RELEASE_RENDER`.
- GATE 1 must be image-bound and must not enter rendering through a geometry JSON path.
- GATE 4 must verify output artifacts and release tests before manifesting.
- Release packages must be machine-auditable from manifests.
- AI or natural-language claims must not create pass tokens.

## Findings

### Finding 1: Final Outputs Were Written Before Release Token

Status: fixed.

Previous behavior:

- `run_from_geometry` rendered SVG, DXF, PNG, and PDF directly into `result/`.
- GATE 4 ran after those files already existed.
- If release tests failed, user-visible final files could remain without a release token.

Correction:

- Rendering now writes first to a system temporary release staging directory.
- GATE 4 validates staged outputs and release tests.
- Final files are copied to `result/` only after GATE 4 passes and the release token exists.
- Failed release attempts return no final outputs and no release manifest.

Regression:

- `tests/test_task_runner.py` now simulates a pytest failure and asserts no final SVG or manifest is written.

### Finding 2: CLI GATE 1 Could Fall Through to Geometry Rendering Path

Status: fixed.

Previous behavior:

- `run_task.py --geometry-json ... --gate GATE_1` was not rejected.
- The geometry path could fall through toward `run_from_geometry` instead of enforcing image-bound GATE 1 intake.

Correction:

- CLI now rejects `--geometry-json --gate GATE_1`.
- GATE 1 requires `--image`.

Regression:

- `tests/test_cli.py` asserts this command fails and does not render a final SVG.

### Finding 3: GATE 2 Accepted Missing Projection Audit as Zero

Status: fixed.

Previous behavior:

- `run_gate_2_checks` used a default empty `projection_audit`.
- Missing projection audit fields were interpreted as `0.0`.
- A geometry JSON could pass GATE 2 without explicitly recording projection invariant results.

Correction:

- GATE 2 now requires `projection_audit`.
- GATE 2 now requires `length_alignment_error`, `height_alignment_error`, and `width_equality_error`.
- Missing or non-numeric audit values fail the gate and do not write `TOKEN_PROJ_ALIGN_PASS`.

Regression:

- `tests/test_quality_gate.py` covers missing and incomplete projection audit failures.

### Finding 4: GATE 3 Accepted Missing Topology Audit as Zero

Status: fixed.

Previous behavior:

- `run_gate_3_checks` used a default empty `topology_audit`.
- Missing topology audit fields were interpreted as `0.0`.
- A geometry JSON could pass GATE 3 without explicitly recording section topology results.

Correction:

- GATE 3 now requires `topology_audit`.
- GATE 3 now requires `hatch_hole_intersection_area`, `rib_hatch_intersection_area`, and `waveline_air_intersection_length`.
- Missing or non-numeric audit values fail the gate and do not write `TOKEN_TOPO_SECTION_PASS`.

Regression:

- `tests/test_quality_gate.py` covers missing topology audit failure.

### Finding 5: Manifest Completeness Needed Missing-Output Regression

Status: fixed.

Previous coverage:

- Release manifest tests detected a missing release token.
- They did not explicitly prove that a missing required output fails manifest completeness.

Correction:

- `tests/test_release_manifest.py` now covers a release with all tokens but a missing PNG output.
- The manifest reports `release_complete=false` and lists `.png` in `missing_outputs`.

### Finding 6: Direct GATE 4 Could Release Without Pytest Status

Status: fixed.

Previous behavior:

- `run_gate_4_checks` could be called directly with `pytest_passed=None`.
- Outside the task runner, that allowed a release token to be written without explicit pytest evidence.

Correction:

- Outside the pytest harness, GATE 4 now fails when pytest status is missing.
- The pytest harness keeps its recursion guard so unit tests can exercise release behavior without recursively spawning pytest.

Regression:

- `tests/test_quality_gate.py` deletes `PYTEST_CURRENT_TEST`, calls GATE 4 without pytest status, and asserts no release token is written.

### Finding 7: GATE 2 Projection Audit Allowed Negative Errors

Status: fixed.

Previous behavior:

- GATE 2 compared projection errors with `value > tolerance`.
- A negative audit value could bypass the failing threshold even though an error magnitude cannot be negative.

Correction:

- Shared audit parsing now rejects negative numeric values for GATE 2 and GATE 3 audit fields.
- Negative values fail before any pass token is written.

Regression:

- `tests/test_quality_gate.py` covers a negative `projection_audit.length_alignment_error`.

### Finding 8: Result Directory Was Too Flat

Status: fixed.

Previous behavior:

- `result/` mixed source images, split images, GATE 1 reports, final outputs, review marks, and manifests in one directory.
- Successful release staging could leave temporary directories behind.

Correction:

- `run_from_geometry` now writes release packages to `result/<output_stem>/`.
- `run_from_geometry` and `run_task.py` can write directly to a source/task `final/` directory with `output_package_dir` / `--output-package-dir`.
- `run_from_geometry` and `run_task.py` can bind review marks into manifests with `review_mark` / `--review-mark`.
- Successful and failed release staging is cleaned from the system temporary directory.
- Existing `result/` artifacts were reorganized under `result/1 (1)/` with per-task `input/`, `gate1/`, and `final/` directories.
- Task 25 and task 26 manifests were regenerated and verified at their new paths.

Regression:

- `tests/test_task_runner.py` now asserts per-package result directories and staging cleanup.
- `tests/test_release_manifest.py` and `tests/test_cli.py` verify manifests at package-directory paths.

## Current Validation

```text
.venv\Scripts\python.exe -m pytest
68 passed
```

## Residual Push Blocker

The local baseline commit exists, but push cannot proceed until both are true:

- A remote such as `origin` is configured.
- `gh auth status` reports an authenticated GitHub session, or an HTTPS/SSH remote is otherwise usable by local Git.
