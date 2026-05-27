# Mechanical Drawing Tool - Production Design Review

## 1. Executive Decision

第一版不做前端，不做自研 CAD 内核，不把图像生成模型作为最终出图引擎。

系统定位为：

```text
命令行驱动的机械制图标准答案生产流水线
= AI 辅助识图 + 成熟 CAD/几何工具出图 + 本地硬门禁审计
```

最高原则：

```text
逻辑严谨 > 几何精准 > 可复核 > 可自动化 > token 节省 > 视觉美观
```

最终图纸必须来自确定性几何对象，而不是生成式图片。每条线、圆、圆弧、剖面线、中心线都必须可追溯到结构化数据、投影关系或人工确认记录。

## 2. Production Readiness Verdict

按大厂生产输出标准评估，本方案可以作为生产级方向，但第一版不能直接宣称全自动生产可用。

可满足：

- 高校机械制图习题的标准答案生产。
- 补线题、三视图校核、全剖、半剖、局部剖、断面图的半自动严谨输出。
- SVG、DXF、PDF、PNG、审计报告的可复核交付。
- 通过测试门禁后再出图的工程化闭环。

暂不承诺：

- 任意低清晰度手机照片全自动识别。
- 任意复杂工业零件图纸 100% 自动还原。
- 生成式图片直接达到 CAD 级精度。
- 没有人工确认时仍保证所有隐藏结构推理正确。

生产结论：

```text
可以进入 POC/MVP 工程实现。
可以用于受控题库、高清输入、人工可复核场景。
要达到大厂级批量生产，需要建立评测集、误差指标、人工复核机制和回归测试体系。
```

## 3. Tooling Strategy

坚持成熟工具优先，最小自研。

| Layer | Tool | Role | 自研程度 |
|---|---|---|---|
| 图像预处理 | OpenCV | 透视校正、旋转校正、直线/圆检测、裁切增强 | 低 |
| 平面拓扑 | Shapely / GEOS | 剖面区域、孔槽留白、波浪线/剖面线相交检查 | 低 |
| DXF 生成 | ezdxf | 程序化生成标准 DXF | 低 |
| CAD 复核 | QCAD / LibreCAD / FreeCAD | 打开、检查、人工微调、格式转换 | 低 |
| 参数化/三维升级 | FreeCAD + OpenCASCADE | 后续 3D 建模、投影生成、复杂实体校核 | 中 |
| SVG 输出 | svgwrite / drawsvg | 白底线稿 SVG 渲染 | 低 |
| PDF/PNG 转换 | CairoSVG / Inkscape CLI | 矢量转高分辨率交付文件 | 低 |
| 质量门禁 | pytest | 硬断言，失败禁止交付 | 低 |
| AI 识图推理 | ChatGPT / OpenAI Vision / 本地 LLM 可选 | 题型判断、候选 JSON、说明文字 | 中 |

不采用：

- 不采用 Stable Diffusion、GPT Image、Images 2.0 作为最终标准图生成器。
- 不自研 CAD 约束求解器。
- 不自研 DXF/PDF 渲染器。
- 第一版不做 React/Fabric/Paper 前端。

## 4. System Architecture

```text
User command
  |
  v
Task runner
  |
  +-- Input registry
  |     - original image path
  |     - task type if provided
  |     - expected output formats
  |
  +-- Vision pipeline
  |     - image quality audit
  |     - perspective correction
  |     - line/circle candidate extraction
  |
  +-- Geometry workspace
  |     - normalized coordinates
  |     - view anchors
  |     - geometry JSON
  |     - manual confirmation marks
  |
  +-- Mechanical rule engine
  |     - projection invariants
  |     - missing-line reasoning
  |     - section/hatch topology
  |
  +-- CAD renderers
  |     - DXF via ezdxf
  |     - SVG via deterministic vector renderer
  |
  +-- Quality gates
  |     - JSON schema validation
  |     - projection assertions
  |     - topology assertions
  |     - render assertions
  |
  v
Output package
  - PNG
  - SVG
  - DXF
  - PDF
  - audit report
  - geometry JSON
```

## 5. Directory Layout

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
├─ core\
│  ├─ vision_pipeline.py
│  ├─ geometry_schema.py
│  ├─ projection_engine.py
│  ├─ section_boolean.py
│  ├─ quality_gate.py
│  ├─ task_runner.py
│  └─ renderers\
│     ├─ dxf_renderer.py
│     ├─ export_converter.py
│     └─ svg_renderer.py
├─ tests\
│  ├─ test_schema.py
│  ├─ test_gate_2_projection.py
│  ├─ test_gate_3_section.py
│  ├─ test_render_outputs.py
│  └─ test_task_runner.py
└─ run_task.py

注：`_ref/`、`input_images/`、`work/`、`result/` 属于本地运行资产，不进入发布仓库历史。
```

## 6. Data Contract

所有图元必须进入统一结构化协议。AI 输出、OpenCV 提取、人工修正都只能写入这个协议，不能绕过。

```json
{
  "task_id": "task_001",
  "task_type": "HALF_SECTION",
  "coordinate_system": {
    "unit": "normalized",
    "canvas_width": 1000,
    "canvas_height": 1000
  },
  "views": [
    {
      "id": "FRONT",
      "type": "FRONT",
      "origin": [100, 150],
      "center": [300, 350],
      "width": 400,
      "height": 300,
      "scale": 1.0
    }
  ],
  "geometries": [
    {
      "id": "LINE_FRONT_001",
      "type": "LINE",
      "line_style": "VISIBLE_OUTLINE",
      "belongs_to_view": "FRONT",
      "source": "confirmed",
      "coords": [100, 200, 300, 200]
    }
  ],
  "audit": {
    "gate_1": "PENDING",
    "gate_2": "PENDING",
    "gate_3": "PENDING",
    "gate_4": "PENDING"
  }
}
```

允许的 source：

- `opencv_candidate`
- `ai_candidate`
- `manual_confirmed`
- `projection_derived`
- `section_derived`
- `renderer_generated`

生产要求：最终输出中，关键结构不得只有 `ai_candidate` 来源。必须经过 `manual_confirmed`、`projection_derived` 或硬门禁确认。

## 7. Four-Gate Execution Protocol

### GATE 1: Input and Geometry Extraction

目标：只做输入审计与几何候选提取，不做机械推理。

检查项：

- 图片路径存在。
- 原图备份完成。
- 分辨率达到最低要求。
- 倾角、透视畸变、对比度记录。
- 输出候选直线、圆、圆弧、中心线、视图边界。

失败处理：

- 不进入投影推理。
- 标记为需要高清图或人工标定。

### GATE 2: Projection Invariant Audit

目标：检查机械投影关系。

硬规则：

- 主视图与俯视图长对正。
- 主视图与左视图高平齐。
- 俯视图与左视图宽相等。
- 多视图比例一致，不允许单视图拉伸。

输出：

- 缺失线候选。
- 多余线候选。
- 坐标误差表。
- 每条补线的推导来源。

### GATE 3: Section and Topology Audit

目标：处理剖切规则和实体区域。

硬规则：

- 剖面线只在实体材料区域。
- 孔、槽、空腔必须留白。
- 局部剖波浪线不得穿越空气腔。
- 纵向剖切加强筋、轮辐等不画剖面线。
- 半剖分界必须是中心线，不是粗实线。

实现：

- Shapely 多边形差集。
- hatch lines 与 holes intersection 必须为 0。
- rib polygons 与 hatch intersection 必须为 0。

### GATE 4: Render and Release Gate

目标：输出前最终测试。

必须通过：

- JSON schema 校验。
- 图层枚举合法。
- 线宽、线型、颜色合法。
- 中心线穿过圆心并适当外延。
- 剖面线不侵入孔槽。
- 输出文件存在且可打开。
- PNG/PDF 渲染尺寸达标。

失败处理：

```text
禁止输出最终答案。
只能输出失败报告和待修正项。
```

## 8. Token-Saving Strategy

为了兼容 token 节省，AI 不读取和复述全量参考文档，只使用压缩后的执行协议。

策略：

- 长文档只在设计阶段读取一次，沉淀为本文件和测试规则。
- 每次处理图片时，只传入任务类型、原图路径、几何 JSON 摘要、失败门禁日志。
- 不把图片处理过程中的完整像素信息发给模型。
- AI 输出必须是结构化 JSON patch，而不是长篇自然语言。
- 作图说明最后生成，且限制 4 到 6 条。
- 失败时只反馈失败断言和相关图元 id，不复述全部规则。

推荐运行提示模板：

```text
Process image: <path>
Task type: <known_or_unknown>
Use protocol: production_review_v1
Return only:
1. gate status
2. geometry_json patch
3. unresolved questions if any
4. audit summary
```

## 9. Human Review Policy

第一版采用人机协同，不追求危险的伪全自动。

必须人工确认的情况：

- 原图低清、倾斜、遮挡、透背严重。
- 题目要求文字或剖切符号不清楚。
- 只有一个视图却要求推断复杂内部结构。
- AI 与投影规则产生冲突。
- GATE 2 或 GATE 3 出现多种可能解。

人工确认内容进入 `review_marks`，作为生产审计链的一部分。

## 10. Output Standard

每题输出一个包：

```text
result/<source_stem>/<task_id>/final/
├─ <output_stem>.png
├─ <output_stem>.svg
├─ <output_stem>.dxf
├─ <output_stem>.pdf
├─ <output_stem>_audit_report.md
└─ <output_stem>_release_manifest.json
```

审计报告必须包含：

- 输入质量指标。
- 几何基准。
- 投影误差。
- 剖切拓扑检查。
- 输出文件清单。
- 失败项或人工确认项。

## 11. Acceptance Metrics

MVP 验收标准：

- 20 张高清单题图中，至少 18 张可完成标准输出。
- 所有输出图均可打开 SVG/DXF/PDF/PNG。
- 所有通过样例的 pytest 必须 100% 通过。
- 已知孔槽样例中剖面线侵入率为 0。
- 多视图样例中投影误差在归一化坐标中为 0 或在约定容差内。
- 每个最终补线图元都能追溯来源。

生产级验收标准：

- 建立不少于 200 题的回归题库。
- 覆盖补线、全剖、半剖、局部剖、旋转剖、阶梯剖、断面图。
- 每次代码变更自动跑全量回归。
- 错误样例进入 fixtures，永不允许回归。
- 人工复核通过率、自动识别通过率、门禁失败率必须持续统计。

## 12. Risk Register

| Risk | Severity | Mitigation |
|---|---:|---|
| 低清图片导致识别错误 | High | 输入审计 + 人工标定 |
| AI 脑补不存在结构 | High | AI 只输出候选，门禁和人工确认后才出图 |
| 剖面线进入孔槽 | High | Shapely 差集 + pytest 硬断言 |
| 多视图方向判断反了 | High | 投影约束 + 人工确认前后方向 |
| DXF/SVG/PDF 不一致 | Medium | 统一几何源，分别渲染后做 smoke test |
| 线型不符合标准 | Medium | layer config 固化 + render test |
| token 消耗过高 | Medium | 摘要协议 + JSON patch + 不复述规则 |

## 13. Professional Review Checklist

设计团队应审核：

- 图层顺序是否符合机械制图阅读习惯。
- 粗实线、细实线、虚线、中心线、剖面线是否清晰区分。
- 半剖、局部剖、全剖版式是否符合教学标准。
- 输出图是否干净、白底、高对比、可打印。

机械制图教师/工程师应审核：

- 投影关系是否严格正确。
- 漏线补画是否有多画或少画。
- 剖面线是否只在实体内。
- 加强筋、轮辐、孔槽规则是否正确。
- 作图步骤是否能用于学生理解。

软件工程团队应审核：

- schema 是否稳定。
- 所有规则是否测试化。
- 工具链是否可安装、可复现。
- 输出是否可批处理。
- 失败时是否能定位具体图元。

## 14. Final Recommendation

最终推荐路线：

```text
Phase 1:
Build command-line deterministic drawing pipeline.

Phase 2:
Add OpenCV extraction and semi-automatic geometry confirmation.

Phase 3:
Add AI candidate generation, but keep AI outside final rendering authority.

Phase 4:
Build regression dataset and production quality dashboard.

Phase 5:
Only after the backend is stable, consider frontend/editor.
```

关键判断：

```text
当前最稳方案不是“让 ChatGPT/Image 直接画图”，
而是“让 AI 帮忙读题，让成熟 CAD/几何库画图，让 pytest 决定能不能交付”。
```

按此方案执行，可以达到大厂生产输出所需要的工程路径；但必须经过题库评测、人工复核流程和回归测试建设后，才能宣称生产级稳定。
