---
description: quickthumb Deck 参考文档，用于将多个画布整合为多页 PDF、PPTX、HTML 幻灯片放映、视频及带编号的图像序列。
---

# Deck { #deck }

`Deck` 是包含多个 `Canvas` 幻灯片的有序集合。
每页幻灯片的渲染效果与其独立渲染时完全一致；Deck 在同一底层管线之上增加了多格式批量导出的能力。
幻灯片完整保留了 Canvas 的[图层术语体系与场景局部 ID 规则](index.md#shared-layer-vocabulary)。

## 实例化创建 { #creation }

### `Deck(width=None, height=None, slides=None, theme=None)` { #deckwidthnone-heightnone-slidesnone-themenone }

```python
from quickthumb import Canvas, Deck

deck = Deck()                          # empty, no default size
deck = Deck(1280, 720)                 # default slide size for unsized slides
deck = Deck(slides=[cover, body])      # from pre-built canvases
```

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `width` | `int \| None` | 默认幻灯片宽度。与 `height` 同时提供或两者均省略。 |
| `height` | `int \| None` | 默认幻灯片高度。 |
| `slides` | `list[Canvas] \| None` | 按序排列的初始幻灯片列表。每项必须为 `Canvas` 实例。 |
| `theme` | `dict \| None` | 与每页幻灯片 `$theme.*` 引用共享的设计变量字典（幻灯片级别的局部 theme 优先）。在 `to_json()`/`from_json()` 中保持保留。 |

### `Deck.from_aspect_ratio(ratio, base_width)` { #deckfrom_aspect_ratioratio-base_width }

与 `Canvas.from_aspect_ratio` 类似，根据宽高比字符串创建具有默认幻灯片尺寸的 Deck。

```python
deck = Deck.from_aspect_ratio("16:9", 1280)   # default 1280×720
```

## 添加幻灯片 { #adding-slides }

可在构造函数中传入初始幻灯片列表（`Deck(slides=[...])`），也可使用 `.slide(canvas, transition=None, *, audio=None, duration=None, notes=None)` 逐页追加；该方法修改 Deck 自身并返回 `self` 支持链式调用。当 Deck 指定了默认尺寸时，**未定尺寸**的 `Canvas()` 会自动继承该尺寸；显式指定尺寸创建的画布则保持自身尺寸（若尺寸不同会触发 `mixed-slide-size` 排版告警）。

| 方法 | 说明 |
| --- | --- |
| `.slide(canvas, transition=None, *, audio=None, duration=None, notes=None)` | 追加单个 `Canvas`；可选的音频与时长用于配置旁白，演讲备注仅在 HTML 演讲者模式下可见 |

```python
deck = (
    Deck(1280, 720)
    .slide(
        Canvas().background(color="#101820").text(content="Cover", size=96, color="#FFFFFF"),
        audio="voice.wav",
        duration=2.5,
        notes="Introduce the central thesis.",
    )
    .slide(Canvas().background(color="#1A1A2E").text(content="Body", size=64, color="#FFFFFF"))
)
```

向未指定默认尺寸的 Deck 中添加未定尺寸的画布会抛出 `ValidationError`：请为 Deck 指定默认尺寸或为画布指定明确尺寸。

Deck 同时也是一个序列集合：支持 `len(deck)`、`deck[i]` 以及对幻灯片直接进行 `for` 循环遍历。`deck.slides` 与 `deck.notes` 返回已对齐的幻灯片和讲者备注列表的副本，因此修改返回的列表不会影响 Deck 内部状态。

## 导出方法 { #export-methods }

### `.export(path, policy=None, *, format=None, quality=None, animation=None)` { #exportpath-policynone-formatnone-qualitynone-animationnone }

与 `render()` 类似写入 Deck，并返回一个其 `written_paths` 列表中包含带编号幻灯片文件（针对栅格输出）或单个 PDF、PPTX、HTML、动画文件路径的 `ExportResult`。路径可为字符串或 `pathlib.Path`；`format`、`quality`、`animation` 与 `policy` 的含义与 `render()` 完全一致。

```python
result = deck.export("slides.png")
print(result.written_paths)
```

关于结果字段、功能预检机制以及与下方其他专用方法的关系，请参阅[推荐输出 API](../reference/export-methods.md#recommended-output-api)。

### `.render(path, format=None, quality=None, animation=None, policy=None)` { #renderpath-formatnone-qualitynone-animationnone-policynone }

根据输出文件扩展名分发渲染 Deck。返回已写入的文件路径列表。

```python
from quickthumb import GifOptions, VideoOptions

deck.render("deck.pdf")      # one multi-page PDF (a page per slide)
deck.render("deck.pptx")     # one multi-slide PPTX (a slide per slide)
deck.render("deck.gif")      # one animation playing transitions between slides
deck.render(
    "preview.gif",
    animation=GifOptions(fps=8, max_size=(540, 960), colors=128),
)
deck.render("deck.html")     # one self-contained HTML slideshow
deck.render("slides.png")    # slides_01.png, slides_02.png, …
deck.render("slides.jpg", quality=85)
```

| 后缀名 | 输出行为 |
| --- | --- |
| `.pdf` | 单个多页 PDF 文件。需要安装 `pdf` 额外依赖。 |
| `.pptx` | 单个多页 PPTX 文件。需要安装 `pptx` 额外依赖。 |
| `.gif` / `.webm` / `.mov` | 以默认设置播放图层动效与幻灯片转场的单个动画文件。WebM 与 MOV 需要 `ffmpeg`（MOV 使用 `prores_ks` 编码器）。 |
| `.mp4` | 包含可选逐页旁白的动画时间轴，采用 H.264/yuv420p 视频与 AAC 音频编码。需要安装 `ffmpeg`（有旁白时还需要 `ffprobe`）。如需静态幻灯片，请使用静态画布和 `Cut()` 转场。 |
| `.html` / `.htm` | 单个自包含的动画 HTML 幻灯片文档。 |
| `.png` / `.jpg` / `.jpeg` / `.webp` | 带编号的静态图片序列文件（例如 `slides_01.png`、`slides_02.png` 等）。`render()` 返回完整生成路径列表。 |

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `path` | `str` | — | 输出路径；光栅文件名采用 `<stem>_NN<ext>` 格式。 |
| `format` | `str \| None` | `None` | 不区分大小写的光栅编码覆盖值（`"PNG"`、`"JPEG"`、`"WEBP"`）；与文档或动画扩展名搭配时会被拒绝。 |
| `quality` | `int \| None` | `None` | 压缩质量：JPEG 为 1–95，WebP 为 1–100；其他目标格式不接受此参数。 |
| `animation` | `GifOptions \| VideoOptions \| None` | `None` | 对应格式的选项：GIF 使用 `GifOptions`，MP4/WebM/MOV 使用 `VideoOptions`。 |
| `policy` | `ExportPolicy \| None` | `None` | 渲染策略，例如动画、HTML 和 PPTX 输出的 `reduced_motion`。`render()` 和 `export()` 都会在写入前执行 `unsupported_motion` 策略。 |

!!! warning
    向 PDF、PPTX 或动画输出传入 `quality` 会抛出 `RenderingError`；渲染空 Deck 也会抛出此错误。

`GifOptions` 和 `VideoOptions` 可从 `quickthumb` 导入。`GifOptions` 控制 GIF 帧率、`hold`、循环次数、底衬、保持宽高比的 `max_size` 和调色板 `colors`；`VideoOptions` 控制 MP4/WebM/MOV 的帧率、`hold`、底衬、配乐和音频循环。配乐以 `AudioTrack(path="music.mp3", loop=True)` 传入。
`VideoOptions(transparent=True)` 可在 VP9 WebM 或 ProRes 4444 MOV 中保留 Alpha 通道（必须为布尔值，默认 `False`）；其他输出格式均不接受此选项。
两组选项的 `hold` 都必须是有限非负数（默认 3 秒），等于默认值时不会写入序列化结果。两者都接受 `workers`（1–8 的严格整数，默认 1）以及 `render_quality="standard"` 或 `"high"`。进程启动设置和支持的输入见[并行动画渲染](../reference/export-frames.md#parallel-animated-rendering)。将一种动画格式的专用选项用于另一种格式会被拒绝。

### `.to_html()` { #to_html }

返回自包含的幻灯片文档。普通观众视图支持鼠标点击、空格键和方向键导航。通过 `quickthumb serve` 打开文档并加上 `?presenter` 查询参数，可显示当前页与下一页预览、演讲备注、可暂停/继续/重置的计时器，并同步观众端控制。

```python
html = deck.to_html()
deck.render("slides.html")
```

开发时使用 `quickthumb serve slides.py`；Python 源文件须在模块级以 `deck`、`slides` 或 `canvas` 变量暴露演示文稿。

### `.to_pdf()` / `.to_pptx()` { #to_pdf-to_pptx }

返回演示文稿的文档字节数据，每个 Canvas 对应一页或一张幻灯片。

```python
with open("deck.pdf", "wb") as f:
    f.write(deck.to_pdf())   # requires quickthumb[pdf]
pptx_bytes = deck.to_pptx()  # requires quickthumb[pptx]
```

### `.to_gif(...)` / `.to_webm(...)` / `.to_mov(...)` { #to_gif-to_webm-to_mov }

返回动画形式的 Deck：每页幻灯片播放图层动画、保持完成后的状态，并通过转场动画切入该页。时间模型详见[动画 GIF 与视频](../reference/export-animation.md#animated-gif-video)。`.to_webm()` 和 `.to_mov()` 需要在 `PATH` 中提供 `ffmpeg`，或通过 `QUICKTHUMB_FFMPEG` 指定其路径。

```python
gif_bytes = deck.to_gif(fps=20, hold=3.0, loop=0, matte="#000000")
webm_bytes = deck.to_webm(fps=30, hold=3.0)
overlay_bytes = deck.to_webm(fps=30, hold=3.0, transparent=True)
```

所有动画字节方法都接受仅限关键字的 `workers=1` 和 `render_quality="standard"`（`"high"` 启用超采样）。`.to_gif()` 还接受保持宽高比缩放的 `max_size=None`，以及调色板大小 `colors=None`（指定时为 2–256）。现有位置参数保持不变。

这些控制也适用于 `.to_mp4()`。如需带旁白的静态幻灯片，请使用静态画布和 `Cut()`。文件选项和字节方法都使用 `hold`。如果某页既没有旁白也没有显式时长，动画视频要求默认停留时长为正值；Deck GIF 和静音图像序列仍接受零值。Deck GIF 忽略逐页旁白和显式时长。

`.to_webm()` 和 `.to_mov()` 的仅限关键字参数 `transparent` 只省略导出底衬；创作时设置的背景仍然可见。编解码器、Alpha 解码和转场细节见[透明 WebM](../reference/export-transparency.md#transparent-webm)。

`.to_mov()` 与 `.to_webm()` 采用相同的参数和时间控制，固定使用 ProRes 4444 视频与 AAC 音频，并保留奇数及单像素尺寸。RGBA 源数据仍为 8 位；16 位 Alpha 编码解码后可能产生一个 8 位 Alpha 等级的差异，颜色采用有损 4:4:4 YUV。实测转换限制和编码器要求见 [ProRes MOV](../reference/export-transparency.md#prores-4444-mov)。`render()` 和 `export()` 均接受 `.mov` 配合 `VideoOptions` 导出不透明或透明视频。

### `.export_image_sequence(output_directory, *, format="png", quality=None, matte=None, lossless=None, options=None, policy=None)` { #export_image_sequenceoutput_directory-formatpng-qualitynone-mattenone-losslessnone-optionsnone-policynone }

在已有的父级目录下创建一个全新目录，将动画时间轴写入为相互独立的 PNG（默认）、JPEG 或 WebP 图片文件以及 `manifest.json` 清单。
`ImageSequenceOptions(fps=30, hold=3, workers=1, render_quality="standard")` 控制时间轴与渲染合成；方法关键字参数用于选择图像编码细节。
JPEG 在不透明底衬（默认纯白）上使用 RGB 编码，支持 `quality=1..95`。
WebP 保留 Alpha 透明通道并支持 `lossless=True`；有损 WebP 支持传入质量数值。
PNG 与无损 WebP 能够严格保留渲染器的确切 RGBA8 像素。
不透明 WebP 文件可能会被解码为 RGB；清单文件模式描述的是逻辑上的 RGBA 解码规则。
导出报告中会记录实际总帧数、时间参数、编码格式及目标路径。
关于校验、按格式元数据及防止覆盖的原子级输出机制，请参阅[图像序列](../reference/export-frames.md#image-sequences)。

### `.to_mp4(...)` { #to_mp4 }

将与 `.to_webm()` 相同的动画时间轴打包在 H.264 MP4 容器中返回，包含所排定的逐页旁白音频与可选的背景原声音乐。
动态 MP4/WebM/MOV 导出支持单个 Deck 最多包含 64 页带旁白的幻灯片；无旁白的静音幻灯片不计入该 FFmpeg 输入数量上限。
若要直接导出为文件，使用 `deck.export("deck.mp4", animation=VideoOptions(soundtrack=AudioTrack(path="music.mp3", loop=True)))`。
渲染器会在导出期间将背景原声带与每页幻灯片的 `audio` 旁白进行混音。
若未指定显式选项，`deck.export("deck.mp4")` 会使用默认的 `VideoOptions()` 渲染相同的动画时间轴。

## `.diagnose()` { #diagnose }

汇总各页幻灯片的 [`Canvas.diagnose()`](canvas.md#diagnose) 结果，并增加 Deck 级别的全局排版检查。返回一个其 `findings` 列表中包含 `DeckDiagnostic` 项的 `DiagnosticReport`：

```python
for finding in deck.diagnose().findings:
    print(finding.slide_index, finding.code, finding.message)
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `str` | 幻灯片诊断代码（`off-canvas`、`tiny-text` 等）或 `mixed-slide-size` |
| `severity` | `str` | `"warning"` 或 `"error"` |
| `message` | `str` | 人类可读的描述文案 |
| `slide_index` | `int \| None` | 出问题的幻灯片索引；Deck 级别的全局问题为 `None` |
| `layer_index` | `int \| None` | 幻灯片内部出问题的图层索引（若适用） |
| `layer_id` | `str \| None` | 出问题图层的稳定 ID（包含分组子元素 ID） |
| `layer_name` | `str \| None` | 图层名称（若有） |
| `bbox` | `dict \| None` | 画布空间中的实测边界框 |
| `related_layers` | `list[str]` | 该诊断涉及的相关图层 ID 列表 |
| `measured` | `dict` | 特定规则的测量数值字典 |
| `suggestion` | `str \| None` | 修复建议提示（若可用） |

当所有幻灯片的尺寸不完全一致时，会产生 `mixed-slide-size` 告警。PDF 导出路径会按每页幻灯片的各自尺寸设定页面大小；但 PPTX 导出采用第一页幻灯片的尺寸作为整个演示文稿的全局尺寸，因此后续尺寸更大的幻灯片在 PowerPoint 中会被裁切。导出目标为 `.pptx` 时，请保持所有幻灯片尺寸统一。

## `.prefetch_assets()`（可选） { #prefetch_assets-optional }

类似于 [`Canvas.prefetch_assets()`](canvas.md#prefetch_assets-optional)，提前下载每页幻灯片所需的全部远程资源，并返回统一的 Deck 级 `asset_manifest`。
渲染和导出本身会自动拉取所需资源，因此仅在耗时较长的大型导出前预检网络故障或陈旧缓存时才需要显式调用。

## JSON { #json }

### `.to_json()` / `Deck.from_json(json_str)` { #to_json-deckfrom_jsonjson_str }

复用各个 Canvas 画布的序列化逻辑，通过规范 JSON 实现 Deck 的双向往返序列化。
数据结构形如 `{"kind": "deck", "width": ..., "height": ..., "theme": {...}, "slides": [<canvas spec>, ...]}`，其中每页幻灯片均带有 `"kind": "canvas"`；`width`/`height`（默认幻灯片尺寸）和 `theme` 仅在设置时才会输出。
在 JSON 编写的幻灯片中，当 Deck 提供了默认尺寸时，单页幻灯片可省略尺寸声明；规范序列化会显式固化这些继承而来的尺寸数值。
每页幻灯片的 `transition`、`audio`、`duration` 与 `notes` 字段会与画布字段一并完整保留。
顶层 `theme` 会与所有幻灯片共享，因此每页幻灯片中均可正常使用 `$theme.*` 变量，其机制与 `Canvas.from_json` 完全一致。

```python
spec = deck.to_json()
restored = Deck.from_json(spec)
```

!!! note
    与 `Canvas.to_json()` 类似，包含 `.custom(fn)` 幻灯片的 Deck 无法被直接序列化，除非注册了这些自定义回调。
    `from_json()` 期望接收 **JSON 字符串**而非字典。
