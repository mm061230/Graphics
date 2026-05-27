# Environment Strategy

## Current Development Runtime

当前开发使用项目内独立虚拟环境：

```text
X:\homework\diagram\.venv
```

用途：

- 快速开发。
- 本地运行测试。
- 不污染系统 Python。

当前命令：

```text
.venv\Scripts\python -m pytest
.venv\Scripts\python run_task.py --help
```

## Production Runtime

严肃出图和批处理使用 Docker 容器。

原因：

- Windows 本地缺少 native cairo 时，CairoSVG 可能无法转 PNG/PDF。
- 本项目已提供有限确定性的 Pillow fallback，用于开发期从本仓库 SVG 生成 PNG/PDF。
- OpenCV、OCR、字体、CAD 转换器都依赖 native runtime。
- 容器能固定依赖版本，减少环境漂移。

容器内固定：

- Python 3.11
- OpenCV runtime
- Shapely/GEOS wheel
- ezdxf
- Cairo native runtime
- Inkscape CLI
- Tesseract OCR
- Chinese OCR data
- Noto CJK fonts

## Policy

```text
开发阶段：.venv
生产阶段：Docker
```

最终出图环境必须通过：

```text
python -m pytest
python run_task.py --help
```

当前本机策略：

```text
CairoSVG 可用时优先使用 CairoSVG。
native cairo 缺失时，使用仓库 SVG 子集 fallback 生成 PNG/PDF。
生产容器仍应提供 native cairo / Inkscape 做独立交叉验证。
```
