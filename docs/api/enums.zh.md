---
description: 用于对齐、填充适配模式、形状、滤镜及颜色渐变的 quickthumb 枚举与渐变模型参考文档。
---

# 枚举与渐变 { #enums-gradients }

## Align { #align }

控制 `position` 坐标点对应图层的哪个基准点，以及文本的水平对齐方式。

```python
from quickthumb import Align
```

### 值 { #values }

| 枚举 | 字符串别名 | 水平对齐 | 垂直对齐 |
| --- | --- | --- | --- |
| `Align.CENTER` | `"center"` | center（居中） | middle（居中） |
| `Align.LEFT` | `"left"` | left（左对齐） | middle（居中） |
| `Align.RIGHT` | `"right"` | right（右对齐） | middle（居中） |
| `Align.TOP_LEFT` | `"top-left"` | left（左对齐） | top（顶对齐） |
| `Align.TOP_CENTER` | `"top-center"` | center（居中） | top（顶对齐） |
| `Align.TOP_RIGHT` | `"top-right"` | right（右对齐） | top（顶对齐） |
| `Align.BOTTOM_LEFT` | `"bottom-left"` | left（左对齐） | bottom（底对齐） |
| `Align.BOTTOM_CENTER` | `"bottom-center"` | center（居中） | bottom（底对齐） |
| `Align.BOTTOM_RIGHT` | `"bottom-right"` | right（右对齐） | bottom（底对齐） |

### 使用法 { #usage }

```python
# Enum value
canvas.image(..., align=Align.TOP_LEFT)

# String alias
canvas.image(..., align="center")

# (horizontal, vertical) tuple
canvas.image(..., align=("center", "middle"))
```

水平元组取值：`"left"`、`"center"`、`"right"`
垂直元组取值：`"top"`、`"middle"`、`"bottom"`

---

## BlendMode { #blendmode }

控制图层与下方已有图层的混合合成方式。

```python
from quickthumb import BlendMode
```

### 值 { #values_1 }

| 枚举 | 字符串别名 | 视觉效果 |
| --- | --- | --- |
| `BlendMode.NORMAL` | `"normal"` | 正常模式；无特殊混合，直接覆盖在上层 |
| `BlendMode.MULTIPLY` | `"multiply"` | 正片叠底；通过相乘颜色数值达到变暗效果 |
| `BlendMode.OVERLAY` | `"overlay"` | 叠加；结合正片叠底与滤色 |
| `BlendMode.SCREEN` | `"screen"` | 滤色；通过反转、相乘再反转达到变亮效果 |
| `BlendMode.DARKEN` | `"darken"` | 变暗；取两个图层中每个像素的较暗值 |
| `BlendMode.LIGHTEN` | `"lighten"` | 变亮；取两个图层中每个像素的较亮值 |

### 使用法 { #usage_1 }

```python
# Enum value
canvas.background(image="texture.jpg", blend_mode=BlendMode.MULTIPLY)

# String alias
canvas.background(image="texture.jpg", blend_mode="multiply")
```

适用于：`.background()` 与 `.image()`。

---

## FitMode { #fitmode }

当定义了目标尺寸边界框时，控制图片的缩放适配方式。

```python
from quickthumb import FitMode
```

### 值 { #values_2 }

| 枚举 | 字符串别名 | 缩放行为 |
| --- | --- | --- |
| `FitMode.COVER` | `"cover"` | 填满边界框，超出部分自动裁切 |
| `FitMode.CONTAIN` | `"contain"` | 完整容纳在边界框内，留出黑边/空白 |
| `FitMode.FILL` | `"fill"` | 忽略原始比例拉伸，恰好填满边界框 |

### 使用法 { #usage_2 }

```python
# Enum value
canvas.image(path="portrait.png", position=("75%", "55%"), width=420, height=520, fit=FitMode.COVER)

# String alias
canvas.image(path="portrait.png", position=("75%", "55%"), width=420, height=520, fit="cover")
```

适用于：`.background(image=...)` 与 `.image()`。仅在同时指定 `width` 和 `height` 定义了目标边界框时生效（对于背景图层则为整个画布）。

---

## LinearGradient { #lineargradient }

由角度与颜色停靠点定义的线性渐变。

```python
from quickthumb import LinearGradient

LinearGradient(
    angle=135,
    stops=[("#FF5733", 0.0), ("#3333FF", 1.0)],
)
```

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `angle` | `float` | 渐变方向（角度）。`0` = 从上到下，`90` = 从左到右。 |
| `stops` | `list[tuple[str, float]]` | `(color, position)` 元组列表。位置为 `0.0` 到 `1.0` 的浮点数。 |

### 示例 { #examples }

```python
# Top-to-bottom dark fade
LinearGradient(angle=0, stops=[("#000000", 0.0), ("#00000000", 1.0)])

# Diagonal blue-to-purple
LinearGradient(angle=135, stops=[("#3B82F6", 0.0), ("#8B5CF6", 1.0)])

# Three-stop gradient
LinearGradient(
    angle=90,
    stops=[("#FF0000", 0.0), ("#00FF00", 0.5), ("#0000FF", 1.0)],
)
```

传递给 `.background(gradient=...)`：

```python
canvas.background(
    gradient=LinearGradient(angle=120, stops=[("#0F172A", 0.0), ("#0F172A00", 1.0)]),
    opacity=0.8,
)
```

---

## RadialGradient { #radialgradient }

从中心点向外辐射发散的径向渐变。

```python
from quickthumb import RadialGradient

RadialGradient(
    stops=[("#FF5733", 0.0), ("#3333FF", 1.0)],
    center=(0.5, 0.5),
)
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `stops` | `list[tuple[str, float]]` | **必填** | `(color, position)` 元组列表。位置为 `0.0` 到 `1.0` 的浮点数。 |
| `center` | `tuple[float, float]` | `(0.5, 0.5)` | 渐变中心点，以画布尺寸比例 `(x, y)` 表示。 |

### 示例 { #examples_1 }

```python
# Vignette (dark edges, bright center)
RadialGradient(
    stops=[("#00000000", 0.0), ("#000000CC", 1.0)],
    center=(0.5, 0.5),
)

# Off-center spotlight
RadialGradient(
    stops=[("#FFFFFF33", 0.0), ("#FFFFFF00", 1.0)],
    center=(0.25, 0.3),
)
```

传递给 `.background(gradient=...)`：

```python
canvas.background(
    gradient=RadialGradient(
        stops=[("#22d3ee33", 0.0), ("#22d3ee00", 1.0)],
        center=(0.5, 0.5),
    ),
)
```

---

## TextFillImage { #textfillimage }

用于文本字形填充的图片。图片会按比例缩放到文本边界框，并按字形轮廓进行蒙版遮罩。

```python
from quickthumb import TextFillImage

TextFillImage(
    path="fire_texture.jpg",
    fit="cover",
)
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `path` | `str` | **必填** | 填充图片的本地文件路径或远程网络 URL。 |
| `fit` | `str \| FitMode` | `"cover"` | 图片在文本边界框内的适配方式：`"cover"`、`"contain"` 或 `"fill"`。 |

### 示例 { #examples_2 }

```python
from quickthumb import Canvas, TextFillImage

# Local file
canvas.text(
    content="FIRE",
    size=140,
    fill=TextFillImage(path="assets/fire_texture.jpg", fit="cover"),
    position=("50%", "50%"),
    align="center",
)

# Remote URL
canvas.text(
    content="MARBLE",
    size=140,
    fill=TextFillImage(
        path="https://example.com/textures/marble.jpg",
        fit="cover",
    ),
    position=("50%", "50%"),
    align="center",
)
```

将 `TextFillImage` 传递给 `.text()` 或 `TextPart` 的 `fill` 参数。上下文实际用法请参阅[渐变与图片填充](text.md#gradient-and-image-fills)。
