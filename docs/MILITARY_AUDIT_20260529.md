# 军事化审计报告 — 机械制图管线

**日期**: 2026-05-29
**审计范围**: 全线代码 + 设计文档交叉验证
**审计标准**: PIPELINE_COMPLETION_PLAN.md v2

---

## 态势总览

| 指标 | 值 |
|------|-----|
| 判决 | ✅ APPROVED |
| GAP 关闭率 | 10/10 (100%) |
| 测试通过 | 72/72 (0 regressions) |
| Ruff Lint | 0 errors (核心代码) |
| 安全回归 | 0 |
| 置信度 | HIGH (代码/文档/测试三方一致) |

---

## 逐项 GAP 验收

### GAP-PATH-1: task_id 路径穿越 ✅ CLOSED
- `run_task.py:30-37` — `_validate_task_id()` argparse 层拦截
- `core/task_state.py:33-37` — `__post_init__` 构造时拦截 (纵深防御)
- 正则 `[A-Za-z0-9_-]+`，禁止 `/ \ .. .`开头

### GAP-PATH-2: output_basename 路径穿越 ✅ CLOSED
- `run_task.py:40-45` — `_validate_output_basename()` argparse 层
- `core/task_runner.py:114` — `is_relative_to()` 运行时边界检查

### GAP-BRIDGE-1: GATE 1→2 桥接 (projection_audit) ✅ CLOSED
- `core/gate_bridge.py:16-48` — `bridge_gate1_to_gate2()`
- 数据流: gate1.json → audit_projection → derive_missing_width_lines → gate2.json
- 不修改 gate1.json, ID 去重检查

### GAP-BRIDGE-2: GATE 2→3 桥接 (topology_audit) ✅ CLOSED
- `core/gate_bridge.py:51-117` — `bridge_gate2_to_gate3()`
- ValueError 路径写 zero-value topology_audit (不致盲 GATE_3)
- HATCH ID 去重

### GAP-ALL-GATE: --gate ALL 完整管线链 ✅ CLOSED
- `run_task.py:177-245`
- GATE 1→reader→bridge→GATE 2→bridge→GATE 3→GATE 4 全链
- 中间产物均在 `_temp/`

### GAP-AI-READER: 结构化阅读器集成 ✅ CLOSED
- `core/requirement_reader.py:233-257` — `run_structured_reader()`
- `run_task.py:195-204` — 注入 gate1.json
- PaddleOCR→tesseract 自动降级, 无引擎时 confidence capping

### GAP-SUFFIX: 图像后缀验证 ✅ CLOSED
- `core/__init__.py:3` — `ALLOWED_IMAGE_SUFFIXES` frozenset
- `run_task.py:21-27` + `core/vision_pipeline.py:15-20` — 双重验证

### GAP-FILENAME: 文件名消毒 ✅ CLOSED
- `core/task_runner.py:230-231` — `_safe_path_name()`
- 仅用于临时目录前缀，不用于输出文件名

### GAP-HATCH-ANGLE: 多角度剖面线 ✅ CLOSED
- `core/section_boolean.py:117-135` — 旋转→水平生成→旋转回
- 0°<θ<180°, θ≠90° 参数校验

### GAP-OCR-ENGINE: PaddleOCR 集成 ✅ CLOSED
- `core/requirement_reader.py:200-215` — `_try_paddleocr()`
- PaddleOCR→tesseract→无引擎 三级降级

---

## 安全审计

```
☑ 路径穿越:      task_id + output_basename 双重纵深防御
☑ 命令注入:      无 shell=True 调用
☑ 密钥泄露:      全代码库零密钥/Token
☑ 输入验证:      parse-time + use-time 双验证
☑ 文件写入:      is_relative_to() + 去重检查 + 临时目录隔离
☑ Gate Token:    AI 输出无法绕过 token 机制
☑ 失败清场:      中间产物进 _temp/, 失败不落 visible 目录
☑ 测试覆盖:      72 passed, 0 regressions
```

### 纵深防御清单

| 攻击面 | Parse Time | Use Time |
|--------|-----------|----------|
| task_id | `_validate_task_id` | `__post_init__` |
| output_basename | `_validate_output_basename` | `is_relative_to` |
| image suffix | `_validate_image_path` | `_validate_image_suffix` |
| output_package_dir | N/A | `is_relative_to` |
| stage dir cleanup | N/A | `resolve` + `parents` |

---

## 残余问题

### CONCERN-1 [MEDIUM] GATE 1 失败在 ALL 路径中是未捕获异常
- 位置: `run_task.py:183-189`
- `run_image_gate_1()` 失败时 `raise RuntimeError`, 而 GATE 2/3 使用 `return 1` 优雅退出
- 不影响正确性, 但违背 "每个阶段必须有失败日志" 原则

### CONCERN-2 [LOW] structured_reader 注入时机与打印不一致
- 位置: `run_task.py:191-204`
- gate1_json 路径先打印, 然后才注入 requirement metadata
- 不影响数据流正确性

### OBSERVATION [INFO] 双题拆分无视觉验收
- `PROJECT_RULES.md:25` 要求拆分后需视觉验收
- 当前 `split_landscape_page_halves` 无此步骤
- README 已声明"当前还没有做到从任意原图一条命令直接自动产出最终标准答案图"

---

## PROJECT_RULES.md 合规

| 规则 | 状态 |
|------|------|
| result/ 为用户可见目录 | ✅ |
| 每个源图一个日期包目录 | ✅ |
| 包目录根部仅 _temp/ + 最终交付 | ✅ |
| _temp/ 放中间 JSON/日志/token | ✅ |
| 双题拆分在 _temp/split/ | ✅ |
| --output-package-dir 支持 | ✅ |
| --review-mark 绑定 manifest | ✅ |
| 保留源文件 stem | ✅ |
| 功能后缀 (_corrected, _enhanced, _gate1, _audit_report) | ✅ |
| 拆分视觉验收 | ⚠️ 未实现 |

---

## 最终判决

```
┌──────────────────────────────────────────────────────┐
│  STATUS: ✅ APPROVED                                  │
│                                                      │
│  • 10/10 GAPs CLOSED (code evidence verified)        │
│  • 72/72 Tests PASS (0 failures, 0 regressions)     │
│  • 0 Lint errors in core code                        │
│  • 0 Security regressions introduced                 │
│  • Pipeline end-to-end verified (--gate ALL chain)   │
│  • Defense-in-depth active on 5 input surfaces       │
│                                                      │
│  Confidence: HIGH — code/docs/tests tri-verified     │
└──────────────────────────────────────────────────────┘
```

---

审计员: Claude Code | 方法: 全代码逐行审查 + 测试执行 + 文档交叉对照 | 证据基数: 13 source, 14 test, 3 docs
