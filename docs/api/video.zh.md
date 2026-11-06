---
description: quickthumb 视频图层参考，涵盖片段修剪、适配模式、播放速度、字幕、色彩校正、遮罩与动效。
---

# 视频 { #video }

`.video()` 用于在画布中添加视频片段。其行为与普通视觉图层完全一致：你可以修剪、缩放、循环、重新定位、设置圆角、调色、遮罩，并在时间轴上编排关键帧动画。

视频图层在动画导出（GIF、MP4、WebM、MOV）及 `render_frame(...)` 中以原生形式渲染。在静态文档目标（PPTX、PDF、SVG、HTML）中，片段将渲染为静态静止画面。

## 方法签名 { #signature }

```python
canvas.video(
    source,
    position,
    width,
    height,
    fit="contain",
    trim_start=0.0,
    trim_end=None,
    start=0.0,
    duration=None,
    speed=1.0,
    volume=1.0,
    captions=None,
    border_radius=0,
    opacity=1.0,
    rotation=0.0,
    align=None,
    blend_mode=None,
    effects=None,
    clip=None,
    mask=None,
    animation=None,
)
```

## 参数 { #parameters }

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `source` | `str` | **必填** | 视频文件路径。 |
| `position` | `tuple` | **必填** | 像素或百分比字符串（`"50%"`）形式的 `(x, y)` 坐标。 |
| `width` | `int` | **必填** | 图层宽度（像素）。 |
| `height` | `int` | **必填** | 图层高度（像素）。 |
| `fit` | `str \| FitMode` | `"contain"` | 视频在图层框内的缩放适配方式：`"contain"`、`"cover"` 或 `"fill"`。参见 [FitMode](enums.md#fitmode)。 |
| `trim_start` | `float` | `0.0` | 源视频文件的播放起始时间（秒）。 |
| `trim_end` | `float \| None` | `None` | 源视频文件的播放结束时间。默认为片段末尾。 |
| `start` | `float` | `0.0` | 片段在时间轴上开始播放的时刻（秒）。 |
| `duration` | `float \| None` | `None` | 片段在场景中的持续呈现时长。 |
| `speed` | `float` | `1.0` | 播放速度倍率（例如 `0.5` 为半速，`2.0` 为两倍速）。 |
| `volume` | `float` | `1.0` | 片段音频音量（适用于 MP4/WebM/MOV）。GIF 导出始终无声。 |
| `captions` | `list \| None` | `[]` | 硬字幕叠加层列表，直接烧录在各帧中。 |
| `border_radius` | `int` | `0` | 圆角半径（像素）。 |
| `opacity` | `float` | `1.0` | 图层不透明度，范围为 `0.0` 至 `1.0`。 |
| `rotation` | `float` | `0.0` | 旋转角度（度数）。 |
| `align` | `str \| Align \| tuple \| None` | `None` | `position` 的锚点基准。参见 [Align](enums.md#align)。 |
| `blend_mode` | `str \| BlendMode \| None` | `None` | 图像合成混合模式。 |
| `effects` | `list \| None` | `[]` | 视觉滤镜效果：`Filter`、`Duotone`、`Grain`、`Glow`、`Shadow`、`Stroke`、`InnerShadow`。 |
| `clip` | `LayerClip \| None` | `None` | 将图层裁剪至几何边界框内。 |
| `mask` | `LayerMask \| None` | `None` | 使用形状或路径对图层进行遮罩。 |
| `animation` | `Animation \| AnimationSpec \| list \| None` | `None` | 入场/出场预设或自定义关键帧动画。 |

## 示例 { #examples }

### 片段修剪与调色 { #trimming-and-color-grading }

将片段裁剪为 6 秒窗口，转换为黑白效果并添加圆角：

```python
from quickthumb import Canvas
from quickthumb.models import Filter

canvas = Canvas(1280, 720).video(
    "clip.mp4",
    position=(64, 64),
    width=1152,
    height=592,
    fit="cover",
    trim_start=1.0,
    trim_end=7.0,
    duration=6.0,
    border_radius=16,
    effects=[Filter(saturation=0.0, contrast=1.15)],
)
```

### 位置动画 { #animating-position }

使视频在播放的同时水平横跨场景滑动：

```python
from quickthumb import AnimationSpec, Canvas, KeyframeSpec, PositionTrack, TimingSpec

canvas = Canvas(1280, 720).video(
    "clip.mp4",
    position=(0, 200),
    width=480,
    height=270,
    fit="cover",
    duration=4.0,
    animation=AnimationSpec.timeline(
        PositionTrack(
            keyframes=[
                KeyframeSpec(time=0.0, value=(0, 0)),
                KeyframeSpec(time=4.0, value=(800, 0)),
            ]
        ),
        timing=TimingSpec(start=0.0, duration=4.0),
        easing="ease_in_out",
    ),
)
```

### 弹簧缓动 { #spring-easing }

使用 `SpringEasing` 添加逼真自然的物理回弹动效：

```python
from quickthumb import AnimationSpec, KeyframeSpec, PositionTrack, SpringEasing

motion = AnimationSpec.timeline(
    PositionTrack(keyframes=[
        KeyframeSpec(time=0, value=(0, 0)),
        KeyframeSpec(time=1, value=(180, 0)),
    ]),
    easing=SpringEasing(stiffness=100, damping=10, mass=1),
)
```

### Wiggle 抖动修改器 { #wiggle-track-modifiers }

在任意轨道上附加 `Wiggle(frequency=2, amplitude=12, seed=42)` 以引入自然且确定性的随机微颤：

```python
from quickthumb import AnimationSpec, KeyframeSpec, PositionTrack, TimingSpec, Wiggle

motion = AnimationSpec.timeline(
    PositionTrack(
        keyframes=[KeyframeSpec(time=0, value=(0, 0))],
        wiggle=Wiggle(frequency=2, amplitude=12, seed=42),
    ),
    timing=TimingSpec(duration=2),
)
```

## 透明视频叠加层 { #transparent-video-overlays }

导出带有透明背景的视频（非常适合底部人名条、动态贴纸或游戏画面悬浮叠加）：

- **WebM（带 Alpha 的 VP9）**：`VideoOptions(transparent=True)`
- **ProRes 4444 MOV**：`canvas.export("overlay.mov", animation=VideoOptions(transparent=True))`

```python
from quickthumb import Canvas, VideoOptions

canvas = Canvas(1280, 720).shape("pill", (100, 600), 400, 80, "#42CEB7")
canvas.export("lower_third.webm", animation=VideoOptions(transparent=True))
```

详情请参见[透明视频导出](../reference/export-transparency.md)。

## 说明 { #notes }

- **源视频时长**：若场景总时长长于源片段，可将 `speed` 设为小于 `1.0` 以实现平滑慢动作拉伸播放。
- **字幕**：字幕渲染在构图所有图层之上，以确保清晰可读。
- **诊断**：`canvas.diagnose()` 会自动检查字幕位置、安全边距以及阅读速度。

---

# 高级动效与图层合成 { #advanced-motion-compositing }

以下章节介绍了所有视觉图层（文本、形状、图像、路径和视频）通用的高级动画与合成功能。

## 曲线运动路径 { #curved-motion-paths }

使用带有切线手柄的 `PositionKeyframeSpec` 创建平滑贝塞尔曲线路径而非生硬直线：

```python
from quickthumb import AnimationSpec, Canvas, PositionKeyframeSpec, PositionTrack, TimingSpec

canvas = Canvas(640, 360).shape(
    "pill", (60, 230), 48, 24, "#42CEB7",
    animation=AnimationSpec.timeline(
        PositionTrack(
            keyframes=[
                PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(120, -200)),
                PositionKeyframeSpec(time=4, value=(480, 0), in_tangent=(-120, -200)),
            ],
            auto_orient=True,  # Rotate layer to follow the path tangent
        ),
        timing=TimingSpec(start=0, duration=4),
        easing="linear",
    ),
)
```

### 控制手柄与速度 { #handles-and-speed }

- `out_tangent=(dx, dy)` 决定离开关键帧时的曲线走向。
- `in_tangent=(dx, dy)` 决定进入关键帧时的曲线走向。
- 配合 `easing="linear"`，图层将沿曲线匀速运动。

### 沿切线自动定向 { #following-the-tangent }

当设置 `auto_orient=True` 时，图层会自动旋转以契合当前的移动方向（向右为 `0°`，顺时针为正）。

### 导出支持 { #export-support }

光栅动画（GIF、MP4、WebM）和 HTML 支持曲线运动路径。文档导出格式（PPTX、PDF）仅展示初始帧。

## 变换锚点与独立轴缩放 { #transform-anchors-and-independent-scale }

默认情况下，图层以中心点为基准进行缩放与旋转（`anchor=(0.5, 0.5)`）。自定义 `anchor=(x, y)` 可设置不同的旋转与缩放枢轴点：

- `(0, 0)`：左上角
- `(0.5, 0.5)`：中心（默认值）
- `(1, 1)`：右下角

```python
from quickthumb import (
    AnimationSpec, Canvas, KeyframeSpec, RotationTrack, ScaleXTrack, ScaleYTrack, TimingSpec,
)

canvas = Canvas(320, 240).shape(
    "rectangle", (100, 100), 80, 40, "#42CEB7",
    anchor=(0, 1),  # Pivot around bottom-left corner
    animation=AnimationSpec.timeline(
        ScaleXTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=1.5)]),
        ScaleYTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=0.6)]),
        RotationTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=2, value=30)]),
        timing=TimingSpec(duration=2),
    ),
)
```

### 导出支持 { #export-support_1 }

自定义锚点与独立轴缩放（`ScaleXTrack`、`ScaleYTrack`）在光栅逐帧、GIF、MP4、WebM 及现代 HTML 演示文稿中均受支持。

## 文本与形状颜色动画 { #animated-text-and-shape-colors }

使用 `ColorTrack` 随时间平滑改变填充色或文本颜色：

```python
from quickthumb import AnimationSpec, Canvas, ColorTrack, KeyframeSpec, TimingSpec

canvas = Canvas(640, 360).text(
    "Color in motion", position=(40, 40), size=48, color="#FF0000",
    animation=AnimationSpec.timeline(
        ColorTrack(keyframes=[
            KeyframeSpec(time=0, value="#FF0000"),
            KeyframeSpec(time=2, value="#0055FF"),
        ]),
        timing=TimingSpec(start=0, duration=2),
    ),
)
```

颜色在感知均匀的 Oklab 颜色空间中平滑插值，避免了过渡期颜色浑浊暗淡。

## 实时时间轴预览 { #live-timeline-preview }

无需等待视频编码，即可直接在浏览器中交互式拖拽预览动效：

```bash
quickthumb serve scene.py --timeline
```

此命令将在 `http://localhost:3030/timeline` 启动带有帧进度条的实时预览页面，文件保存时自动即时热重载。

## 父级绑定与 Null 控制器 { #parent-links-and-null-controllers }

使用 `parent="parent-layer-id"` 建立图层层级链接。当父图层移动、旋转或缩放时，子图层将随之一同变换：

```python
from quickthumb import Canvas

scene = (
    Canvas(320, 240)
    .null(position=(100, 50), id="controller")  # Invisible point controller
    .shape("rectangle", (10, 20), 40, 20, "#42CEB7", parent="controller")
)
```

### 几何变换契约 { #geometry-contract }

- 子图层位置相对于父图层的坐标空间计算。
- 子图层继承父图层的运动变换（位置、旋转、缩放）。
- 父图层的样式（不透明度、效果、遮罩）**不会**被子图层继承，从而保持子图层样式的独立性。

### 导出适配器与支持边界 { #current-adapters-and-boundaries }

父级绑定在光栅图像、GIF、MP4 和 WebM 导出中得到完整支持。在文档格式（PPTX、PDF、SVG）中，带有父级的编组导出为静态渲染切片。

## 文本范围选择器 { #text-range-selectors }

使用 `RangeSelector` 可以按词、按行或按字符逐步驱动文本动画：

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

### 字符归属 { #character-ownership }

当 `target="characters"` 时，每个字形都会获得独立的动画相位。空格和标点符号均按照精确的字体度量得以保留。

## 轨道遮罩（Track Matte） { #track-mattes }

使用 `mask=TrackMatte(layer="source-id")` 将另一个图层用作 Alpha 遮罩或亮度遮罩：

```python
from quickthumb import Canvas, TrackMatte

canvas = (
    Canvas(640, 360)
    .shape("ellipse", (120, 80), 200, 200, color="#FFFFFF", id="hole")
    .image("photo.jpg", position=(0, 0), width=640, height=360, mask=TrackMatte(layer="hole"))
)
```

- `mode="alpha"`：基于源图层的透明通道进行遮罩。
- `mode="luma"`：基于源图层的明暗亮度进行遮罩。
- `invert=True`：反转镂空裁切区域。

### 动态形状遮罩几何变换 { #animated-shape-mask-geometry }

使用 `MaskPositionTrack`、`MaskSizeTrack` 或 `MaskFeatherTrack` 可以动态改变遮罩的位置、大小及羽化半径。

### 原生 HTML 形状遮罩 { #native-html-shape-masks }

矩形、胶囊形和椭圆遮罩在 HTML 幻灯片中导出为纯净的 CSS 裁剪路径（clipping path）。

### 图层专属路径遮罩 { #owner-attached-path-masks }

使用 `LayerMask(shape="path", d="M0 0 H40 V40 H0 Z")` 可将自定义 SVG 路径遮罩直接绑定到任意图层上。

### 路径轮廓动态遮罩 { #path-shaped-mattes }

将 `Canvas.path()` 图层作为动态位移轨道遮罩进行引用，可实现高度定制化的动态镂空遮罩动效。
