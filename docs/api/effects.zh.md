---
description: quickthumb 效果参考文档（描边、投影、发光、滤镜、文本背景框、颗粒、双色调、内阴影、背景模糊）及各图层支持情况。
---

# 效果 { #effects }

效果（Effects）用于改变单个图层的绘制外观。每种图层类型支持其特定的效果集合，传入不支持的效果将抛出 `ValidationError`。

| 效果 | 文本（Text） | 图像、SVG、视频 | 形状（Shape） | 背景（Background） |
| --- | :---: | :---: | :---: | :---: |
| `Stroke` | ✓ | ✓ | ✓ | — |
| `Shadow` | ✓ | ✓ | ✓ | — |
| `Glow` | ✓ | ✓ | ✓ | — |
| `Filter` | — | ✓ | — | ✓ |
| `Background` | ✓ | — | — | — |
| `Grain` | — | ✓ | — | ✓ |
| `Duotone` | — | ✓ | — | — |
| `InnerShadow` | — | ✓ | ✓ | — |
| `BackdropBlur` | — | ✓ | ✓ | — |

将效果以列表形式传递给任意图层的 `effects` 参数：

```python
from quickthumb import Shadow, Stroke

canvas.text(
    content="CLICK NOW",
    size=96,
    color="#FFFFFF",
    effects=[
        Stroke(width=4, color="#000000"),
        Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
    ],
)
```

---

## Stroke { #stroke }

围绕文本字形、图像边缘或形状轮廓绘制描边。

```python
from quickthumb import Stroke

Stroke(width=4, color="#000000")
```

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `width` | `int` | 描边粗细（像素）。必须为正整数。 |
| `color` | `str` | 描边颜色。十六进制字符串（`"#RRGGBB"` 或 `"#RRGGBBAA"`）。 |

### 示例 { #example }

```python
from quickthumb import Stroke, TextPart

canvas.text(
    content=[
        TextPart(text="BIG TEXT", color="#FFFFFF", effects=[Stroke(width=6, color="#000000")]),
    ],
    size=108,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

---

## Shadow { #shadow }

为图层添加带偏移的外阴影（投影）。

```python
from quickthumb import Shadow

Shadow(offset_x=4, offset_y=8, color="#000000", blur_radius=12)
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `offset_x` | `int` | **必填** | 水平阴影偏移量（像素）。可为负数。 |
| `offset_y` | `int` | **必填** | 垂直阴影偏移量（像素）。可为负数。 |
| `color` | `str` | **必填** | 阴影颜色。十六进制字符串。 |
| `blur_radius` | `int` | `0` | 模糊扩散半径（像素）。非负整数。 |

### 示例 { #example_1 }

```python
from quickthumb import Shadow

canvas.image(
    path="portrait.png",
    position=("74%", "54%"),
    width=420,
    height=520,
    effects=[Shadow(offset_x=0, offset_y=14, color="#000000", blur_radius=24)],
)
```

---

## Glow { #glow }

围绕图层边缘添加柔和的彩色光晕外发光。

```python
from quickthumb import Glow

Glow(color="#B8FF00", radius=16, opacity=0.35)
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `color` | `str` | **必填** | 发光颜色。十六进制字符串。 |
| `radius` | `int` | **必填** | 发光扩散半径（像素）。正整数。 |
| `opacity` | `float` | `1.0` | 发光强度，取值范围 `0.0` 到 `1.0`。 |

### 示例 { #example_2 }

```python
from quickthumb import Glow

canvas.text(
    content="ELECTRIC",
    size=96,
    color="#FFFFFF",
    effects=[Glow(color="#22d3ee", radius=24, opacity=0.5)],
)
```

---

## Filter { #filter }

应用图像处理调整滤镜。适用于背景图层和图像图层。

```python
from quickthumb import Filter

Filter(blur=4, brightness=0.75, contrast=1.1, saturation=0.9)
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `blur` | `int` | `0` | 高斯模糊半径。非负整数。 |
| `brightness` | `float` | `1.0` | 亮度倍数。正浮点数。`1.0` = 原始亮度，`0.5` = 半亮度。 |
| `contrast` | `float` | `1.0` | 对比度倍数。正浮点数。`1.0` = 原始对比度。 |
| `saturation` | `float` | `1.0` | 饱和度倍数。非负浮点数。`0.0` = 灰度黑白，`1.0` = 原始饱和度。 |

所有参数默认值均为中性无调整，因此只需指定你希望更改的参数。

### 示例 { #example_3 }

```python
from quickthumb import Filter

canvas.background(
    image="hero.jpg",
    fit="cover",
    effects=[Filter(blur=6, brightness=0.6, saturation=0.8)],
)
```

---

## Background（文本背景框） { #background-text-fill }

在文本块下方绘制填充的圆角矩形背景框。仅适用于文本图层。

```python
from quickthumb import Background

Background(color="#111827CC", padding=(16, 24), border_radius=14, opacity=1.0)
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `color` | `str` | **必填** | 填充颜色。十六进制字符串（`"#RRGGBB"` 或 `"#RRGGBBAA"`）。 |
| `padding` | `int \| tuple` | `0` | 内边距。单个 `int` 表示四边统一，`(vertical, horizontal)` 或 `(top, right, bottom, left)`。 |
| `border_radius` | `int` | `0` | 圆角半径（像素）。非负整数。 |
| `opacity` | `float` | `1.0` | 填充不透明度，取值范围 `0.0` 到 `1.0`。 |

### 示例 { #example_4 }

```python
from quickthumb import Background

canvas.text(
    content="BREAKING NEWS",
    size=72,
    color="#FFFFFF",
    position=("8%", "50%"),
    align=("left", "middle"),
    effects=[
        Background(color="#CC0000", padding=(12, 20), border_radius=8),
    ],
)
```

!!! note "说明"
    作为效果的 `Background` 与 `.background()` 全局背景图层构建器相互独立。该效果仅包裹紧贴文本块呈现；而全局背景图层则覆盖整个画布。

---

## Grain { #grain }

为背景或图像图层添加胶片噪点颗粒。

```python
from quickthumb import Grain

Grain(intensity=0.12, monochrome=True, blend_mode="overlay", opacity=1.0)
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `intensity` | `float` | **必填** | 噪点强度幅度，取值从 `0.0`（无噪点）到 `1.0`（最大值）。 |
| `monochrome` | `bool` | `True` | `True` = 单色亮度噪点（灰阶颗粒）；`False` = 各通道独立的彩色噪点。 |
| `blend_mode` | `str` | `"overlay"` | 噪点与图层的混合模式。可选 `"overlay"`、`"screen"`、`"multiply"`、`"normal"` 之一。 |
| `opacity` | `float` | `1.0` | 整体颗粒透明度，取值从 `0.0`（不可见）到 `1.0`（完全可见）。 |
| `seed` | `int \| None` | `None` | 用于生成确定性输出的随机数种子。`None` 表示每次渲染生成不同随机噪点。 |

`intensity=0.0` 表示不添加任何噪点。

### 示例 { #example_5 }

```python
from quickthumb import Canvas, Grain

canvas = (
    Canvas(1280, 720)
    .background(
        color="#1A1A2E",
        effects=[Grain(intensity=0.12, monochrome=True)],
    )
    .image(
        path="portrait.png",
        position=("70%", "50%"),
        width=400,
        height=500,
        align=("center", "middle"),
        effects=[Grain(intensity=0.08, monochrome=False, blend_mode="overlay", opacity=0.6)],
    )
)
```

!!! note "说明"
    `Grain` 适用于背景、图像、SVG 及视频图层，不支持文本或形状图层。

---

## Duotone { #duotone }

根据亮度将图层重新映射为两种指定颜色：暗部区域映射为 `shadows` 阴影颜色，亮部区域映射为 `highlights` 高光颜色，中间色阶平滑过渡。非常适合将摄影照片快速融入品牌专属配色。

```python
from quickthumb import Duotone

Duotone(shadows="#0A1730", highlights="#7FADFF", opacity=1.0)
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `shadows` | `str` | **必填** | 映射图像最暗区域的颜色。 |
| `highlights` | `str` | **必填** | 映射图像最亮区域的颜色。 |
| `opacity` | `float` | `1.0` | 替换原始色彩的效果强度，取值从 `0.0` 到 `1.0`。 |

---

## InnerShadow { #innershadow }

在图层边缘内部绘制的内阴影，呈现凹陷内嵌的视觉质感。

```python
from quickthumb import InnerShadow

InnerShadow(offset_x=0, offset_y=6, color="#00000080", blur_radius=12)
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `color` | `str` | **必填** | 阴影颜色；支持颜色自带的 Alpha 透明通道。 |
| `offset_x` | `int` | `0` | 水平偏移量（像素）。 |
| `offset_y` | `int` | `0` | 垂直偏移量（像素）。 |
| `blur_radius` | `int` | `0` | 模糊半径（像素）。 |
| `opacity` | `float` | `1.0` | 整体强度，取值从 `0.0` 到 `1.0`。 |

---

## BackdropBlur { #backdropblur }

对图层形状所遮盖的下方已有绘制内容进行模糊处理，产生类似于毛玻璃（磨砂玻璃）的半透明质感。通常与半透明填充色搭配使用，使图层仍呈现为清晰的面板：

```python
from quickthumb import BackdropBlur, Canvas

canvas = (
    Canvas(1280, 720)
    .background(image="photo.jpg", fit="cover")
    .shape(
        shape="rectangle",
        position=(80, 440),
        width=640,
        height=200,
        color="#FFFFFF33",
        border_radius=24,
        effects=[BackdropBlur(radius=24)],
    )
)
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `radius` | `int` | **必填** | 模糊半径（像素）。 |
| `opacity` | `float` | `1.0` | 背景模糊呈现强度，取值从 `0.0` 到 `1.0`。 |
