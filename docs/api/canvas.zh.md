---
description: quickthumb Canvas 实例化创建、宽高比、图层构成、渲染导出、JSON 加载及图像输出参考文档。
---

# Canvas { #canvas }

`Canvas` 是最顶层根对象。它包含尺寸以及按绘制顺序排列的有序图层列表。
其创作字段遵循[通用图层术语体系](index.md#shared-layer-vocabulary)，该体系同样适用于 Deck 幻灯片与规范 JSON。

## 实例化创建 { #creation }

### `Canvas(width=None, height=None)` { #canvaswidthnone-heightnone }

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720)
```

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `width` | `int \| None` | 画布宽度（像素）。必须为正整数。 |
| `height` | `int \| None` | 画布高度（像素）。必须为正整数。 |

宽度和高度必须同时指定，或两者均省略。
**未指定**尺寸创建的画布（`Canvas()`）属于*未定尺寸*（unsized）状态：
它支持调用图层构建方法，但在直接赋予尺寸或将其加入已指定尺寸的 [`Deck`](deck.md)（从而继承 Deck 的默认尺寸）之前，无法进行渲染、排版诊断或序列化。
可通过检查 `canvas.has_size` 判断当前状态。

### `Canvas.from_aspect_ratio(ratio, base_width)` { #canvasfrom_aspect_ratioratio-base_width }

根据宽高比字符串和基准宽度创建画布。高度将自动计算得出。

```python
wide     = Canvas.from_aspect_ratio("16:9", base_width=1280)   # 1280×720
square   = Canvas.from_aspect_ratio("1:1",  base_width=1080)   # 1080×1080
vertical = Canvas.from_aspect_ratio("9:16", base_width=1080)   # 1080×1920
```

| 参数 | 类型 | 说明 |
| --- | --- | --- |
| `ratio` | `str` | `"W:H"` 格式的宽高比字符串，例如 `"16:9"` |
| `base_width` | `int` | 画布基准宽度（像素） |

## 图层构建方法 { #layer-builders }

所有图层构建方法均会修改画布并返回 `self`，支持链式调用。

| 方法 | 说明 |
| --- | --- |
| `.background(...)` | 添加全画布背景图层 |
| `.text(...)` | 添加文本图层 |
| `.image(...)` | 添加叠加图片图层 |
| `.shape(...)` | 添加形状图层 |
| `.path(...)` | 绘制带填充或描边的 [SVG 路径](path.md) |
| `.svg(...)` | 添加 SVG 矢量图层，在渲染时进行栅格化 |
| `.video(...)` | 向动效排版中添加[视频剪辑](video.md) |
| `.counter(...)` | 添加[动态数字计数器](#animated-counters) |
| `.group(...)` | 添加包含子图层的自动布局分组容器 |
| `.outline(...)` | 添加围绕画布边缘的描边边框 |
| `.chart(...)` | 基于类型化图表规范添加确定性的柱状图或折线图图层 |
| `.qr_code(...)` | 添加正方形二维码图层 |
| `.custom(fn)` | 添加自定义 Pillow 图像绘制回调图层 |

完整参数详情请参阅[数据可视化参考](data-visualizations.md)及各图层专属参考文档。

### 动态数字计数器 {#animated-counters}

使用 `.counter(from_, to, duration, ...)` 将递增/递减数字制作为动态文本图层。
可正常传入 `position`、`size`、`color` 等常规文本参数：

```python
from quickthumb import Canvas

canvas = Canvas(320, 180).background(color="#102030").counter(
    0, 100, 2, suffix="%", size=64, color="#FFFFFF", position=(40, 50)
)
canvas.render("counter.gif")
```

`delay`、`decimals`、`minimum_integer_digits`、`prefix`、`suffix` 与 `grouping` 用于控制时间轴与数字格式化显示。
`style` 支持 `"plain"`、`"odometer"` 或 `"flip"`；`easing` 支持 `"linear"`、`"ease_in"`、`"ease_out"` 或 `"ease_in_out"`。
静态单帧输出将展示最终数值。

## `.diagnose()` { #diagnose }

无需写入文件，直接排查设计中的排版与可读性缺陷。
返回一个包含 `findings` 诊断项列表的 `DiagnosticReport`（排版无隐患时列表为空）：

```python
for finding in canvas.diagnose().findings:
    print(finding.severity, finding.code, finding.message)
```

诊断代码包括：`off-canvas`、`tiny-text`、`text-overflow`、`text-clipped`、`missing-glyph`、`low-contrast`、`layer-overlap`、`layer-hidden` 与 `edge-crowding`。
详细说明及终端对应的 `quickthumb lint`（或 `quickthumb diagnose`）命令请参阅[诊断与 CLI](../diagnostics.md)。

## `.prefetch_assets()`（可选） { #prefetch_assets-optional }

正常情况下你无需主动调用此方法：
`render()` 和 `export()` 会自动下载所需的远程图片、SVG、文字填充图片及字体，且 `export()` 会返回下载记录 `asset_manifest`。
仅在耗时较长的批量导出前预检网络连接/陈旧缓存项，或为了后续离线渲染预热缓存时，才需要显式调用此方法。
它不执行实际渲染，仅返回资源清单：

```python
manifest = canvas.prefetch_assets().asset_manifest
if any(entry.status == "stale" for entry in manifest):
    ...  # decide whether to proceed with cached bytes
```

有关状态枚举、`QUICKTHUMB_ASSET_MAX_AGE` 缓存有效期及离线模式，请参阅[远程资源与缓存](../reference/export-assets.md#remote-assets-and-caching)。

## 导出方法 { #export-methods }

### `.export(path, policy=None, *, format=None, quality=None, animation=None)` { #exportpath-policynone-formatnone-qualitynone-animationnone }

与 `render()` 类似将画布写入文件，并返回一个其 `written_paths` 列表中包含所写文件的 `ExportResult`。
路径参数可为字符串或 `pathlib.Path`。`format`、`quality`、`animation` 与 `policy` 的语义与 `render()` 一致。

```python
result = canvas.export("card.png")
print(result.written_paths)
```

关于结果字段、功能预检机制以及与下方其他专用方法的关系，请参阅[推荐输出 API](../reference/export-methods.md#recommended-output-api)。

### `.render(path, format=None, quality=None, debug=False, animation=None, policy=None)` { #renderpath-formatnone-qualitynone-debugfalse-animationnone-policynone }

渲染画布并写入磁盘文件。输出格式根据文件扩展名自动识别。
`.svg`、`.pptx`、`.pdf` 生成矢量或富文档产物；`.gif`、`.mp4`、`.webm`、`.mov` 播放画布图层声明的 `animation` 动效并导出为动画。
详情请参阅 [SVG、PPTX、PDF 与视频导出](../exports.md)。
Canvas 的 `.lot` 导出支持记录 [Lottie 矢量](../reference/export-lottie.md#lottie-vectors) 中所述的受限原生矢量特性，并通过 `LottieOptions` 指定 fps 和结尾定格时长。
若包含不支持的内容，将在写入前直接拒绝抛错，不会隐式降级为 PNG。

```python
from quickthumb import GifOptions, VideoOptions

canvas.render("output.png")
canvas.render("output.jpg", format="JPEG", quality=85)
canvas.render("output.webp", format="WEBP", quality=90)
canvas.render("debug.png", debug=True)  # raster output with public layer-id bboxes
canvas.render("output.svg")
canvas.render("output.pptx")  # requires quickthumb[pptx]
canvas.render("output.pdf")   # requires quickthumb[pdf]
canvas.render("output.gif")   # animated; .mp4/.webm/.mov require the ffmpeg binary
canvas.render(
    "preview.gif",
    animation=GifOptions(fps=8, max_size=(540, 960), colors=128),
)
canvas.render("preview.mp4", animation=VideoOptions(fps=30))
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `path` | `str` | — | 输出文件路径。 |
| `format` | `str \| None` | `None` | 不区分大小写的栅格编码格式重写。有效值为 `"PNG"`、`"JPEG"`、`"WEBP"`；若与文档或动画后缀名混用将被直接拒绝。 |
| `quality` | `int \| None` | `None` | 压缩质量。JPEG 为 1–95，WebP 为 1–100；对其他格式指定时将被拒绝。 |
| `debug` | `bool` | `False` | 在栅格图片上叠加公开图层 ID 边界框，便于视觉检查。 |
| `animation` | `GifOptions \| VideoOptions \| LottieOptions \| None` | `None` | 格式专属选项。GIF 使用 `GifOptions`，MP4/WebM/MOV 使用 `VideoOptions`，`.lot` 使用 `LottieOptions`。 |
| `policy` | `ExportPolicy \| None` | `None` | 渲染器策略，例如动画、HTML、PPTX 中的 `reduced_motion`。`render()` 与 `export()` 均在写入前应用 `unsupported_motion`。`export()` 会在报告中包含显式请求的[静态 SVG 保真度检查](../reference/export-validation.md#optional-static-svg-fidelity-report)。 |

!!! warning
    在 `format="PNG"` 时传入 `quality` 会抛出 `RenderingError`。对文档或动画输出（`.svg`、`.pptx`、`.pdf`、`.html`、`.gif`、`.mp4`、`.webm`、`.mov`、`.lot`）传入 `debug=True` 同样会抛出 `RenderingError`。

`GifOptions`、`VideoOptions` 与 `LottieOptions` 均可直接从 `quickthumb` 顶层导入。
`GifOptions` 支持配置 `fps`、`hold`、`matte`、`loop`、`max_size=(width, height)` 与 `colors`。
`VideoOptions` 支持配置 `fps`、`hold`、`matte`、`soundtrack=AudioTrack(...)` 与 `loop_audio`。
`VideoOptions(transparent=True)` 可在 VP9 WebM 与 ProRes 4444 MOV 中保留 Alpha 透明通道。该参数为严格布尔值，默认值为 `False`；其他输出格式若指定此选项将被直接拒绝。
上述选项中的 `hold` 必须为大于等于 0 的严格有限数值，默认为 3 秒。若与默认值相等，在序列化选项中会自动省略。
上述选项在渲染时还支持传入 `workers`（1–8 范围内的正整数，默认为 1）以及 `render_quality="standard"` 或 `"high"`。
关于多进程 spawn 行为与受支持的输入类型，请参阅[并行多帧渲染](../reference/export-frames.md#parallel-animated-rendering)。
GIF 专属的尺寸缩放与调色板选项在 MP4/WebM/MOV 中会被直接拒绝。

### `.to_svg(embed_fonts=False)` { #to_svgembed_fontsfalse }

将画布渲染并返回为 SVG 文档字符串。`embed_fonts=True` 会将使用的字体文件作为 `@font-face` Data URL 内嵌其中。

```python
svg = canvas.to_svg(embed_fonts=True)
```

### `.to_pptx()` { #to_pptx }

返回包含可编辑文本框与自选图形的单页 PowerPoint 文件二进制数据（`bytes`）。需要安装 `pptx` 额外依赖。

```python
with open("deck.pptx", "wb") as f:
    f.write(canvas.to_pptx())
```

### `.to_pdf()` { #to_pdf }

将画布渲染并返回为 PDF 文件二进制数据（`bytes`）。
在字体能够安全内嵌且不需要复杂字符整形的前提下，生成包含原生矢量背景/形状以及可选取文本的单页 PDF。
对于不支持的原生文本，会以像素级精确的图片切片形式嵌入。需要安装 `pdf` 额外依赖。

```python
with open("card.pdf", "wb") as f:
    f.write(canvas.to_pdf())
```

### `.to_gif(...)` / `.to_mp4(...)` / `.to_webm(...)` / `.to_mov(...)` { #to_gif-to_mp4-to_webm-to_mov }

依次播放图层声明的 `animation` 动效，随后将最终画面定格停留 `hold` 秒，并返回动画文件数据。
详情请参阅[动画 GIF 与视频](../reference/export-animation.md#animated-gif-video)。
对于不包含任何动效的画布，将生成单帧 GIF 图像。
`.to_mp4()`、`.to_webm()` 与 `.to_mov()` 要求系统 `PATH` 中包含 `ffmpeg` 或通过 `QUICKTHUMB_FFMPEG` 显式指定二进制路径。

```python
gif_bytes = canvas.to_gif(fps=20, hold=3.0, loop=0, matte="#000000")
mp4_bytes = canvas.to_mp4(fps=30, hold=2.0, soundtrack="music.mp3")
webm_bytes = canvas.to_webm(fps=30, hold=2.0)
overlay_bytes = canvas.to_webm(fps=30, hold=2.0, transparent=True)
```

`.to_mp4()`、`.to_webm()` 与 `.to_mov()` 支持传入音频文件路径 `soundtrack`（自动按视频长度截断混音）以及显式的循环选项 `loop_audio`。
`AudioTrack(..., loop=True)` 可循环播放较短的配乐。直接传入字符串路径将保留默认的循环播放行为。
GIF 无法包含音频。完整参数列表请参阅 [Deck API](deck.md)。

所有动态字节导出方法均支持仅限关键字参数 `workers=1` 与 `render_quality="standard"`（指定为 `"high"` 时开启超采样）。
`.to_gif()` 还支持用于保持宽高比缩放的 `max_size=None` 以及调色板大小 `colors=None`（传入时支持 2–256 色）。
原有的位置参数保持不变。

`.to_webm()` 与 `.to_mov()` 的仅限关键字参数 `transparent` 仅省略导出底衬衬垫（matte）；人工声明的背景图层依然正常可见。
编解码器、Alpha 解码及转场细节请参阅[透明 WebM](../reference/export-transparency.md#transparent-webm)。

`.to_mov()` 与 `.to_webm()` 具有相同的参数与时间控制，固定编码为 ProRes 4444 视频与 AAC 音频。
支持保留奇数宽高和单像素尺寸。输入的 RGBA 源数据为 8 位；16 位 Alpha 编码解码后可能会产生 1 级的 8 位 Alpha 色阶微差。
色彩采用有损 4:4:4 YUV。实测转换精度限制与编码器配置要求请参阅 [ProRes MOV](../reference/export-transparency.md#prores-4444-mov)。
`render()` 和 `export()` 在不透明及透明视频场景下均接受 `.mov` 后缀并搭配 `VideoOptions`。

### `.export_image_sequence(output_directory, *, format="png", quality=None, matte=None, lossless=None, options=None, policy=None)` { #export_image_sequenceoutput_directory-formatpng-qualitynone-mattenone-losslessnone-optionsnone-policynone }

在已有的父级目录下创建一个全新目录，将动画时间轴写入为相互独立的 PNG（默认）、JPEG 或 WebP 图片文件以及 `manifest.json` 清单。
`ImageSequenceOptions(fps=30, hold=3, workers=1, render_quality="standard")` 控制时间轴与渲染合成；方法关键字参数用于选择图像编码细节。
JPEG 在不透明底衬（默认纯白）上使用 RGB 编码，支持 `quality=1..95`。
WebP 保留 Alpha 透明通道并支持 `lossless=True`；有损 WebP 支持传入质量数值。
PNG 与无损 WebP 能够严格保留渲染器的确切 RGBA8 像素。
不透明 WebP 文件可能会被解码为 RGB；清单文件模式描述的是逻辑上的 RGBA 解码规则。
导出报告中会记录实际总帧数、时间参数、编码格式及目标路径。
关于校验、按格式元数据及防止覆盖的原子级输出机制，请参阅[图像序列](../reference/export-frames.md#image-sequences)。

### `.to_base64(format="PNG", quality=None)` { #to_base64formatpng-qualitynone }

将渲染后的图像返回为 Base64 编码字符串。

```python
b64 = canvas.to_base64(format="PNG")
b64 = canvas.to_base64(format="WEBP", quality=90)
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `format` | `str` | `"PNG"` | 输出格式：`"PNG"`、`"JPEG"` 或 `"WEBP"` |
| `quality` | `int \| None` | `None` | 压缩质量：JPEG 1–95 或 WebP 1–100。 |

### `.to_data_url(format="PNG", quality=None)` { #to_data_urlformatpng-qualitynone }

将渲染后的图像返回为 Data URL 格式（`data:<mime>;base64,...`）。

```python
url = canvas.to_data_url(format="JPEG", quality=90)
# → "data:image/jpeg;base64,..."
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `format` | `str` | `"PNG"` | 输出格式：`"PNG"`、`"JPEG"` 或 `"WEBP"` |
| `quality` | `int \| None` | `None` | 压缩质量：JPEG 1–95 或 WebP 1–100。 |

### `.inspect()` { #inspect }

返回确定性的 `CanvasInspection` 记录，包含图层标识符、顺序、可见性、边界框及文本排版元数据。
不会写入任何磁盘输出文件。测量尺寸时可能会读取本地字体或图片文件，但不会触发父图层的实际绘制管线。

```python
report = canvas.inspect()
for layer in report.layers:
    print(layer.id, layer.bbox)
```

对于包含父级变换关联的场景，边界框反映的是静态排版布局而非动画运行中的瞬时帧；计算策略偏保守，范围可能略微超出实际着色像素。
使用 `canvas.render("debug.png", debug=True)` 可视化查看这些边界框。
关于裁剪、蒙版、动态计数器和父级变换，请参阅[检查复杂布局](../reference/inspection-details.md)。

### `.to_json()` { #to_json }

将画布序列化为 JSON 字符串。

```python
json_str = canvas.to_json()
```

若画布中包含 `.custom(fn)` 图层，由于回调函数无法序列化，将抛出 `ValidationError`。

### `Canvas.from_json(json_str)` { #canvasfrom_jsonjson_str }

从 JSON 字符串反序列化构建画布。

```python
canvas = Canvas.from_json(json_str)
```

!!! note
    `from_json()` 期望接收 **JSON 字符串**而非 Python 字典。若持有字典，请先调用 `json.dumps(data)`。

## `.custom(fn)` { #customfn }

添加一个接收并返回 Pillow `Image` 的自定义绘图回调。

```python
from PIL import ImageDraw
from quickthumb import Canvas

def draw_badge(image):
    d = ImageDraw.Draw(image)
    d.polygon([(70, 70), (240, 70), (155, 180)], fill="#FF3B30")
    return image

canvas = Canvas(512, 512).custom(draw_badge)
```

| 规则 | 详情 |
| --- | --- |
| `fn` 必须为可调用对象 | 接收一个 `PIL.Image.Image` 参数 |
| 返回值 | 可返回就地修改后的同一图像、相同尺寸的新图像或 `None` |
| 错误处理 | 回调函数内部抛出的异常会被封装为 `RenderingError` |
| 序列化限制 | 自定义图层**无法**序列化为 JSON |
