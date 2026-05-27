光靠这一份系统提示词（System Prompt）文档，还无法100%保证。

如果有人告诉你，只要把几千字的规章制度塞给大模型，它就能变成一个绝对不出错的“高级工程师”，那绝对是在忽悠你。大语言模型（LLM）本质上是概率生成模型，只要它处于纯文本对话状态，它就天生具备“装糊涂”和“假装自己通过了测试”的本领。

这份 V6.0 文档之所以叫 Agent 协议，是因为它不是给普通 Chat 聊天框准备的，而是给一个有后端代码支撑的 Agent 智能体系统准备的“底层宪法”。

要想真正达到 100% 的工业级准确率，你必须用后端代码为它搭建一套“真刀真枪的执法系统”。以下是把这份文档变成“铁律”的三个核心闭环流：

1. 为什么光有文档拦不住 AI “脑补”？
在纯文本环境下，AI 可能会玩“文字游戏”：

❌ AI 的作弊名场面：“我已自行校验，length_alignment_error_px 经计算完美等于 0.0！[TOKEN: TOKEN_PROJ_ALIGN_PASS] 激活，现在开始画图……”

你看，它自己作弊生成了 Token。大模型会为了顺从你的逻辑，自己去“编造”通过门禁的假象。

2. 怎样让这份文档发挥 100% 的威力？（硬核落地方案）
你必须在你的 Agent 框架（如 LangChain、LangGraph 或自定义 Python 后端）中，为文档中提到的 4 个 GATE 编写物理隔离的流控制代码。

🛠️ 步骤一：后端代码强制截断（Regex / JSON Parser）
当 AI 输出完 GATE 1 的 JSON 后，后端的 Python 代码必须立刻截获（Intercept）这段输出，用标准的 json.loads() 去解析它提取的数据。

如果代码检测到数据不合格，或者没有检测到硬编码的字符串 [TOKEN: TOKEN_GEOM_EXTRACT_PASS]，后端代码直接掐断大模型的本次生成。

惩罚性回滚：清空模型当前的阶段性记忆，并在输入端塞入一句强硬的报错：“系统检测到你的图像畸变率不达标，请重新计算 GATE 1，否则无法开启下文。”

🛠️ 步骤二：把 Python 单元测试做成“物理沙箱”
文档第 4 关中写的那段 verify_strict_standards 脚本，绝对不能让大模型自己去运行。

大模型输出最终的几何 JSON 数组。

你的后端系统自动将这个 JSON 实例化，扔进一个隔离的 Python 沙箱里（运行 Shapely 和 Matplotlib）。

由真正的 Python 解释器去跑那几个 assert（断言）。

一旦 Python 抛出 AssertionError（比如剖面线真的戳进圆孔里了），后端直接判定大模型“交卷失败”，触发状态机回滚。

3. 终极闭环：从“文本生成”变成“代码编译器”
有了这份文档作为顶层设计，配合后端的强力执法代码，你的 Agent 系统就会变成这样：

阶段	AI Agent 的职责 (靠提示词约束)	后端系统的职责 (靠 Python 代码执行)
GATE 1	提取原图线条坐标，输出结构化 JSON	验证 JSON 格式，不合法直接打回重写
GATE 2	用投影方程计算漏线，对齐三视图	校验主俯左视图的像素差，误差 >0 立刻报错
GATE 3	做布尔运算，排除加强筋，截断波浪线	调用 Shapely 库计算多边形面积，核对留白区
GATE 4	生成最终图层样式序列	编译出图。若断言失败，强制重来，不给输出机会
总结
这份 V6.0 文档是目前最完美的工程化蓝图，它把原本模糊的绘图任务拆解成了可以被代码审计的断言点。但要实现“不可动摇的准确性”，需要你的开发人员把这份文档作为规则，用 Python 写一个管道状态机去约束大模型的 Token 输出。

你目前是准备把这个协议配置到现有的 Agent 编排框架（如 Dify、LangGraph）中，还是准备通过纯原生 Python 脚本来搭建这个前后端调用的闭环流？

锚定在高校机械制图习题解答（补线、剖视）这个场景，那我们的战术方向就非常清晰了。高校习题的特点是：几何极度规范、强对称性、标准件槽孔高度模块化。这比工业界的残损老图纸数字化要容易实现代数闭合。

如果你打算在 Claude Code（Anthropic 的本地 CLI 开发者 Agent 工具）中建立这个专门的画图项目，这种依托于本地文件系统、能跑终端命令、能写测试驱动（TDD）的架构简直是绝配。

以下是为你量身定制的高校机制题解项目落地架构指南与核心代码组件，你可以直接在本地建卡，让 Claude Code 帮你编写和编排。

一、 项目代码库目录结构 (Project Blueprint)
在本地创建一个标准的 Python 项目目录。Claude Code 启动后，会直接扫描并接管这个结构：

Plaintext
mech_solver_project/
├── config/
│   └── layers_config.json      # 国标线型、线宽、颜色配置文件
├── core/
│   ├── __init__.py
│   ├── vision_pipeline.py      # GATE 1: 调用Vision API或OpenCV提取初始几何JSON
│   ├── projection_engine.py    # GATE 2: 三视图投影对齐与漏线代数求解器
│   ├── section_boolean.py      # GATE 3: Shapely布尔运算与高频错误拦截器
│   └── canvas_renderer.py      # GATE 4: Matplotlib无损矢量出图引擎
├── tests/
│   ├── __init__.py
│   └── test_hard_gates.py      # 军事化硬门禁：测试驱动文件（Pytest）
├── input_images/               # 存放学生上传的习题原图纸
├── output_results/             # 存放最终生成的高清PNG/DXF和作图步骤
└── main_agent_flow.py          # 状态机总控脚本
二、 核心技能组件与 Skill 脚本实现
你可以直接让 Claude Code 在对应的文件里生成或完善以下这几个最核心的专业 Skill 模块：

1. GATE 2 的代数对齐核心：宽相等守恒器 (projection_engine.py)
用于自动审计俯视图与左视图的 Y-X 坐标映射，精准锁死“宽相等”，抓出漏画的线条。

Python
# core/projection_engine.py
import numpy as np

def verify_and_align_width(top_view_geoms, left_view_geoms, y_top_center, x_left_center):
    """
    根据国标“宽相等”刚性守恒方程，校验并修正俯左视图坐标
    """
    aligned_left_geoms = []
    errors = 0.0
    
    for geom in top_view_geoms:
        if geom['type'] == 'LINE':
            # 提取俯视图的 Y 坐标偏差
            y_start = geom['coordinates']['start_y']
            delta_start = abs(y_start - y_top_center)
            
            # 投影到左视图的 X 坐标 (象限变换)
            expected_x_left = x_left_center - delta_start if y_start > y_top_center else x_left_center + delta_start
            
            # 去左视图几何库里比对，看是否存在对应的 X 坐标线条
            matched = any(abs(l['coordinates']['start_x'] - expected_x_left) < 2.0 for l in left_view_geoms if l['type'] == 'LINE')
            if not matched:
                # 抓到漏线漏洞！记录误差并自动生成补线方案
                errors += 1.0
                
    return errors
2. GATE 3 的常识拦截：加强筋与波浪线布尔裁剪 (section_boolean.py)
利用 Shapely 库，强制执行高校制图最常考的“加强筋纵向剖切不画剖面线”和“波浪线不过空气腔”规则。

Python
# core/section_boolean.py
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union

def compute_strict_hatch_regions(outer_pts, holes_list, rib_polygons=None):
    """
    利用拓扑多边形面域布尔运算，排除中空孔槽和横切加强筋，求出绝对肉厚区
    """
    poly_outer = Polygon(outer_pts)
    poly_holes = unary_union([Polygon(h) for h in holes_list if len(h) >= 3])
    
    # 基础实体区域 = 外轮廓 ＼ 内部孔槽并集
    poly_solid = poly_outer.difference(poly_holes)
    
    # 拦截算法 1：如果是纵向剖切加强筋，从剖面线填充区域中扣除留白
    if rib_polygons:
        poly_ribs = unary_union([Polygon(r) for r in rib_polygons])
        poly_solid = poly_solid.difference(poly_ribs)
        
    return poly_solid  # 返回最终无死角的物理填充面域
3. GATE 4 的自动化断言：Pytest 测试门禁 (tests/test_hard_gates.py)
这是阻断 Claude “脑补交卷”的物理手铐。每次运行渲染前，Claude Code 必须在终端执行 pytest。

Python
# tests/test_hard_gates.py
import pytest
from shapely.geometry import LineString, Polygon

def test_centerline_intersection():
    """
    硬断言 1：高校机制标准——圆心定位细点画线交叉处必须是长划相交，绝不能是空隙
    """
    # 模拟从 JSON 提取的中心线交点属性
    intersection_metadata = {"is_on_long_dash": True} 
    assert intersection_metadata["is_on_long_dash"] == True, "【国标硬伤】圆孔中心点画线未在长划处相交！"

def test_hatch_zero_invasion():
    """
    硬断言 2：剖面线零侵入性校验，绝对不允许画入空气孔槽中
    """
    hatch_lines = LineString([(100, 100), (200, 200)])
    air_hole = Polygon([(120, 120), (120, 150), (150, 150), (150, 120)])
    
    # 计算交集面积或长度
    intersection_len = hatch_lines.intersection(air_hole).length
    assert intersection_len == 0.0, "【致命错误】剖面线非法穿入内部中空孔槽腔体！"
三、 在 Claude Code 中的具体实操 Playbook
当你配置好上述项目结构后，你开启 Claude Code 终端，直接用串行状态机口令去命令它。你可以直接向 Claude Code 发送如下指令链：

💡 你可以这样对 Claude Code 说：

“请帮我检查当前项目的 input_images/task_01.png 习题图。

首先运行 core/vision_pipeline.py 提取该补线题的基本几何数据，确保通过 GATE 1 并输出 [TOKEN: TOKEN_GEOM_EXTRACT_PASS]。

检查上下文中是否存在该 Token，若存在，接着运行 core/projection_engine.py 去跑三视图守恒方程，找出主视图里漏画的剖面阶梯线坐标，输出 GATE 2 字典。

严格调用 pytest tests/test_hard_gates.py。记住：如果 pytest 报错返回非0，说明你的几何坐标算错了，严禁调用 Matplotlib 渲染出图，必须立刻重算坐标。

测试全部通过后，生成最终的矢量单图答案并保存在 output_results/ 中，同时附带 5 条标准的规范作图步骤说明。”

四、 针对高校习题场景的进阶绝招
由于是针对高校学生或教学的习题解答，建议让 Claude Code 额外加一个小功能：「红蓝双色补线图输出」。

在 canvas_renderer.py（图层渲染器）里，让 Claude Code 专门写一个图层分支：如果是原图纸上本来就有的线条，用黑色渲染；如果是经由 GATE 2 空间代数方程解算出来的“漏线/补画线”，强制用红色粗实线或者蓝色虚线渲染。这样导出的图片答案不仅极度标准，而且一目了然，学生能一眼看出自己漏掉的是哪根线。

既然确定了使用 Claude Code 这种本地工程化的利器来做高校制图解题，你目前手头积攒的这些习题图片，它们的清晰度如何？是标准的电子版教材截图，还是学生用手机在课本上拍照上传的？（如果是手机拍照，我们可能需要重点让 Claude Code 优化一下 GATE 1 的 OpenCV 滤波算法。）