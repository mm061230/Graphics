# Military Execution Plan

## 0. Command Principle

本项目按 `docs/references/plan1.md` 执行，采用军事化门禁流程。

总原则：

```text
不跳关。
不脑补。
不让 AI 自证通过。
不生成无法审计的最终图。
每个阶段必须有文件产物、代码断言、失败日志。
```

第一版目标：

```text
用户给一张手机拍摄机械制图题图。
系统按 GATE 1-4 处理。
能确定则输出标准答案。
不能确定则精准说明缺什么，并请求最小确认。
```

## 1. System Architecture

```text
run_task.py
  |
  v
core/task_runner.py
  |
  +-- core/task_state.py
  |     - 状态机
  |     - Token 文件
  |     - 回滚记录
  |
  +-- core/vision_pipeline.py
  |     - 手机图输入审计
  |     - OpenCV 校正
  |     - 线/圆/视图候选提取
  |
  +-- core/requirement_reader.py
  |     - OCR 读题
  |     - 题型识别
  |     - 不确定项记录
  |
  +-- core/geometry_schema.py
  |     - Pydantic 数据模型
  |     - JSON Schema
  |     - 图元合法性校验
  |
  +-- core/projection_engine.py
  |     - 主/俯/左视图坐标系
  |     - 长对正
  |     - 高平齐
  |     - 宽相等
  |     - 漏线候选
  |
  +-- core/section_boolean.py
  |     - Shapely 面域布尔
  |     - 剖面线裁剪
  |     - 孔槽留白
  |     - 加强筋不剖
  |
  +-- core/renderers/
  |     +-- svg_renderer.py
  |     +-- dxf_renderer.py
  |     +-- export_converter.py
  |
  +-- core/quality_gate.py
        - GATE 1-4 统一断言入口
        - pytest 调度
        - release token 控制
```

## 2. Runtime Directories

```text
X:\homework\diagram
├─ docs\
│  └─ references\
├─ input_images\
├─ work\
│  ├─ original\
│  ├─ corrected\
│  ├─ enhanced\
│  ├─ extracted\
│  ├─ geometry_json\
│  ├─ review_marks\
│  ├─ state\
│  └─ audit_logs\
├─ result\
│  └─ <source_stem>\
│     ├─ source\
│     ├─ split\
│     └─ <task_id>\
│        ├─ input\
│        ├─ gate1\
│        └─ final\
├─ config\
├─ core\
├─ tests\
└─ run_task.py
```

## 3. Gate Contract

### GATE 1: Geometry Extraction Lock

Input:

```text
手机拍摄题图
```

Responsibilities:

- 复制原图，禁止覆盖。
- 图像质量审计。
- 透视校正、旋转校正、裁切、增强。
- OCR/视觉读取题目要求。
- 提取图元候选。
- 输出 `work/geometry_json/<task_id>_gate1.json`。

Pass Conditions:

```text
原图存在
校正图存在
题图区可定位
detected_views_count >= 1
JSON schema valid
关键不确定项已记录
```

Pass Token:

```text
work/state/<task_id>/TOKEN_GEOM_EXTRACT_PASS
```

Fail Output:

```text
work/audit_logs/<task_id>_gate1_failed.md
```

### GATE 2: Projection Algebra Lock

Input:

```text
GATE 1 geometry JSON
```

Responsibilities:

- 建立视图坐标系。
- 校验比例一致性。
- 校验长对正、高平齐、宽相等。
- 推导漏线和线型。
- 输出 `work/geometry_json/<task_id>_gate2.json`。

Pass Conditions:

```text
TOKEN_GEOM_EXTRACT_PASS exists
projection errors <= tolerance
每条补线都有 reason/source
无悬空图元
无未解释线型
```

Pass Token:

```text
work/state/<task_id>/TOKEN_PROJ_ALIGN_PASS
```

Fail Output:

```text
work/audit_logs/<task_id>_gate2_failed.md
```

### GATE 3: Topology Section Lock

Input:

```text
GATE 2 geometry JSON
```

Responsibilities:

- 识别剖切区域。
- 建立实体材料多边形。
- 扣除孔、槽、空腔。
- 生成剖面线。
- 拦截加强筋纵向剖切错误。
- 拦截波浪线穿空气腔。
- 输出 `work/geometry_json/<task_id>_gate3.json`。

Pass Conditions:

```text
TOKEN_PROJ_ALIGN_PASS exists
hatch_hole_intersection_area == 0
rib_hatch_intersection_area == 0
waveline_air_intersection_length == 0
section polygons valid
```

Pass Token:

```text
work/state/<task_id>/TOKEN_TOPO_SECTION_PASS
```

Fail Output:

```text
work/audit_logs/<task_id>_gate3_failed.md
```

### GATE 4: Release Render Gate

Input:

```text
GATE 3 geometry JSON
```

Responsibilities:

- 生成 SVG。
- 生成 DXF。
- 转换 PNG/PDF。
- 运行 pytest。
- 生成审计报告。

Pass Conditions:

```text
TOKEN_TOPO_SECTION_PASS exists
all pytest tests passed
SVG exists
DXF exists
PNG exists
PDF exists
report exists
```

Pass Token:

```text
work/state/<task_id>/TOKEN_SYSTEM_RELEASE_RENDER
```

Final Output:

```text
result/<source_stem>/<task_id>/final/<output_stem>.svg
result/<source_stem>/<task_id>/final/<output_stem>.dxf
result/<source_stem>/<task_id>/final/<output_stem>.png
result/<source_stem>/<task_id>/final/<output_stem>.pdf
result/<source_stem>/<task_id>/final/<output_stem>_audit_report.md
result/<source_stem>/<task_id>/final/<output_stem>_release_manifest.json
```

## 4. Failure Discipline

任何 GATE 失败：

```text
停止后续阶段。
不生成最终答案。
写失败报告。
记录失败断言、相关图元 id、建议修复方式。
如果需要用户确认，只问最少关键问题。
```

禁止：

```text
虽然失败但继续渲染。
AI 文字声明“我已通过测试”。
跳过 pytest。
输出无来源图元。
凭肉眼补线但不记录 source/reason。
```

## 5. Token Discipline

运行时只把最小信息交给 AI：

```text
task_id
image_path
current_gate
geometry summary
uncertain fields
failed assertions
required json patch format
```

AI 不重复读取全量协议。协议固化在代码和文档中。

## 6. Implementation Phases

### Phase 0: Bootstrap

目标：项目骨架、配置、依赖、目录。

产物：

- `pyproject.toml`
- `config/layers_config.json`
- `run_task.py`
- `core/task_state.py`
- `core/geometry_schema.py`
- `tests/test_schema.py`

### Phase 1: Deterministic Rendering Core

目标：不依赖图片，手写 geometry JSON 也能出图。

产物：

- SVG renderer
- DXF renderer
- PNG/PDF converter
- render smoke tests

### Phase 2: Gate Engine

目标：GATE 1-4 状态机可执行。

产物：

- token 文件机制
- gate pass/fail 报告
- pytest 调度
- 禁止跳关

### Phase 3: Topology Engine

目标：Shapely 剖面线裁剪可靠。

产物：

- hatch generation
- holes subtraction
- rib exclusion
- section tests

### Phase 4: Projection Engine

目标：长对正、高平齐、宽相等。

产物：

- view coordinate models
- projection audit
- missing-line candidates
- projection tests

### Phase 5: Vision Intake

目标：手机图输入可审计、可校正。

产物：

- image quality audit
- perspective correction
- rotation correction
- candidate line/circle extraction

### Phase 6: Requirement Reader

目标：读取题目要求和题型。

产物：

- OCR integration
- AI structured requirement reader
- uncertain field handling

### Phase 7: End-to-End Task

目标：处理真实手机题图。

产物：

- `run_task.py --image ...`
- complete output package
- complete audit report

## 7. Build Order

执行顺序必须是：

```text
Bootstrap
  ↓
Schema
  ↓
Renderer
  ↓
Quality Gate
  ↓
Topology
  ↓
Projection
  ↓
Vision
  ↓
Requirement Reader
  ↓
End-to-End
```

原因：

```text
先保证“给定正确几何就能严谨出图”，
再解决“怎么从手机照片得到正确几何”。
```

这样即使识别阶段不完美，最终输出也不会被污染。
