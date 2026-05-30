# Diagram Military Pipeline

## Goal

给定一张自己排好的机械制图图片，用命令行指令完成整理和后续处理。

目标工作流：

1. 输入一张图片。
2. 如果图片里有两个题，先自动拆成两个任务。
3. `result/` 里每张图先生成一个日期包目录：`<stem>_<YYYYMMDD>/`
4. 包目录下只保留：
   - 一个 `_temp/` 目录
   - 最终交付文件
5. 原图、拆分图、中间图、GATE 1 JSON、状态 token、失败日志、review mark 等内部审计资产都留在 `_temp/`。

## Current Command Set

### 1. 双题页整理与拆分

当一张横向页面里并排放了两个题，使用：

```powershell
python run_task.py --image "input_images/aa.png" --split-page-halves
```

输出目录：

```text
result/aa_20260528/
└─ _temp/
   ├─ original/
   │  └─ aa.png
   └─ split/
      ├─ aa_normalized.png
      ├─ aa_task25.png
      └─ aa_task26.png
```

这一步不会把内部 gate 审计文件写到包目录根部。

### 2. 单图或子图执行 GATE 1

```powershell
python run_task.py --image "input_images/aa.png" --task-id "aa_task25" --gate GATE_1
```

GATE 1 产物写到对应包目录的 `_temp/`：

```text
result/aa_20260528/_temp/original/
result/aa_20260528/_temp/corrected/
result/aa_20260528/_temp/enhanced/
result/aa_20260528/_temp/geometry_json/
result/aa_20260528/_temp/state/
result/aa_20260528/_temp/audit_logs/
```

### 3. 已有几何 JSON 时执行最终 release

```powershell
python run_task.py --task-id "aa_task25" --geometry-json "result/aa_20260528/_temp/geometry_json/aa_task25_manual.json" --gate GATE_4 --output-basename "aa_task25_final"
```

## Result Directory Rules

- `result/` 是用户可见目录。
- 一个源图一个日期包目录。
- 包目录根部只放 `_temp/` 和最终交付文件。
- `_temp/` 是内部运行目录，允许放中间 JSON、日志、token、review mark。
- 双题页拆分后，拆分子图和规范化图都放 `_temp/split/`。

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
