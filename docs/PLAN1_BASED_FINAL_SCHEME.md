# Plan1-Based Final Scheme

## 1. Core Basis

本方案以 `docs/references/plan1.md` 为主要依据。

`plan1.md` 的核心判断是正确的：

```text
单靠系统提示词不能保证机械制图准确。
必须用后端代码建立物理隔离的状态机、JSON 解析、单元测试和几何沙箱。
AI 不能自己生成通过 Token，也不能自己宣布测试通过。
```

因此，本项目不是“提示词画图工具”，而是：

```text
代码执法的机械制图 Agent 流水线
```

AI 的职责是读题、推理、生成候选结构化数据；最终是否允许出图，由本地代码和测试决定。

## 2. User Workflow

用户真实使用方式：

```text
用户手机拍题
  ↓
用户命令 Codex 处理指定图片
  ↓
系统自动校正、识别题意、提取几何候选
  ↓
系统执行 GATE 1-4
  ↓
必要时请求最小人工确认
  ↓
通过后输出标准答案图
```

示例命令：

```text
处理 X:\homework\diagram\input\task_01.jpg，按 plan1 流程输出标准答案
```

第一版不做前端，不做 Web 编辑器。

## 3. Architecture

```text
run_task.py
  |
  v
main_agent_flow.py
  |
  +-- GATE 1: vision_pipeline.py
  |       OpenCV 校正、图像质量审计、线圆候选提取
  |
  +-- GATE 2: projection_engine.py
  |       长对正、高平齐、宽相等、漏线推导
  |
  +-- GATE 3: section_boolean.py
  |       Shapely 剖面区域、孔槽留白、加强筋不剖、波浪线隔离
  |
  +-- GATE 4: quality_gate.py + pytest
  |       JSON Schema、几何断言、图层断言、输出文件断言
  |
  +-- renderer
          ezdxf / SVG / CairoSVG / PDF / PNG
```

## 4. Project Structure

```text
X:\homework\diagram
├─ docs\
│  ├─ references\
│  │  └─ plan1.md
│  └─ ...
├─ input_images\
├─ work\
│  ├─ original\
│  ├─ corrected\
│  ├─ extracted\
│  ├─ geometry_json\
│  ├─ review_marks\
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
│  └─ layers_config.json
├─ core\
│  ├─ vision_pipeline.py
│  ├─ geometry_schema.py
│  ├─ projection_engine.py
│  ├─ section_boolean.py
│  ├─ canvas_renderer.py
│  ├─ quality_gate.py
│  └─ task_state.py
├─ tests\
│  ├─ test_gate_1_input.py
│  ├─ test_gate_2_projection.py
│  ├─ test_gate_3_section.py
│  └─ test_gate_4_release.py
└─ run_task.py
```

## 5. Tool Selection

坚持 `plan1.md` 的思想：AI 不能凭空画，必须交给真实工具执行。

| Stage | Tool | Reason |
|---|---|---|
| 手机图校正 | OpenCV | 成熟、可本地执行、适合透视校正和线圆检测 |
| 几何数据校验 | Pydantic / JSON Schema | 防止 AI 输出非法结构 |
| 投影关系 | NumPy / 自定义薄层规则 | 只写机械制图特定约束，不自研大型 CAD |
| 剖面布尔 | Shapely | 成熟 GEOS 拓扑能力，适合孔槽留白和剖面裁剪 |
| DXF 输出 | ezdxf | 成熟 Python DXF 库 |
| SVG 输出 | svgwrite / drawsvg | 确定性矢量线稿 |
| PDF/PNG 输出 | CairoSVG / Inkscape CLI | 成熟矢量转换 |
| CAD 复核 | QCAD / LibreCAD / FreeCAD | 人工或外部复核 |
| 硬门禁 | pytest | 不通过就禁止交付 |

不采用：

- GPT Image / Images 2.0 作为最终答案图生成器。
- 扩散模型作为最终出图。
- AI 自己生成通过 Token。
- AI 自己声称 pytest 已通过。

## 6. Gate Protocol

### GATE 1: Geometry Extraction Lock

输入：手机照片。

任务：

- 备份原图。
- 检测分辨率、倾角、透视畸变、对比度。
- OpenCV 校正图片。
- 提取候选视图框、直线、圆、圆弧、中心线、剖切符号。
- 生成 `gate_1_geometry.json`。

硬断言：

```text
image_exists == true
detected_views_count >= 1
rotation_theta_deg <= configured_limit
geometry_json_schema_valid == true
```

通过后由后端写入：

```text
TOKEN_GEOM_EXTRACT_PASS
```

注意：Token 必须由代码写入状态文件，不能由 AI 文本输出伪造。

### GATE 2: Projection Algebra Lock

输入：GATE 1 的结构化几何。

任务：

- 建立主视图、俯视图、左视图局部坐标系。
- 执行长对正、高平齐、宽相等。
- 推导漏线候选。
- 判断线型：粗实线、细虚线、中心线。

硬断言：

```text
length_alignment_error <= tolerance
height_alignment_error <= tolerance
width_equality_error <= tolerance
all_derived_lines_have_reason == true
```

通过后由后端写入：

```text
TOKEN_PROJ_ALIGN_PASS
```

### GATE 3: Topology Section Lock

输入：GATE 2 的投影闭合几何。

任务：

- 对全剖、半剖、局部剖、断面图执行剖切规则。
- 用 Shapely 计算实体材料区域。
- 从剖面线区域中扣除孔、槽、空腔。
- 拦截加强筋纵向剖切画剖面线。
- 拦截波浪线穿空气腔。

硬断言：

```text
hatch_hole_intersection_area == 0
rib_hatch_intersection_area == 0
waveline_air_intersection_length == 0
section_region_is_valid == true
```

通过后由后端写入：

```text
TOKEN_TOPO_SECTION_PASS
```

### GATE 4: Military Release Gate

输入：前三关的最终 geometry JSON。

任务：

- 渲染 SVG。
- 渲染 DXF。
- 转换 PNG/PDF。
- 跑 pytest。
- 输出审计报告。

硬断言：

```text
all_layers_valid == true
centerlines_cross_circle_centers == true
hatch_does_not_enter_holes == true
projection_errors_within_tolerance == true
output_files_exist == true
render_smoke_test_pass == true
```

通过后由后端写入：

```text
TOKEN_SYSTEM_RELEASE_RENDER
```

只有这个 Token 存在，才允许生成最终答案。

## 7. Phone Photo Handling

手机拍题是主场景，但不能无条件盲出。

系统按三档处理：

### A. Auto Grade

条件：

- 题目文字清楚。
- 图线清楚。
- 剖切符号可读。
- 视图完整。
- 投影关系可闭合。

处理：

```text
自动跑完 GATE 1-4，直接输出。
```

### B. Assisted Grade

条件：

- 大部分清楚，但存在局部模糊或多解。

处理：

```text
系统只问 1-3 个关键确认问题。
确认后继续出图。
```

示例：

```text
A-A 剖切箭头方向不清，请确认观察方向是向左还是向右。
```

### C. Reject and Retake

条件：

- 图线糊成一片。
- 题目要求缺失。
- 关键视图被裁掉。
- 反光/遮挡严重。

处理：

```text
不出最终答案，只输出重拍建议。
```

这不是失败，而是防止错误答案进入最终交付。

## 8. Token-Saving Implementation

为节省 token，执行时不把全部协议和长文档重复塞给模型。

采用：

- 本地代码保存规则。
- 每关只给 AI 最小上下文。
- AI 返回 JSON patch。
- 失败时只返回失败 gate、图元 id、断言信息。
- 作图说明最后生成，限制 4-6 条。

AI 交互格式：

```json
{
  "stage": "GATE_2",
  "task": "projection_audit",
  "input_summary": {},
  "required_output": "json_patch_only"
}
```

## 9. No Regression Dataset at Start

当前没有回归题库，不影响启动。

启动方式：

```text
先按逐题生产模式做。
每处理一张真实手机题图，就自动沉淀为一个生产样例。
```

每题保留：

- 原图。
- 校正图。
- 几何 JSON。
- 最终图。
- 审计报告。
- 人工确认记录。
- 失败断言。

这些样例会自然形成未来的回归题库。

## 10. Production Feasibility

如果要求是：

```text
手机拍清楚题目，系统严格识别、提取、推理、校验、出图
```

则本方案可行。

如果要求是：

```text
任意模糊、遮挡、缺视图、题意缺失的照片也自动完美输出
```

则不可行，也不应该承诺。专业系统必须在信息不足时拒绝或请求确认。

大厂生产标准不是“永远不问问题”，而是：

```text
能自动确定的，自动高质量输出。
不能确定的，精准拦截并请求最小补充。
绝不生成无法审计的假答案。
```

## 11. Final Design Verdict

以 `plan1.md` 为主要依据，最终方案定为：

```text
Plan1 状态机硬门禁
+ OpenCV 手机图校正
+ JSON 几何协议
+ 投影代数求解
+ Shapely 剖切布尔
+ ezdxf/SVG 确定性出图
+ pytest 军事化总门禁
+ 必要时最小人工确认
```

该方案是当前目标下最稳的工程路径。

它满足：

- 严谨逻辑。
- 精准比例与投影关系。
- 手机拍题主流程。
- token 节省。
- 成熟开源工具优先。
- 第一版无前端。
- 最终输出可审计、可复核、可扩展到生产。
