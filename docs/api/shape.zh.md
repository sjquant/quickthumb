---
description: quickthumb 形状图层参考，涵盖矩形、椭圆、胶囊形、三角形、星形、多边形以及描边、投影和定位。
---

# 形状 { #shape }

`.shape()` 用于在指定位置添加基础几何图形：矩形、椭圆、胶囊形、三角形、星形或多边形。

## 方法签名 { #signature }

```python
canvas.shape(
    shape,
    position,
    width,
    height,
    color,
    fill=None,
    border_radius=0,
    opacity=1.0,
    rotation=0.0,
    align=None,
    points=None,
    star_points=5,
    inner_radius=0.5,
    effects=None,
)
```

## 参数 { #parameters }

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `shape` | `str` | **必填** | 形状类型：`"rectangle"`、`"ellipse"`、`"pill"`、`"triangle"`、`"star"` 或 `"polygon"`。 |
| `position` | `tuple` | **必填** | `(x, y)` 坐标。取值可为整数（像素）或百分比字符串（`"50%"`）。 |
| `width` | `int` | **必填** | 形状宽度（像素）。正整数。 |
| `height` | `int` | **必填** | 形状高度（像素）。正整数。 |
| `color` | `str` | **必填** | 填充颜色。十六进制字符串（`"#RRGGBB"` 或 `"#RRGGBBAA"`）。 |
| `fill` | `LinearGradient \| RadialGradient \| None` | `None` | 渐变填充，作用于形状内部并随形状一同旋转。对于无法绘制渐变的导出目标（PPTX、PDF、SVG、HTML），`color` 将作为纯色降级回退选项。 |
| `border_radius` | `int` | `0` | 圆角半径（像素）。仅适用于 `"rectangle"`。非负整数。 |
| `opacity` | `float` | `1.0` | 图层不透明度，范围为 `0.0` 至 `1.0`。 |
| `rotation` | `float` | `0.0` | 旋转角度（度数）。 |
| `align` | `str \| Align \| tuple \| None` | `None` | `position` 对应的形状对齐参考点。参见 [Align](enums.md#align)。 |
| `points` | `list[tuple[float, float]] \| None` | `None` | `"polygon"` 形状的顶点列表，在形状框内归一化为 `0.0`–`1.0`。至少需要 3 个点。 |
| `star_points` | `int` | `5` | 星形的尖角数量。仅适用于 `"star"`。最小值为 3。 |
| `inner_radius` | `float` | `0.5` | `"star"` 的内径与外径之比，取值必须严格介于 `0.0` 至 `1.0` 之间。 |
| `effects` | `list \| None` | `[]` | 效果列表：`Stroke`、`Shadow`、`Glow`。 |

## 示例 { #examples }

### 标签矩形 { #label-rectangle }

```python
from quickthumb import Shadow, Stroke

canvas.shape(
    shape="rectangle",
    position=(64, 64),
    width=320,
    height=96,
    color="#CC0000",
    border_radius=14,
    effects=[
        Stroke(width=3, color="#FFFFFF"),
        Shadow(offset_x=0, offset_y=10, color="#000000", blur_radius=18),
    ],
)
```

### 旋转徽章 { #rotated-badge }

```python
canvas.shape(
    shape="rectangle",
    position=(64, 64),
    width=360,
    height=120,
    color="#CC0000",
    border_radius=16,
    opacity=0.95,
    rotation=-4,
    align=("left", "top"),
)
```

### 椭圆与圆形 { #ellipse-circle }

```python
# Circle: set width == height
canvas.shape(
    shape="ellipse",
    position=("50%", "50%"),
    width=200,
    height=200,
    color="#22d3ee",
    align=("center", "middle"),
)
```

### 胶囊形 { #pill }

两端完全圆弧化的矩形胶囊，无需设置 `border_radius`。

```python
canvas.shape(
    shape="pill",
    position=(64, 60),
    width=220,
    height=56,
    color="#B8FF00",
)
```

### 三角形 { #triangle }

朝上的等腰三角形，内切于 `width` × `height` 边界框中。使用 `rotation` 可以调整朝向。

```python
canvas.shape(
    shape="triangle",
    position=("50%", "20%"),
    width=140,
    height=120,
    color="#F59E0B",
    align=("center", "middle"),
    rotation=180,   # point down
)
```

### 星形 { #star }

`star_points` 设置角数；`inner_radius` 控制角的尖锐程度（越小越尖锐）。

```python
from quickthumb import Glow

canvas.shape(
    shape="star",
    position=("80%", "50%"),
    width=280,
    height=280,
    color="#7C5CFF",
    align=("center", "middle"),
    rotation=12,
    star_points=5,
    inner_radius=0.45,
    effects=[Glow(color="#7C5CFF", radius=40, opacity=0.5)],
)
```

### 多边形 { #polygon }

在形状框内通过归一化坐标定义顶点：`(0.0, 0.0)` 为左上角，`(1.0, 1.0)` 为右下角。

```python
# A right-pointing arrow
canvas.shape(
    shape="polygon",
    position=(600, 60),
    width=160,
    height=100,
    color="#53BF9D",
    points=[
        (0.0, 0.25), (0.6, 0.25), (0.6, 0.0),
        (1.0, 0.5),
        (0.6, 1.0), (0.6, 0.75), (0.0, 0.75),
    ],
)
```

### 带发光效果的居中形状 { #centered-shape-with-glow }

```python
from quickthumb import Glow

canvas.shape(
    shape="rectangle",
    position=("50%", "80%"),
    width=480,
    height=72,
    color="#111827",
    border_radius=36,
    align=("center", "middle"),
    effects=[Glow(color="#22d3ee", radius=24, opacity=0.4)],
)
```

## 校验规则 { #validation-rules }

- `shape`、`position`、`width`、`height` 和 `color` 为必填项。
- `position` 必须为包含 2 个元素的元组。百分比字符串必须符合 `-?N%` 格式。
- `border_radius` 不能为负数。
- `opacity` 必须介于 `0.0` 至 `1.0` 之间。
- `points` 仅在 `"polygon"` 时必填，其余形状类型下传入会被拒绝。至少包含 3 个顶点，每个坐标归一化在 `0.0` 至 `1.0` 之间。
- `star_points` 必须至少为 3；`inner_radius` 必须严格介于 `0.0` 至 `1.0` 之间。
