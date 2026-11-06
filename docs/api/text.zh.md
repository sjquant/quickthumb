---
description: quickthumb 文本图层参考，涵盖富文本片段、字体、对齐、换行、描边、投影和尺寸自适应。
---

# 文本 { #text }

`.text()` 用于添加文本图层。内容可以是普通字符串，也可以是由 `TextPart` 对象组成的列表以实现分段样式定制。

## 方法签名 { #signature }

```python
canvas.text(
    content,
    font=None,
    font_source="auto",
    font_variations=None,
    emoji_style="monochrome",
    size=None,
    color=None,
    fill=None,
    position=None,
    align=None,
    bold=False,
    italic=False,
    weight=None,
    max_width=None,
    max_height=None,
    min_size=1,
    balance_lines=False,
    effects=None,
    line_height=None,
    letter_spacing=None,
    auto_scale=False,
    rotation=0.0,
    opacity=1.0,
)
```

## 参数 { #parameters }

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `content` | `str \| list[TextPart]` | **必填** | 文本内容。普通字符串或用于富文本的 `TextPart` 列表。 |
| `font` | `str \| None` | `None` | 字体家族名称、本地文件路径或远程 Web 字体 URL。 |
| `font_source` | `"auto" \| "system" \| "google"` | `"auto"` | 字体查找源。`"google"` 会下载并缓存指定的 Google Font。 |
| `font_variations` | `dict[str, float] \| None` | `None` | OpenType 可变轴参数，例如 `{"wght": 650}`。 |
| `emoji_style` | `"monochrome" \| "color"` | `"monochrome"` | Emoji 表情呈现偏好。 |
| `size` | `int \| None` | `None` | 字号（像素）。必须为正整数。 |
| `color` | `str \| None` | `None` | 默认文本颜色。十六进制字符串（`"#RRGGBB"` 或 `"#RRGGBBAA"`）。 |
| `fill` | `LinearGradient \| RadialGradient \| TextFillImage \| None` | `None` | 应用于字形文字的渐变或图像填充。设置后在视觉上优先于 `color`。参见[渐变与图像填充](#gradient-and-image-fills)。 |
| `position` | `tuple \| None` | `None` | `(x, y)` 坐标。取值可为整数（像素）或百分比字符串（`"50%"`）。 |
| `align` | `str \| Align \| tuple \| None` | `None` | 文本块对齐方式。参见 [Align 对齐取值](#align-values)。 |
| `bold` | `bool` | `False` | 粗体标志。与 `weight` 互斥。 |
| `italic` | `bool` | `False` | 斜体标志。 |
| `weight` | `int \| str \| None` | `None` | CSS 风格字重（例如 `700`、`900`、`"bold"`）。与 `bold` 互斥。 |
| `max_width` | `int \| str \| None` | `None` | 折行宽度（像素或百分比字符串，如 `"60%"`）。 |
| `max_height` | `int \| str \| None` | `None` | 文本块最大高度（像素或百分比字符串）。 |
| `min_size` | `int` | `1` | 自动缩放自适应时允许的最小字号。 |
| `balance_lines` | `bool` | `False` | 设置 `max_width` 时平衡折行后的各行长度。 |
| `effects` | `list \| None` | `[]` | 效果列表：`Stroke`、`Shadow`、`Glow`、`Background`。 |
| `line_height` | `float \| None` | `None` | 行高倍数。正浮点数。 |
| `letter_spacing` | `int \| None` | `None` | 水平字间距微调（像素）。 |
| `auto_scale` | `bool` | `False` | 自动缩小字号直至文本容纳在 `max_width` 和/或 `max_height` 范围内。 |
| `rotation` | `float` | `0.0` | 旋转角度（度数）。 |
| `opacity` | `float` | `1.0` | 图层不透明度，范围为 `0.0` 至 `1.0`。 |

## Align 对齐取值 {#align-values}

`align` 支持以下任意一种写法：

```python
align="center"              # shorthand
align="top-left"            # compound string
align=("left", "middle")    # (horizontal, vertical) tuple
align=Align.BOTTOM_RIGHT    # enum
```

| 字符串 | 枚举 | 位置说明 |
| --- | --- | --- |
| `"center"` | `Align.CENTER` | 水平与垂直居中 |
| `"left"` | `Align.LEFT` | 左对齐，垂直居中 |
| `"right"` | `Align.RIGHT` | 右对齐，垂直居中 |
| `"top-left"` | `Align.TOP_LEFT` | 左上角 |
| `"top-center"` | `Align.TOP_CENTER` | 顶部边缘水平居中 |
| `"top-right"` | `Align.TOP_RIGHT` | 右上角 |
| `"bottom-left"` | `Align.BOTTOM_LEFT` | 左下角 |
| `"bottom-center"` | `Align.BOTTOM_CENTER` | 底部边缘水平居中 |
| `"bottom-right"` | `Align.BOTTOM_RIGHT` | 右下角 |

使用元组时：水平取值为 `left`、`center`、`right`；垂直取值为 `top`、`middle`、`bottom`。

## 示例 { #examples }

### 普通文本 { #plain-text }

```python
canvas.text(
    content="Hello World",
    size=64,
    color="#FFFFFF",
    align="center",
)
```

### 使用 `TextPart` 定制富文本 { #rich-text-with-textpart }

```python
from quickthumb import Stroke, TextPart

canvas.text(
    content=[
        TextPart(text="5 ", color="#FBBF24", weight=900),
        TextPart(text="WARNING SIGNS", color="#FFFFFF", weight=900),
    ],
    size=72,
    position=("8%", "55%"),
    align=("left", "middle"),
)
```

### 配合效果使用 { #with-effects }

```python
from quickthumb import Background, Glow, Shadow, Stroke

canvas.text(
    content="BREAKING",
    size=96,
    color="#FFFFFF",
    position=("8%", "50%"),
    align=("left", "middle"),
    weight=900,
    max_width="65%",
    effects=[
        Stroke(width=4, color="#000000"),
        Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
        Glow(color="#B8FF00", radius=16, opacity=0.25),
        Background(color="#111827CC", padding=(16, 24), border_radius=14),
    ],
)
```

### 自动缩小自适应 { #auto-scale-to-fit }

```python
canvas.text(
    content="This is a very long title that should fit",
    size=80,
    color="#FFFFFF",
    max_width="70%",
    auto_scale=True,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

### 使用 Web 字体 { #using-a-webfont }

```python
canvas.text(
    content="Custom Font",
    font="https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiA.woff2",
    size=72,
    color="#FFFFFF",
    align="center",
)
```

!!! note "Web 字体 URL"
    当 `font` 为 URL 时，`bold`、`italic` 和 `weight` 将被忽略，因为该 URL 已经精确指向某个具体字体文件。如需不同样式，请分别使用独立的 URL，或者指定字体家族名称配合 `font_source="google"`，让 `weight` 和 `italic` 自动为您选择匹配的文件。

### 渐变与图像填充 {#gradient-and-image-fills}

使用渐变或图像填充文本字形，而非单调纯色。向 `fill` 传入 `LinearGradient`、`RadialGradient` 或 `TextFillImage`：

```python
from quickthumb import Canvas, LinearGradient, RadialGradient, TextFillImage, TextPart

# Linear gradient headline
canvas.text(
    content="GRADIENT",
    size=120,
    fill=LinearGradient(angle=90, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)]),
    position=("50%", "50%"),
    align="center",
)

# Image-filled text
canvas.text(
    content="TEXTURE",
    size=140,
    fill=TextFillImage(path="fire_texture.jpg", fit="cover"),
    position=("50%", "50%"),
    align="center",
)

# Per-segment fills using TextPart
canvas.text(
    content=[
        TextPart(
            text="HOT ",
            fill=LinearGradient(angle=45, stops=[("#FF4500", 0.0), ("#FFD700", 1.0)]),
            weight=900,
        ),
        TextPart(
            text="COLD",
            fill=LinearGradient(angle=45, stops=[("#00BFFF", 0.0), ("#8A2BE2", 1.0)]),
            weight=900,
        ),
    ],
    size=110,
    position=("50%", "50%"),
    align="center",
)
```

在 `TextPart` 上设置的 `fill` 仅覆盖该片段自身的图层级 `fill`。`fill` 和 `color` 相互独立；二者同时设置时，`fill` 在视觉呈现上具有更高优先级。图像填充配置选项请参见 [TextFillImage](enums.md#textfillimage)。

## TextPart { #textpart }

`TextPart` 用于在同一文本图层内为不同文本片段定义独立样式。

```python
from quickthumb import Stroke, TextPart

TextPart(
    text="HOT",
    color="#FF3B30",
    fill=None,
    size=56,
    font="Impact",
    font_source=None,
    font_variations=None,
    emoji_style=None,
    weight=900,
    italic=False,
    line_height=None,
    letter_spacing=0,
    effects=[Stroke(width=3, color="#000000")],
)
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `text` | `str` | **必填** | 文本片段。不可为空。 |
| `color` | `str \| None` | `None` | 当前片段的覆盖颜色（十六进制）。 |
| `fill` | `LinearGradient \| RadialGradient \| TextFillImage \| None` | `None` | 当前片段的渐变或图像填充。仅覆盖当前片段的图层级 `fill`。 |
| `size` | `int \| None` | `None` | 当前片段的字号覆盖值。 |
| `font` | `str \| None` | `None` | 当前片段的字体覆盖值。 |
| `font_source` | `"auto" \| "system" \| "google" \| None` | `None` | 字体源覆盖值。`None` 表示继承图层设置；显式设置将覆盖图层。 |
| `font_variations` | `dict[str, float] \| None` | `None` | 可变轴参数覆盖。`None` 表示继承图层；`{}` 会显式清除继承的轴参数。 |
| `emoji_style` | `"monochrome" \| "color" \| None` | `None` | Emoji 风格覆盖。`None` 表示继承；`"monochrome"` 会显式覆盖。 |
| `bold` | `bool \| None` | `None` | 粗体覆盖。与 `weight` 互斥。 |
| `italic` | `bool \| None` | `None` | 斜体覆盖。 |
| `weight` | `int \| str \| None` | `None` | 字重覆盖。与 `bold` 互斥。 |
| `line_height` | `float \| None` | `None` | 行高倍数覆盖。 |
| `letter_spacing` | `int \| None` | `None` | 字间距覆盖。 |
| `effects` | `list[TextEffect]` | `[]` | 片段级效果：`Stroke`、`Shadow`、`Glow`、`Background`。 |

## 文本动画 { #text-animations }

使用 `RangeSelector` 可以实现按词或按字符的文字动画：

```python
from quickthumb import AnimationSpec, Canvas, KeyframeSpec, PositionTrack, RangeSelector, TimingSpec

canvas = Canvas(800, 400).text(
    "Words appear one by one",
    size=48,
    color="#FFFFFF",
    position=(50, 150),
    animation=AnimationSpec.timeline(
        PositionTrack(keyframes=[
            KeyframeSpec(time=0, value=(0, 20)),
            KeyframeSpec(time=0.4, value=(0, 0)),
        ]),
        selector=RangeSelector(
            target="words",  # "words", "lines", or "characters"
            offset=[KeyframeSpec(time=0, value=-100), KeyframeSpec(time=2, value=100)],
        ),
        timing=TimingSpec(duration=2),
    ),
)
```

有关选择器形态、时序及颜色过渡的详细信息，请参见[文本范围选择器](video.md#text-range-selectors)。

## 校验规则 { #validation-rules }

- `content` 为必填项，且不能是空列表。
- `TextPart.text` 不能为空字符串。
- `TextLayer` 与 `TextPart` 中 `weight` 和 `bold=True` 均互斥。
- `auto_scale=True` 要求必须设置 `max_width` 或 `max_height`。
- `max_width` 必须为正整数或类似于 `"60%"` 的正百分比字符串。
- `position` 中的百分比字符串必须符合 `-?N%` 模式（负百分比有效）。
- `fill` 和 `color` 为独立字段；同时设置时 `fill` 具有更高视觉优先级。
- `TextFillImage.path` 支持本地文件路径和远程 URL；本地文件不存在时会在渲染时抛出 `FileNotFoundError`。
