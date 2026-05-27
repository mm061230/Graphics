# 机械制图智能Agent数字化复刻与闭合几何渲染执行标准协议 (V4.0 工业级闭合版)

## 0. 目标与Agent身份定义 (System Role & Objective)
本协议是专为具备代码执行能力（Code Interpreter/Advanced Data Analysis）的高阶人工智能语言模型（LLM Agent）编写的**工业级标准化执行物理协议**。
* **核心任务**：接收包含机械制图题目的手绘、拍照或扫描图片，通过计算机视觉进行高精度逆向校正，依托严格的机械工程制图标准（GB/T）进行数字几何求解与拓扑布尔填充，最终输出高分辨率、符合工程规范的矢量图纸。
* **绝对红线**：禁止调用任何随机生成、扩散或渐变式绘图API。所有图形线段、圆弧、剖面线必须拥有百分之百的确定性矢量坐标，每一像素的渲染必须由底层 Python 几何数学引擎计算产生。

---

## 1. 自动化多级坐标系与视口配置 (Viewport & Canvas Grid)
进入任务后，AI 引擎必须强制初始化全局归一化视口，将图像像素映射至数学直角坐标系：
* **Canvas定义**：全局画布尺寸设为 [0, 1000] x [0, 1000] 的二维欧几里得空间，左下角为数学原点 (0,0)，X轴正向水平向右，Y轴正向垂直向上。
* **投影制式**：强制默认执行**第一角画法（First-Angle Projection）**。
* **核心视图锚点绑定**：
  * **主视图（Front View）**：核心投影源，其几何中心锚点显式声明为 (X_FC, Y_FC)，底面极限线设为 Y_Baseline。
  * **俯视图（Top View）**：固定置于主视图正下方，中心锚点为 (X_TC, Y_TC)。硬性代数约束：X_TC = X_FC。
  * **左视图（Left View）**：固定置于主视图正右方，中心锚点为 (X_LC, Y_LC)。硬性代数约束：Y_LC = Y_FC。

---

## 2. 输入图像逆向计算机视觉校正管道 (Vision Homography Pipeline)
若输入图片包含手机斜拍导致的透视畸变、纸张旋转或边缘越界，AI 必须首行运行以下 Python OpenCV 变换流水线进行刚体与射影对齐：

```python
import cv2
import numpy as np

def transform_image_to_standard_canvas(image_path):
    img = cv2.imread(image_path)
    # 1. 边缘检测与自适应阈值分割
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    
    # 2. 查找最大闭合四边形（题框或作业本边界）
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    max_contour = max(contours, key=cv2.contourArea)
    
    # 3. 提取4个极端顶点坐标 (Top-Left, Top-Right, Bottom-Right, Bottom-Left)
    peri = cv2.arcLength(max_contour, True)
    approx = cv2.approxPolyDP(max_contour, 0.02 * peri, True)
    
    if len(approx) == 4:
        pts1 = np.float32([p[0] for p in approx])
        # 4. 映射到标准归一化 1000x1000 视口空间
        pts2 = np.float32([[0, 1000], [1000, 1000], [1000, 0], [0, 0]])
        M = cv2.getPerspectiveTransform(pts1, pts2)
        corrected_img = cv2.warpPerspective(img, M, (1000, 1000))
        return corrected_img
    return img
```

---

## 3. 标准化图层与国家标准物理线型映射 (Line Layer & Styling Matrix)
在绘图引擎内部，必须维护严格的图层逻辑。禁止任何图线发生越界或线型交叉干扰。各图层样式由下列物理矩阵强制绑定：

| 图层枚举值 (layer_id) | 制图国标应用场景 | 物理线宽 (Pixel) | 渲染颜色 (Hex) | 虚实线数学分布规则 (LineStyle) |
| :--- | :--- | :--- | :--- | :--- |
| **VISIBLE_OUTLINE** | 粗实线：可见外部轮廓、剖切产生的可见过渡棱边。 | 2.5 px | #000000 | solid (连续不断) |
| **HIDDEN_OUTLINE** | 细虚线：不可见的内部结构腔体、背部隐藏的孔槽边线。 | 0.8 px | #222222 | dashed (线长 4 px，空隙 2 px) |
| **CENTERLINE** | 细点画线：回转体中心轴线、对称面中心线、圆孔定位交线。 | 0.8 px | #FF0000 | (0, (16, 3, 2, 3)) (长划16, 空3, 短点2, 空3) |
| **HATCH_LINE** | 细实线：表示被切削实体材料断面的平行剖面线簇。 | 0.6 px | #444444 | solid，统一约束：倾角 45 度，步长 6 px |
| **WAVE_LINE** | 细实线：局部剖切面的范围断裂分界线。 | 0.6 px | #0000FF | 三阶连续贝塞尔曲线，禁止画成直线或锯齿线 |

---

## 4. 三视图代数投影守恒方程组 (Orthographic Geometry Invariants)
任何被补画或修改的特征点，其坐标推导必须使下列三视图投影代数方程组严格收敛。若不收敛，直接触发几何异常拦截。

### 4.1 水平长对正约束 (Horizontal Dimension Equivalence)
对于主视图内的任意特征几何极值点 P_Front(x_f, y_f) 与俯视图对应点 P_Top(x_t, y_t)：
x_f = x_t

### 4.2 垂直高平齐约束 (Vertical Dimension Equivalence)
对于主视图内的任意特征几何极值点 P_Front(x_f, y_f) 与左视图对应点 P_Left(x_l, y_l)：
y_f = y_l

### 4.3 空间宽相等中心对称映射守恒 (Depth Width Conservational Mapping)
设俯视图的水平对称中心线绝对纵坐标为 Y_Top_Center，左视图的垂直对称中心线绝对横坐标为 X_Left_Center。
特征距各自对称基准的单侧绝对距离 Δ 必须保持绝对刚性守恒：
Δ = |y_t - Y_Top_Center| = |x_l - X_Left_Center|

**平移象限守恒变换方程：**
1. 位于俯视图中心线上侧的后部空间特征（y_t > Y_Top_Center），必须投射映射至左视图中心线的左侧空间：
   x_l = X_Left_Center - Δ
2. 位于俯视图中心线下侧的前部空间特征（y_t < Y_Top_Center，有机件朝向观察者侧），必须投射映射至左视图中心线的右侧空间：
   x_l = X_Left_Center + Δ

---

## 5. 拓扑多边形面域布尔剖切算法引擎 (Topological Boolean Hatching Engine)
为彻底杜绝剖面线穿过空气孔、盲槽、腔体的逻辑性原理错误，AI 必须在图形层调用 Shapely 几何多边形库执行布尔实体差集计算。

```python
import shapely.geometry as sg
from shapely.ops import unary_union

def generate_precise_hatch_layer(outer_boundary_pts, holes_pts_list):
    # 1. 实例化最大闭合外轮廓多边形
    polygon_outer = sg.Polygon(outer_boundary_pts)
    
    # 2. 实例化并合并所有非材料空腔多边形
    hole_polygons = [sg.Polygon(pts) for pts in holes_pts_list if len(pts) >= 3]
    union_holes = unary_union(hole_polygons)
    
    # 3. 几何拓扑布尔求差：计算真正的物理实体肉厚面域
    polygon_solid = polygon_outer.difference(union_holes)
    
    # 4. 在画布范围内生成 45 度的超大型等距平行线簇
    raw_hatch_lines = []
    for offset in range(-1400, 1400, 6):
        line = sg.LineString([(0, offset), (1000, 1000 + offset)])
        raw_hatch_lines.append(line)
        
    # 5. 执行裁剪：只保留与实体多边形相交的线段
    final_hatch_lines = []
    for line in raw_hatch_lines:
        if line.intersects(polygon_solid):
            cropped_hatch = line.intersection(polygon_solid)
            if isinstance(cropped_hatch, sg.LineString):
                final_hatch_lines.append(cropped_hatch)
            elif isinstance(cropped_hatch, sg.MultiLineString):
                for sub_line in cropped_hatch.geoms:
                    final_hatch_lines.append(sub_line)
                    
    return final_hatch_lines
```

---

## 6. 各类题型算法化核心控制流 (Algorithmic Operational Blueprints)

### 6.1 半剖视图 (Half-Section View)
* **输入特征检测**：主轴对称。分界线两侧呈现互斥表现。
* **分界硬判定**：分界线强制设为 CENTERLINE（细点画线），禁止转为任何粗实线。
* **左侧/上方（视图半区）逻辑滤网**：
  * 执行判定：若图元落在该半区且属性为 HIDDEN_OUTLINE，强制运行 delete() 函数，全面隐藏不可见线，不画虚线。
* **右侧/下方（剖视半区）逻辑提升**：
  * 将所有在此半区内的内部孔槽、阶梯面对应的 HIDDEN_OUTLINE 属性无条件提升为 "VISIBLE_OUTLINE"，线宽修改为粗实线标准。
  * 限制边界条件：在点画线右侧/下侧区域内执行第5章的布尔填充算法。

### 6.2 旋转剖视图 (Rotated Section View)
当结构件的内部圆孔、沉孔分布在斜向或偏心圆周轴线上时，AI 必须对其坐标执行刚体旋转变换，严禁直接垂直投射：
* 设主要回转轴心为 (X_C, Y_C)，偏心结构的实测特征中心点为 (X_0, Y_0)，其特征轴线与主正交基准线的法向夹角为 θ。
* 执行二维齐次旋转矩阵映射计算，将其摆平至与正交投影面完全平行的虚拟位置 (X_Rotated, Y_Rotated)：
  X_Rotated = cos(θ)*(X_0 - X_C) - sin(θ)*(Y_0 - Y_C) + X_C
  Y_Rotated = sin(θ)*(X_0 - X_C) + cos(θ)*(Y_0 - Y_C) + Y_C
* 使用旋转修正后的全新几何基准线投射至目标全剖/半剖视图，严禁直接产生错位投影。

### 6.3 漏线补画判定树与线型收敛控制
在补齐缺失图线任务中，AI 必须将每条缺失线条放入以下二叉分支决策树执行逻辑收敛判定：

```text
               检测到跨视图投影缺失或不匹配
                            │
              ├─── 是否存在物理交线/棱边/端面界限?
              │         ├─── 否: 拦截退出，禁止多画(False)
              │         └─── 是: 进入可见性分析
              │
              └─── 该特征在此视角的法向射线上是否被遮挡?
                        ├─── 否: 赋予线型 "VISIBLE_OUTLINE" (粗实线)
                        └─── 是: 该视图是否已经被指定为剖视图?
                                  ├─── 否: 赋予线型 "HIDDEN_OUTLINE" (细虚线)
                                  └─── 是: 处于剖视切削面实体厚度内吗?
                                            ├─── 是: 赋予线型 "VISIBLE_OUTLINE" (粗实线化)
                                            └─── 否: 隐藏省略，不予画出
```

---

## 7. 军工级自动化单元测试门禁与硬性断言 (Hard Assertions Quality Gate)
Python 绘图引擎代码在渲染文件并展示给终端用户前，必须在后台静默跑通以下质量校验断言脚本。若有任意一项抛出异常，AI 必须强制回溯图元坐标参数，严禁直接交图。

```python
def execute_military_quality_gate(json_drawing_data, shapely_output_layers):
    # 门禁1：中心线垂直相交性校验 (圆孔定位中心线必须长划相交，禁止点或空隙相交)
    for element in json_drawing_data["geometries"]:
        if element["type"] == "CIRCLE" and element["line_style"] == "CENTERLINE":
            cx, cy = element["parameters"]["center_x"], element["parameters"]["center_y"]
            horiz_line = get_line_by_point(json_drawing_data, point=(cx, cy), direction="HORIZONTAL")
            vert_line = get_line_by_point(json_drawing_data, point=(cx, cy), direction="VERTICAL")
            assert is_point_on_long_dash(horiz_line, cx) and is_point_on_long_dash(vert_line, cy),                 "Security Exception: 圆孔中心定位线交点不符合长划相交规范！"

    # 门禁2：剖面线零透壁溢出校验 (剖面线多边形与空气孔槽多边形交集面积必须为0)
    hatch_poly = shapely_output_layers["HATCH_LINE"].buffer(0.001)
    holes_poly = shapely_output_layers["HOLES"]
    assert hatch_poly.intersection(holes_poly).area == 0.0,         "Topology Exception: 严重逻辑制图错误，剖面线非法侵入孔槽或空腔空气内部！"

    # 门禁3：加强筋/肋板纵向剖切不剖断言拦截
    rib_polygons = shapely_output_layers.get("RIBS", [])
    for rib in rib_polygons:
        assert shapely_output_layers["HATCH_LINE"].intersection(rib).area == 0.0,             "GB Standard Exception: 违反国标规定，肋板纵向剖切区不可画剖面线！"
            
    print("【Agent质量审计提示】自动化闭合验证 100% 通过。")
    return True
```

---

## 8. 高标准多格式物理交付规范 (Delivery Specification)
通过门禁校验后，AI Agent 必须以标准工程图纸格式向用户输出：
1. **高分辨率无损图纸**：导出宽度 >= 2400 px，DPI >= 300 的白底黑线高对比度纯净无水印 PNG 图像。
2. **三视图代数坐标映射表**：明示每一个补画图元端点的具体代数推算过程。
3. **闭合自检审计报告**：附带第7章硬断言脚本无异常通过的日志输出。
