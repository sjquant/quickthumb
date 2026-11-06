---
description: quickthumb 的工作原理：有序图层组成的画布、位置与对齐、效果、富文本、自动布局、JSON 规范与校验。
---

# 核心概念 { #core-concepts }

## 画布即图层列表 { #a-canvas-is-a-list-of-layers }

`Canvas` 拥有指定尺寸和一组有序图层列表。每个图层方法都会追加一个图层并返回画布实例，因此支持链式调用：

```python
from quickthumb import Canvas

canvas = (
    Canvas(1280, 720)
    .background(color="#0F172A")
    .text(content="Hello", size=64, color="#FFFFFF", align="center")
    .outline(width=8, color="#22D3EE")
)
canvas.render("hello.png")
```

图层严格按照添加顺序依次绘制。先添加的图层位于底层，最后添加的图层位于顶层。因此构建图像的过程就像作画：先画背景，最后绘制细节。

## 图层类型 { #layer-types }

| 方法 | 添加内容 | 参考文档 |
| --- | --- | --- |
| `.background()` | 全画布纯色、渐变或图片 | [背景](api/background.md) |
| `.text()` | 普通文本或带样式的 `TextPart` 列表 | [文字](api/text.md) |
| `.image()` | 指定位置的图片，支持可选的抠图去背景 | [图像](api/image.md) |
| `.shape()` | 矩形、椭圆、胶囊形、三角形、星形或多边形 | [形状](api/shape.md) |
| `.svg()` | SVG 文件，如图标或徽标（需要 `svg` 额外依赖） | [SVG](api/svg.md) |
| `.video()` | 视频片段，用于动效导出 | [视频](api/video.md) |
| `.chart()`, `.qr_code()` | 柱状图、折线图或二维码 | [数据可视化](api/data-visualizations.md) |
| `.counter()` | 从一个数值过渡到另一个数值的动态计数器 | [Canvas](api/canvas.md#animated-counters) |
| `.group()` | 自动排列子图层的行或列容器 | [分组（自动布局）](api/group.md) |
| `.outline()` | 围绕画布边缘的描边线框 | [描边](api/outline.md) |
| `.custom(fn)` | 自定义绘图函数，可直接在 Pillow 图像上绘制 | [Canvas](api/canvas.md) |

## 位置与对齐 { #position-and-alignment }

`position` 是一个 `(x, y)` 坐标对。每个坐标值可以是像素数或画布百分比，两者支持混用：

```python
canvas.shape(shape="rectangle", position=(64, 64), width=200, height=80, color="#CC0000")
canvas.text(content="Hello", size=72, color="#FFFFFF", position=("8%", 360))
```

`align` 决定了图层的哪个基准点落在该坐标位置上。默认值为左上角。设置 `align=("center", "middle")` 会将图层中心对齐到该坐标；设置 `align=("right", "bottom")` 并配合 `position=(1280, 720)`，则无论图层自身尺寸多大，都能将其固定在 1280×720 画布的右下角。

`align` 支持多种写法：

```python
align=("center", "middle")      # (horizontal, vertical)
align="center"                  # same as ("center", "middle")
align="bottom-right"
align=Align.BOTTOM_RIGHT
```

水平方向的有效值为 `left`、`center` 和 `right`；垂直方向为 `top`、`middle` 和 `bottom`。如果文本图层设置了 `align` 但未指定 `position`，画布会根据对齐规则自动定位，例如 `align="center"` 会将其水平居中。

## 效果 { #effects }

效果（Effects）用于改变单个图层的绘制外观，以列表形式传入：

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

并非所有效果都适用于所有图层：

| 图层 | 支持的效果 |
| --- | --- |
| Background（背景） | `Filter`, `Grain` |
| Text（文字） | `Stroke`, `Shadow`, `Glow`, `Background`（文字背景框） |
| Shape（形状） | `Stroke`, `Shadow`, `Glow`, `InnerShadow`, `BackdropBlur` |
| Image, SVG, Video（图像、SVG、视频） | `Stroke`, `Shadow`, `Glow`, `Filter`, `Grain`, `Duotone`, `InnerShadow`, `BackdropBlur` |

为图层传入不支持的效果会触发 `ValidationError`。各效果的完整参数请参阅[效果参考](api/effects.md)。

## 富文本 { #rich-text }

当文本样式完全统一时，传入普通字符串即可。如果需要为不同文字片段应用不同样式，可传入 `TextPart` 列表：

```python
from quickthumb import TextPart

canvas.text(
    content=[
        TextPart(text="5 ", color="#FBBF24"),
        TextPart(text="WAYS TO WIN", color="#FFFFFF"),
    ],
    size=80,
    weight=900,
    position=("8%", "55%"),
    align=("left", "middle"),
)
```

图层级别的设置（本例中的 `size` 和 `weight`）会应用于每个文字片段，除非片段自身进行了单独覆盖。`TextPart` 支持单独覆盖 `color`、`size`、`font`、`weight`、`bold`、`italic`、`letter_spacing`、`line_height` 以及 `effects`。

## 渐变、混合模式与填充方式 { #gradients-blend-modes-and-fit }

背景除了纯色和图片外，还支持传入 `gradient` 渐变：

```python
from quickthumb import LinearGradient, RadialGradient

canvas.background(gradient=LinearGradient(angle=135, stops=[("#FF5733", 0.0), ("#3333FF", 1.0)]))
canvas.background(gradient=RadialGradient(center=(0.5, 0.5), stops=[("#FF5733", 0.0), ("#3333FF", 1.0)]))
```

渐变色标（stops）中的颜色支持 Alpha 通道（例如 `"#00000080"`），常用于压暗文字下方的照片区域。

背景或图像图层的 `blend_mode` 用于控制其与下层内容的混合模式：`normal`、`multiply`、`screen`、`overlay`、`darken` 或 `lighten`。

`fit` 决定了图片如何填充其边界框：`cover` 会填满整个区域并裁剪多余部分（背景图层的默认值），`contain` 会完整容纳整张图片，`fill` 则会拉伸填充。

## 自动布局 { #auto-layout }

手动指定绝对位置的文字，在文案变长时容易产生重叠或溢出。`group` 容器会自动测量其子图层，并将它们排列为行或列；你只需定位该容器一次，容器就会自动为其子图层计算排版：

```python
canvas.group(
    children=[
        {"type": "shape", "shape": "pill", "width": 120, "height": 36, "color": "#E94560"},
        {"type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900},
        {"type": "text", "content": "Longer copy pushes the rest down", "size": 40, "color": "#A2A8D3"},
    ],
    direction="column",
    gap=24,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

子图层无需设置 `position`，且分组支持嵌套。详情参阅[分组（自动布局）](api/group.md)。

## JSON 规范 { #json-specs }

上述所有内容均可使用 JSON 编写来代替 Python 代码，画布支持双向转换：

```python
spec = canvas.to_json()
same_canvas = Canvas.from_json(spec)
```

唯一的例外是 `.custom(fn)`，因为 Python 函数无法序列化为 JSON。

JSON 规范还支持在 `theme` 块中统一定义颜色和尺寸，并通过 `$theme.<path>` 引用：

```json
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "theme": { "colors": { "primary": "#B8FF00" }, "sizes": { "title": 96 } },
  "layers": [
    { "type": "text", "content": "Hello", "size": "$theme.sizes.title", "color": "$theme.colors.primary" }
  ]
}
```

详情参阅 [JSON Schema 与 AI 工作流](json-schema.md)。

## 路径动效 { #path-motion }

`Canvas.path()` 支持 SVG 路径数据、填充（包含渐变）以及虚线描边。路径具有固定的 `width`/`height` 视口，不仅用于裁切局部绘制，还在旋转和缩放期间定义其归一化的 `anchor` 锚点：

```python
from quickthumb import AnimationSpec, Canvas, KeyframeSpec, ScaleTrack, TimingSpec

canvas = Canvas(320, 240).path(
    "M2 20C2 2 38 2 38 20C38 38 2 38 2 20Z", (100, 80), 40, 40,
    "#38B6A080", anchor=(0.5, 0.5),
    animation=AnimationSpec.timeline(
        ScaleTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=4)]),
        timing=TimingSpec(duration=1), easing="linear",
    ),
)
frame = canvas.render_frame(0.75)
```

使用轨道时间轴为路径制作动效。不同导出格式对路径动效的支持程度不同；路径暂不支持预设动效、错峰（stagger）、作为 Group 子元素以及变换父级关联。动画和导出详情请参阅 [Path API](api/path.md)。

## 错误与检查 { #errors-and-checks }

添加图层时会立即校验参数，此时尚未开始绘制：

```python
from quickthumb import ValidationError

try:
    canvas.text(content="Hello", size=64, color="#FFF")
except ValidationError as error:
    print(error)  # /color: invalid hex color: #FFF
```

仅在绘制期间暴露的问题（例如网络下载失败）会抛出 `RenderingError`；本地文件不存在则会抛出 `MissingAssetError`。所有错误均包含结构化的 `details` 属性；详情参阅[结构化错误](errors.md)。

画布即便参数合法，也可能在视觉上存在排版问题。`canvas.diagnose()` 无需实际渲染文件即可检测文本过小、文字溢出画布、对比度不足、图层被完全遮挡等常见缺陷。详情参阅[诊断与 CLI](diagnostics.md)。
