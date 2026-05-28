# Diagram Military Pipeline

## Goal

给定一张自己排好的机械制图图片，用命令行指令完成整理和后续处理。

目标工作流：

1. 输入一张图片。
2. 如果图片里有两个题，先自动拆成两个任务。
3. `result/` 里只保留用户需要看的内容：
   - 原图副本
   - 规范化中间图
   - 每个任务的输入图
   - 每个任务的最终交付文件
4. GATE 1 候选 JSON、状态 token、失败日志、review mark 等内部审计资产都留在 `work/`。

## Current Command Set

### 1. 双题页整理与拆分

当一张横向页面里并排放了两个题，使用：

```powershell
python run_task.py --image "input_images/1 (1).jpg" --split-page-halves
```

输出目录：

```text
result/1 (1)/
├─ source/
│  └─ 1 (1).jpg
├─ split/
│  └─ 1 (1)_normalized.png
├─ task25/
│  └─ input/
│     └─ 1 (1)_task25.png
└─ task26/
   └─ input/
      └─ 1 (1)_task26.png
```

这一步不会把 GATE 1 JSON、state token、失败日志写进 `result/`。

### 2. 单图或子图执行 GATE 1

```powershell
python run_task.py --image "result/1 (1)/task25/input/1 (1)_task25.png" --task-id "1 (1)_task25" --gate GATE_1
```

GATE 1 产物写到本地运行目录：

```text
work/original/
work/corrected/
work/enhanced/
work/geometry_json/
work/state/
work/audit_logs/
```

### 3. 已有几何 JSON 时执行最终 release

```powershell
python run_task.py --task-id "1 (1)_task25" --geometry-json "work/geometry_json/1 (1)_task25_manual.json" --gate GATE_4 --output-basename "1 (1)_task25_final" --output-package-dir "result/1 (1)/task25/final"
```

## Result Directory Rules

- `result/` 是用户可见目录，不放内部 gate 审计垃圾。
- `work/` 是内部运行目录，允许放中间 JSON、日志、token、review mark。
- 一个源图一个目录。
- 一个任务一个 `input/` 和一个 `final/`。
- 双题页拆分后，`split/` 只保留规范化中间图，不重复堆拆分子图。

## Current Boundary

当前仓库已经支持：

- 双题页自动整理与拆分
- GATE 1 识图与候选 JSON 生成
- 基于几何 JSON 的 GATE 2 / GATE 3 / GATE 4
- 最终 SVG / DXF / PNG / PDF / audit report / release manifest 交付

当前还没有做到：

- 从任意原图一条命令直接自动产出最终标准答案图
- 自动判断“单题还是双题”并自动选择完整后续路径

所以当前推荐流程是：

1. 双题页先跑 `--split-page-halves`
2. 对目标子图跑 GATE 1
3. 校正或补齐几何 JSON
4. 跑 GATE 4 release
