---
description: 借助局部 viewBox、渐变、虚线和路径动画，绘制带有填充或描边的 SVG 路径。
---

# 路径 { #path }

`Canvas.path()` 支持使用标准 SVG 路径数据（`d`）绘制带有填充或描边的矢量路径，无需外部 SVG 文件或额外依赖：

```python
from quickthumb import Canvas

canvas = Canvas(160, 120).path(
    "M 0 0 H 100 V 100 H 0 Z M 25 25 H 75 V 75 H 25 Z",
    position=(20, 10),
    width=120,
    height=100,
    view_box=(0, 0, 100, 100),
    color="#42CEB7",
)
canvas.export("path.png")
```

## 参数 { #parameters }

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `d` | `str` | **必填** | SVG 路径指令（`M`、`L`、`H`、`V`、`C`、`S`、`Q`、`T`、`A`、`Z`）。 |
| `position` | `tuple` | **必填** | 像素或百分比字符串（`"50%"`）形式的 `(x, y)` 坐标。 |
| `width` | `int` | **必填** | 框体宽度（像素）。 |
| `height` | `int` | **必填** | 框体高度（像素）。 |
| `view_box` | `tuple \| None` | `None` | 局部坐标窗口 `(x, y, width, height)`。默认为 `(0, 0, width, height)`。 |
| `color` | `str \| None` | `"#000000"` | 纯色填充。仅需描边的路径请设为 `None`。 |
| `fill` | `LinearGradient \| RadialGradient \| None` | `None` | 渐变填充。提供时将覆盖 `color`。 |
| `stroke` | `str \| None` | `None` | 描边颜色（十六进制字符串）。 |
| `stroke_width` | `int \| float` | `1` | 局部单位下的描边粗细。 |
| `line_cap` | `str` | `"butt"` | 端点样式：`"butt"`、`"round"` 或 `"square"`。 |
| `line_join` | `str` | `"miter"` | 转角连接样式：`"miter"`、`"bevel"` 或 `"round"`。 |
| `miter_limit` | `float` | `4` | 切换为斜角（bevel）前的最大斜接比例（miter ratio）。 |
| `dash_array` | `tuple \| None` | `None` | 由线段与间隙长度组成的虚线模式元组 `(dash, gap, ...)`。 |
| `dash_offset` | `float` | `0` | 虚线模式的起始相位偏移量。 |
| `rotation` | `float` | `0.0` | 旋转角度（度数）。 |
| `opacity` | `float` | `1.0` | 图层不透明度，范围为 `0.0` 至 `1.0`。 |
| `anchor` | `tuple` | `(0.5, 0.5)` | 用于旋转与缩放的归一化锚点。 |
| `animation` | `AnimationSpec \| None` | `None` | 适用于位移、修剪、虚线相位或变形的时间轴动画。 |

## 示例 { #examples }

### 带虚线描边的曲线 { #stroked-curves-with-dashed-outline }

```python
canvas.path(
    "M10 50 C30 0 70 100 90 50",
    position=(20, 10),
    width=120,
    height=100,
    color=None,
    stroke="#42CEB7",
    stroke_width=6,
    line_cap="round",
    view_box=(0, 0, 100, 100),
    dash_array=(12, 6),
    dash_offset=3,
)
```

### 带有镂空的渐变填充 { #gradient-fill-with-cutouts }

路径采用**奇偶填充规则（even-odd fill rule）**：重叠的内部轮廓会自然形成镂空或孔洞。

```python
from quickthumb import LinearGradient

canvas.path(
    "M10 10 H90 V90 H10 Z M30 30 H70 V70 H30 Z",
    position=(20, 10),
    width=120,
    height=100,
    color=None,
    fill=LinearGradient(angle=45, stops=[("#42CEB7", 0), ("#315D8E", 1)]),
    view_box=(0, 0, 100, 100),
)
```

## 路径动画 { #path-animations }

### 虚线相位动画（蚂蚁线走马灯） { #animated-dash-phase-marching-ants }

为 `DashOffsetTrack` 制作动画可生成虚线沿路径流动的爬行效果：

```python
from quickthumb import AnimationSpec, DashOffsetTrack, KeyframeSpec, TimingSpec

phase_animation = AnimationSpec.timeline(
    DashOffsetTrack(keyframes=[
        KeyframeSpec(time=0, value=0),
        KeyframeSpec(time=1, value=20),
    ]),
    timing=TimingSpec(duration=1),
    easing="linear",
)

canvas.path(
    "M0 10 H100",
    position=(10, 10),
    width=200,
    height=20,
    color=None,
    stroke="#42CEB7",
    dash_array=(6, 4),
    animation=phase_animation,
)
```

### 描边修剪（路径自绘制线条） { #stroke-trim-self-drawing-line }

使用 `TrimEndTrack` 可以实现线条或轮廓从头到尾逐步绘制的效果：

```python
from quickthumb import AnimationSpec, KeyframeSpec, TimingSpec, TrimEndTrack

draw_outline = AnimationSpec.timeline(
    TrimEndTrack(keyframes=[
        KeyframeSpec(time=0, value=0.0),
        KeyframeSpec(time=1.5, value=1.0),
    ]),
    timing=TimingSpec(duration=1.5),
    easing="ease_in_out",
)

canvas.path(
    "M0 20 Q50 -10 100 20",
    position=(20, 20),
    width=200,
    height=60,
    view_box=(0, -10, 100, 30),
    color=None,
    stroke="#42CEB7",
    stroke_width=4,
    animation=draw_outline,
)
```

- `TrimStartTrack` 与 `TrimEndTrack`：沿路径总长度的归一化端点（`0.0` 至 `1.0`）。
- `TrimOffsetTrack`：沿路径平移修剪区间。

### 路径变形 { #path-morphing }

使用 `PathMorphTrack` 可以将一种矢量图形平滑变形为另一种图形：

```python
from quickthumb import AnimationSpec, KeyframeSpec, PathMorphTrack, TimingSpec

morph = AnimationSpec.timeline(
    PathMorphTrack(keyframes=[
        KeyframeSpec(time=0, value="M10 10 H50 V50 H10 Z"),
        KeyframeSpec(time=1, value="M20 20 H60 V60 H20 Z"),
    ]),
    timing=TimingSpec(duration=1),
    easing="ease_in_out",
)

canvas.path(
    "M10 10 H50 V50 H10 Z",
    position=(10, 10),
    width=100,
    height=100,
    color="#42CEB7",
    animation=morph,
)
```

每个关键帧必须包含 1 至 16 个非退化轮廓，且轮廓数量、顺序、闭合状态、环绕方向以及嵌套结构必须完全一致。轮廓之间在过渡期间亦不可相交或接触。不兼容的关键帧会抛出 `path_morph_topology` 异常；若过渡过程中产生无效的中间形态，则会在渲染时报错，而不是静默改变拓扑结构。

复杂轮廓可能会超出每个轮廓最多 256 个细分顶点、4096 个对应点或 100 万次边缘对比较的资源上限。重新采样必须将顶点控制在局部 SVG 单位 ¼ 范围内；放大显示可能会使该近似误差可见。若变形准备阶段被拒绝，请简化路径。

## 导出支持 { #export-support }

- **光栅与视频（PNG、GIF、MP4、WebM）**：支持渲染路径、虚线、修剪及变形动画。
- **Lottie**：将受支持的[路径变形动画](../reference/export-lottie.md#lottie-path-morph)导出为矢量数据。
- **HTML**：针对受支持的开放路径使用原生 SVG 渲染及 CSS 描边动画。变形动画使用创作时的静态图像。
- **PDF 与 PPTX**：将受支持的路径导出为矢量图形；变形动画使用创作时的静态图像。
