---
description: quickthumb 的 GIF、视频与幻灯片旁白导出功能参考。
---

# GIF、视频与旁白 { #gif-video-and-narration }

[导出参考](../exports.md) · [输出格式选择指南](../output-guide.md)

## 动画 GIF 与视频 { #animated-gif-video }

有关规范采样与编码帧数差异、幻灯片/旁白时钟、字幕及交互式 HTML 行为的说明，请参见[动画时序](../timing.md)。

动画导出使用与 PNG 输出相同的像素流水线，将每图层的 `animation` 动效和 Deck 幻灯片 `transition` 转场渲染为真实的光栅帧序列。Canvas 与 Deck 的 GIF/MP4/WebM/MOV 导出均会播放该动画时间轴，即便未显式传递选项的文件导出也是如此。

```python
from quickthumb import AudioTrack, Canvas, Deck, Fade, GifOptions, VideoOptions
from quickthumb.transitions import Push

canvas = Canvas(1280, 720).background(color="#101820").text(
    content="Hello", position=("50%", "50%"), size=96, color="#FFFFFF",
    animation=Fade(duration=0.6),
)
canvas.render("hello.gif")                     # defaults: 20 fps, 3s hold
canvas.render(
    "preview.gif",
    animation=GifOptions(fps=8, max_size=(540, 960), colors=128),
)
mp4 = canvas.to_mp4(fps=30, hold=2.0)          # tunable variants return bytes

other = Canvas(1280, 720).background(color="#204060")
deck = Deck(1280, 720).slide(canvas).slide(other, transition=Push(direction="left"))
gif = deck.to_gif(fps=20, hold=3.0, loop=0)
webm = deck.to_webm(fps=30, hold=3.0)
```

每个动效均接收 `duration`、`delay` 和 `trigger`，以及两项时序控制参数：

- `easing`：从通用缓动函数词汇表（`"linear"`、`"ease"`、`"ease_out_cubic"`、`"ease_out_back"` 等）中选择入场曲线。传统动效默认为 `"ease"`；规范预设会自动解析其缓动曲线与观感，其余情况默认为 `"linear"`。用于展示已逝时间的进度条需要使用 `"linear"` 以精确体现其进度。HTML 导出将命名缓动曲线与自定义三次贝塞尔曲线函数传递给 CSS。命名多项式曲线采用现有的 CSS 三次贝塞尔曲线近似实现：曲线形态高度相近，但中间像素状态无需与规范采样完全绝对一致。
- `start`：将动效锚定在幻灯片的绝对时间点，而非顺延挂载在前序动效之后。锚定动效不会挪动相对挂载动效所依赖的时间游标，因此两种风格可以自由混用。

```python
from quickthumb import Wipe

canvas.shape(
    shape="rectangle", position=(0, 700), width=1280, height=6, color="#E8A552",
    animation=Wipe(direction="right", duration=6.0, easing="linear"),
)
canvas.shape(
    shape="rectangle", position=(80, 180), width=180, height=14, color="#E8A552",
    animation=Wipe(direction="right", duration=2.4, start=0.9, easing="linear"),
)
```

带有 `stagger` 交错延迟的规范 `AnimationSpec` 可使每个目标按照独立节奏依次运动。行目标（lines）直接从图层绘制完成的渲染结果中切片提取，因此每一行都保持最初绘制时的排版，并在屏幕外静候出场：

```python
from quickthumb import AnimationSpec

canvas.text(
    content="가로로 한 번.\n세로로 한 번.\n미리보기로 또 한 번.",
    position=(80, 150), size=38, color="#F2EFE9", line_height=1.5,
    animation=AnimationSpec.rise(
        from_="bottom", distance=26, duration=0.45, stagger=0.32, target="lines"
    ),
)
```

若行间距过于紧凑以至于彼此触碰，则无法在渲染切片中有效区分；单词（words）与字符（characters）目标同样没有可分离的独立色带，此时会自动降级为将整个图层作为一个整体进行运动。

静态文本与顶层编组也可以作为显式父级链条中的叶子节点参与 stagger 交错动画。分离后的切片条带继承祖先节点的完整仿射变换，并保留各自的锚点与外观动画轨道。该机制复用了前述部分条带适配器与整体块级降级回退；交错图层本身不能作为其他图层的父级。计数器加交错动画以及动态数据源仍受到严格保护。详情请参见[父级变换支持边界](../api/video.md#current-adapters-and-boundaries)及可运行的 `examples/parent_stagger.py` 示例。

`Canvas.render()` 与 `Deck.render()` 针对动画文件输出接收专门的格式选项对象。GIF 使用 `GifOptions`（`fps`、`hold`、`matte`、`loop`、`max_size=(width, height)` 和 `colors`）；MP4/WebM/MOV 使用 `VideoOptions`（`fps`、`hold`、`matte`、`soundtrack=AudioTrack(...)`、`loop_audio` 以及 WebM/MOV 的 `transparent=True`）。二者均支持 `workers=1` 与 `render_quality="standard"`。视频导出拒绝 GIF 尺寸与调色板控制参数；GIF 导出拒绝视频专用选项。通用的 `render(..., quality=...)` 选项严格保留给 JPEG 和 WebP 光栅输出使用。

两个选项模型均使用 `hold=3.0` 作为静止状态保持时间，与 Canvas 和 Deck 字节方法中的 `hold` 保持一致。其值必须为有限非负数；布尔值与字符串会被拒绝。序列化选项中会省略默认的 hold 值并在加载时恢复；显式指定的零值将予以保留。旁白时长与显式指定的 Deck 幻灯片持续时间仍用于决定视频排期，而 Deck GIF 依然忽略这些按页设定的时长。Deck 动画视频保留原有限制：当任意幻灯片既无旁白又未显式指定正数时长时，`hold=0` 将报错失败，因为其音频调度需要正数时长的静音底轨。对于此类幻灯片，请指定正数的 hold 值。Canvas、Deck GIF 以及无声图像序列继续允许将 hold 设为 0。

字节导出方法接收相同的标量命名关键字参数：Canvas GIF/MP4/WebM/MOV 和 Deck GIF/动画 MP4/WebM/MOV 支持 `workers=1` 与 `render_quality="standard"`，GIF 还支持 `max_size=None` 与 `colors=None`。这些方法直接使用 `hold` 参数，不接收选项对象。旁白视频复用与其他视频输出相同的 Deck MP4 时间轴。

文件执行在检查导出策略之前确定目标格式。Canvas 与 Deck MP4 始终播放动画时间轴，未提供选项时使用默认的 `VideoOptions()`。未实际执行的创作时 Morph 变形转场在导出静态文件或开启减弱动态效果时不会产生降级错误或凭据诊断。减弱动效仍会保留编码器的 hold 保持时间以及幻灯片之间的默认转场。有关采样率、编码视觉帧数与持续时长的详细信息，请参见[动画时序](../timing.md)。

`ExportResult.pixel_metrics.width` 与 `height` 依然表示规范第一张画布的光栅像素尺寸。它们不反映 GIF 缩放或 MP4/WebM 的画面裁剪。图像序列导出结果会在独立字段中报告其完整输出尺寸。

`validate_export(target)` 是针对声明的动效能力进行的查询，独立于具体的文件执行选项。例如，即使启用了减弱动态效果策略，`validate_export("mp4")` 仍会查询动画视频能力。具体的 `svg` 与 `pdf` 查询使用现有的 `raster` 系列标签描述其静态文档降级方案。目标参数大小写不敏感；`jpg`、`jpeg`、`webp`、`png`、`gif`、`mp4`、`webm`、`mov`、`htm` 和 `image_sequence` 均被视作对应系列的格式别名。GIF 查询归属于 `raster`，而出于兼容性考虑，GIF 的 `ExportResult.target` 仍报告为 `video`。

## 带旁白的 Deck 视频 { #narrated-deck-video }

可将 Deck 导出为每页均带有配音解说的视频：

- 向 `Deck.slide()` 传递 `audio=`。若未提供 `duration=`，系统将通过 `ffprobe` 自动测量旁白音频的时长。显式传递 `duration=` 会裁剪音频或用静音补齐。未提供音频的幻灯片将静音保持 `hold` 时长（默认 3 秒）。
- `deck.export("deck.mp4")` 与 `deck.render("deck.mp4")` 默认会在播放图层动画与转场的同时播放旁白语音。`deck.to_mp4()`、`deck.to_webm()` 和 `deck.to_mov()` 返回编码后的动画视频二进制字节。
- 如需制作带有旁白的静止画面幻灯片，请构建静态 Canvas 并显式设置 `Cut()` 硬切转场。输出格式为 H.264/yuv420p，有音频时音轨采用 AAC 编码。省略转场将使用默认淡入淡出，而非硬切。`reduced_motion=True` 同样会选择默认转场，并非静止幻灯片专用导出模式。在常规 MP4 路径中，已存在的图层动画依然会正常播放。
- 在 `deck.export()` 或 `deck.render()` 中通过 `animation=VideoOptions(soundtrack=AudioTrack(path="music.mp3", volume=0.16, loop=True))` 添加背景音乐。Quickthumb 会自动将其与各页旁白语音进行混音；调用方无需自行提前预混音频。

```python
from quickthumb import Canvas, Deck, VideoOptions
from quickthumb.transitions import Cut

deck = Deck(640, 360).transition(Cut())
deck.slide(Canvas(640, 360).background(color="#123456"),
           audio="voice.wav", duration=2.5)
deck.slide(Canvas(640, 360).background(color="#456789"), duration=1.0)
result = deck.export("narrated.mp4", animation=VideoOptions(fps=30))
mp4_bytes = deck.to_mp4(fps=30)
```

## 动画时序 { #timing }

除无法手动点击推进外，视频与 GIF 遵循与 HTML 幻灯片放映完全一致的时序逻辑：`on_click` 动效会自动像 `after_previous` 一样依次顺畅播放（PowerPoint 自带的视频导出功能也是同样逻辑）。每张幻灯片在前一张幻灯片的最后一帧之上播放转场，运行其自身包含的动画（与 HTML 一致，转场开始时同步触发动画），随后在其定型静止状态保持一段时间（若转场设置了 `advance_after` 则以此为准，否则保持 `hold` 时长）。在带有旁白的 MP4/WebM/MOV 输出中，推断或显式指定的旁白时长（或无声幻灯片的默认时长）长于 `advance_after` 时会相应延长画面的视觉停留时间。没有设置转场的幻灯片会以 0.5 秒淡入过渡（没有转场的第 0 页幻灯片立即开播）；为第 0 页设置转场可以使其从底色渐入，这也有助于让循环播放的 GIF 在首尾循环处自然平滑过渡。

GIF 由 Pillow 直接按每帧独立时长进行编码，无需任何额外依赖。MP4（H.264）、WebM（VP9）与 MOV（ProRes 4444）则要求系统 `PATH` 中包含 `ffmpeg` 可执行文件（或通过 `QUICKTHUMB_FFMPEG` 环境变量显式指定路径）。

Canvas 的 MP4、WebM 和 MOV 输出均支持配乐音轨：支持 ffmpeg 能够解码的任意音频文件（MP3、WAV、AAC、OGG 等），在 MP4/MOV 中编码为 AAC，在 WebM 中编码为 Opus：

```python
mp4 = canvas.to_mp4(soundtrack="music.mp3")                    # loops to fill the video
mp4 = canvas.to_mp4(soundtrack="jingle.wav", loop_audio=False) # plays once, then silence
```

音频始终被精确裁剪至视频总长度。对于 `AudioTrack`，`loop=True` 会循环播放较短的音轨，`loop=False` 播放一遍后保持静音；`loop_audio` 为显式覆盖参数。传统的字符串路径保留旧版的循环播放默认行为。GIF 导出不支持添加配乐音轨。

!!! tip "格式技巧"
    - **背景底衬**：视频各帧合成在不透明底衬上（默认为黑色）。制作 Alpha 透明叠加图层时，请选用 WebM 或 MOV 并开启 `transparent=True`。
    - **分辨率要求**：H.264/VP9 4:2:0 视频编码要求像素尺寸必须为偶数（如 1280×720）。
    - **GIF 体积优化**：在 `GifOptions` 中设置 `max_size=(w, h)` 并将 `colors` 限制为 128（或 64）可显著压缩 GIF 文件体积。
