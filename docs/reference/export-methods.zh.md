---
description: quickthumb 导出方法、结果凭据与格式选择契约参考。
---

# 导出方法与结果凭据 { #export-methods-and-receipts }

[导出参考](../exports.md) · [输出格式选择指南](../output-guide.md)

## 推荐的输出 API { #recommended-output-api }

使用 `export()` 输出 Canvas 或 Deck，并获取包含 `written_paths`、功能/降级诊断、像素/时序元数据、资源及实测渲染环境信息的 `ExportResult`：
输出文件的扩展名决定目标格式。MP4、WebM、MOV 和 GIF 会播放动画时间轴。
Deck 视频还会混音各幻灯片的旁白语音。

```python
from quickthumb import VideoOptions

result = deck.export("slides.mp4", animation=VideoOptions(hold=2, render_quality="high"))
print(result.written_paths, result.fallback_diagnostics)
deck.export("slides.html")  # interactive slideshow with click-triggered motion
canvas.export("card.webp", quality=85)  # JPEG/WebP compression quality
```

| 需求 | 入口方法 |
| --- | --- |
| 输出文件，应用功能策略并返回结果凭据 | `export(path, ...)` |
| 绘制调试边界框或使用更低级的底层文件渲染器 | `render(path, ...)` |
| 获取二进制字节或内存文档 | `to_mp4()`、`to_gif()`、`to_html()` 等 |
| 导出带旁白的 Deck 幻灯片 | `export(path, animation=VideoOptions(hold=3))` / `to_mp4(hold=3)` |
| 输出无声动画逐帧序列及清单文件 | `export_image_sequence(directory, options=...)` |
| 输出受限的仅 Canvas Lottie 矢量文件 | `canvas.export("scene.lot", animation=LottieOptions(fps=30, hold=3))`；参见 [Lottie 矢量导出](export-lottie.md#lottie-vectors) |

所有支持动画的字节方法和选项均使用 `hold` 参数指定最终静止状态保持的秒数。
`render_quality="standard"` 或 `"high"` 控制动画合成渲染质量；
`export()` / `render()` 中的 `quality` 控制压缩质量：JPEG 接收 1–95 整数，WebP 接收 1–100 整数。
除非需要高级的基于多进程派生（spawn）的渲染，否则请保持 `workers=1`。
可选的[时间曝光](../timing.md#temporal-exposure)可为 Canvas 导出添加动态模糊（motion blur）。
`export()` 和 `render()` 在写入前都会严格执行文件功能策略（如 `unsupported_motion="error"`）；`export()` 还会额外返回执行凭据。
字节导出方法提供针对具体格式的专属控制参数，但不返回共享的文件凭据。
对于 Deck 光栅图像序列，请使用返回的 `written_paths`，它们是带数字编号的文件路径列表。
图像序列导出使用独立的专用 API，因为其输出目标是一个全新目录。

## 格式与选项选择规则 { #format-and-option-selection }

Canvas 与 Deck 遵循相同的格式选择规则，唯一的例外是 `.lot` 为 Canvas 独占；Deck 会拒绝 Lottie 输出。

| 输入 | 结果 |
| --- | --- |
| 文件扩展名（未指定 `format`） | 决定输出格式；`.jpg`/`.jpeg` 报告 `output_format="jpeg"`，`.htm`/`.html` 报告 `"html"`。 |
| 大小写不敏感的 `format="PNG"`、`"JPEG"` 或 `"WEBP"` | 为光栅文件、未知扩展名或无扩展名文件名指定光栅编码。保留请求的文件名，不会为了匹配编码而重命名文件。 |
| 光栅 `format` 搭配文档或动画扩展名 | 直接拒绝报错，避免将图片字节写入 SVG、PDF、HTML、PPTX、视频或 `.lot` 文件名中。 |
| `quality` | JPEG 整数 1–95 或 WebP 整数 1–100；其余目标格式传入会被拒绝。 |
| `animation` | GIF 对应 `GifOptions`；MP4/WebM/MOV 对应 `VideoOptions`；Canvas `.lot` 对应 `LottieOptions`。其余静态/文档目标传入会被拒绝。 |

格式选择、压缩质量以及动画选项系列冲突会在读取资源或写入文件前被立即拒绝。各编码器的具体限制会在导出准备阶段校验。渲染或编码失败仍可能在后续发生；常规文件导出并不是原子化的多文件事务。请检查返回的 `written_paths`，而不是凭空猜测 Canvas 或带编号的 Deck 文件名。Deck 无法导出为单个 SVG；如需 SVG 请分别导出其各个 Canvas 幻灯片。有关独立新目录与编码选项契约，请参见[图像序列](export-frames.md#image-sequences)。

## 文档图层路由机制 { #document-layer-routing }

Canvas 与 Deck 的 HTML/PPTX 导出，以及 Canvas 的 SVG/PDF 导出，均会在 `result.capability_report` 中以 `feature="layer_representation"` 报告实际执行的图层路由路径。
原生 HTML/CSS、SVG/PDF 基础图元、可编辑的 PowerPoint 对象及原始嵌入 SVG 的支持状态为 `support="native"`；
降级生成的 PNG 切片为 `support="fallback"`，且 `fallback="rasterize"`。
对于将可编辑前景与固定发光图片结合的 PPTX 内容，其状态为 `support="partial"`，`fallback="rasterize"`；编辑前景内容后需重新导出以更新发光效果。
这些指标是对表示方式的观察记录，并非像素保真度比对。

`result.fallback_diagnostics` 标识了受影响的检查图层 `layer_id` 及原因。被保留的编组会在 `layer_ids` 中包含其所有子图层 ID；依赖共同背景的前缀复合层没有单一的 `layer_id`，会在 `layer_ids` 中列出所有参与图层源。之所以将此类复合层合并报告，是因为其视觉呈现取决于各图层混合后的像素。被展平的自动布局子图层保留其原始检查 ID。空的光栅切片和空文本不会生成任何元素，也不会产生表示形式观察记录。

对于这些执行的路由，`native_attempt=True` 包含原生内容输出，或者对原生候选方案进行了执行/验证但最终降级为光栅的情况。请通过 `support` 和 `fallback` 来确认最终实际采用的表示形式。`False` 则表示在进行原生生成或验证前就已选定了光栅捕获。在仅包含功能检查的纯静态诊断中，该信息可能未确定（`None`）。父级场景在 SVG/PDF/PPTX 中报告其静态复合体；HTML 还可以报告带有烘焙仿射 CSS 动画的 PNG 图层。原有的动效功能诊断依然独立保留。SVG/PDF 观察记录描述创作时的静态输出。PDF 文本在受支持时会保留嵌入字体；但当文字塑形、字形覆盖率或字体嵌入受限时，可能会选择带有原因说明的光栅切片。

执行的 Deck 观察记录还带有从 0 开始的 `slide_index`。图层 ID 保持在单张幻灯片内部有效，与 `deck.inspect().slides[index]` 一致；可通过同时查看这两个字段来区分不同幻灯片间的重名图层 ID。Canvas 观察记录省略 `slide_index`。Deck HTML 保留其交互提示、转场和演讲者备注；这些表示记录不会把基于点击驱动的幻灯片变成固定时长的自动播放。

例如，`ExportPolicy(unsupported_motion="error")` 并不会拒绝静态的遮罩形状：因为该 HTML 路由会使用 PNG 切片保留其遮罩，并如实报告该决策。系统不会引入额外的图层选择策略。该执行路由报告涵盖 Canvas SVG/PDF 与 Canvas/Deck HTML/PPTX；Deck PDF 暂不收集此类观察记录。保真度指标描述整个文档，不会归因于各个具体的降级图层。在打开 HTML 目标文件前会先渲染所有幻灯片，因此若后续幻灯片不支持或发生严格动效拒绝，原有文件将完好保留。

PPTX 路由描述实际的 OOXML 表示方式：原生文本框和自选图形保持为可编辑对象；PNG 切片保留其光栅像素和位置，但失去单字形与矢量的可编辑性。降级为光栅的原因包括遮罩、背景混合、图像/径向渐变文本填充以及不受支持的字体语义。Canvas 记录省略幻灯片索引；Deck 记录标明所在幻灯片。PPTX 文件导出在打开目标路径前会先构建完整演示文稿，因此后续图层渲染失败不会破坏已存在的目标文件。

这些结构层面的观察记录并不能保证在特定查看器中与 PowerPoint 或 Keynote 达到像素级一致，也无法证明字体可用性、动画时序或透明度表现。系统不提供 PPTX 保真度策略或自动化应用程序渲染器。PPTX 几何尺寸按每个源像素 9,525 EMU（即每英寸 96 像素）或每个源像素 0.75 PDF 点进行换算。后续基于 PDF 的查看器对比必须基于其实际页面尺寸推导缩放比例，而不能假定 PDF 导出器的一点对一像素映射关系。

## 导出调用迁移指南 { #migrating-output-calls }

- `Deck.to_mp4()` 现在会播放动画，与 Canvas 及文件导出保持一致。请将原有的 `to_animated_mp4()` 和 `to_narrated_mp4()` 调用替换为 `to_mp4()`。
- 将 `render_mp4()` 和 `render_narrated_mp4()` 替换为 `export("deck.mp4")`。独立的静止幻灯片编码器已被移除，不保留别名。如需保持静止场景，请创建静态 Canvas 并使用 `Cut()`；这不会冻结已经带有动画的 Deck，也不保证编码输出完全一致。
- `export_image_sequence()` 替代了 `export_png_sequence()`；公开的 options/manifest/result 模型现为 `ImageSequence*`，旧别名已全部废除。
- 将带动画 Deck 的 `slide_duration=` 和带旁白的 `default_duration=` 替换为 `hold=`。将动画相关的 `quality=` 替换为 `render_quality=`，包括保存的 GifOptions、VideoOptions 和 ImageSequenceOptions JSON。不保留别名。

## 导出工作原理 { #how-export-works }

SVG、PDF 和 PPTX 导出器会将符合条件的图层保持为**原生（native）**形式，并在无法使用原生表示时降级使用规范的 PNG 切片。位置、折行与对齐共享光栅渲染器的布局计算。HTML 采用相同的原生或光栅策略；参见下文 [HTML](export-documents.md#html)。

[Lottie](export-lottie.md#lottie-vectors) 则仅接受受限的原生矢量子集，并在写入前拒绝不受支持的内容，绝不会回退替换为 PNG 帧。

| 图层类型 | SVG | PPTX | PDF |
| --- | --- | --- | --- |
| 背景颜色 / 渐变 | 原生 `rect` + 渐变定义 | 原生形状填充（线性渐变为原生，径向渐变嵌入图像） | 原生填充；不透明渐变为原生，半透明渐变嵌入图像 |
| 外边框 | 原生 `rect` 描边 | 原生带边框矩形 | 原生矩形描边 |
| 基础形状（所有图元） | 原生元素，包含旋转与描边/投影/发光 | 原生自选图形；多边形转为任意多边形 | 原生路径包含旋转；带有效果的形状嵌入图像 |
| 文本（普通与富文本） | 每行/片段的原生 `<text>`，包含折行、字距、渐变填充与效果 | 带有分段样式的可编辑文本框 | 字体可嵌入且无需复杂塑形时为原生可选文本；不支持的字体、渐变/图像填充或模糊效果嵌入为像素图像 |
| 编组（自动布局） | 子图层按布局位置以原生形式导出 | 同左 | 同左 |
| 图像及图像填充文本 | 嵌入 PNG 切片 | 嵌入图片 | 嵌入图片 |
| SVG 图层 | 嵌入为矢量数据 URL（应用效果时降级为光栅） | 嵌入图片 | 嵌入图片 |
| 混合模式与自定义图层 | 最后一个混合/自定义图层之下的所有内容展平合并为一张 PNG | 同左 | 同左 |

## Deck（多张图片与幻灯片） { #decks-multiple-images-and-slides }

`Deck` 是一个由 Canvas 组成的有序列表。每张幻灯片都是一个完整的 `Canvas`，其渲染效果与单独渲染完全一致。完整方法列表请参见 [Deck API 参考](../api/deck.md)。

只需为 Deck 指定一次尺寸，各个幻灯片即可作为直接继承该尺寸的简单 `Canvas()`：

```python
from quickthumb import AudioTrack, Canvas, Deck, VideoOptions

deck = (
    Deck(1280, 720)   # default slide size; Deck.from_aspect_ratio("16:9", 1280) also works
    .slide(Canvas().background(color="#101820").text(content="Cover", size=96, color="#FFFFFF"))
    .slide(Canvas().background(color="#1A1A2E").text(content="Body", size=64, color="#FFFFFF"))
)
# pre-built canvases work too: Deck(slides=[cover, body])

deck.render("deck.pdf")     # one multi-page PDF (a page per slide)
deck.render("deck.pptx")    # one multi-slide PPTX (a slide per slide)
deck.render("deck.gif")     # one animation playing transitions between slides
deck.export("deck.mp4")     # animated slides with per-slide narration
deck.render(
    "deck.mp4",
    animation=VideoOptions(soundtrack=AudioTrack(path="music.mp3", loop=True)),
)  # animated + mixed audio
deck.render("animated.mp4", animation=VideoOptions(fps=20))  # animated, silent
deck.render("slides.png")   # numbered sequence: slides_01.png, slides_02.png, …

pdf_bytes = deck.to_pdf()
pptx_bytes = deck.to_pptx()
gif_bytes = deck.to_gif()
webm_bytes = deck.to_webm()
mp4_bytes = deck.to_mp4()   # timeline with per-slide narration
```

`render()` 根据输出扩展名分发处理：`.pdf` 和 `.pptx` 生成单个多页文档；`.gif`、`.mp4`、`.webm` 和 `.mov` 生成动画；光栅图像格式没有原生的多页容器，因此 Deck 会将每张幻灯片写入带有前导零编号的独立序列文件，并返回写入的文件路径列表。

幻灯片可以拥有不同尺寸。`deck.diagnose()` 会汇总每张幻灯片的[诊断信息](../diagnostics.md)（每条均带有 `slide_index` 标记），并在尺寸不一致时添加 `mixed-slide-size` 警告。PDF 路由会按各幻灯片的尺寸调整对应页面大小，但 PPTX 仅拥有由第一张幻灯片决定的全局尺寸，因此比第一张幻灯片更大的页面在 PowerPoint 中会被截断。输出目标为 `.pptx` 时请确保幻灯片尺寸一致。Deck 可复用单个 Canvas 序列化通过 `deck.to_json()` / `Deck.from_json(...)` 实现完整的 JSON 往返转换。

## CLI 命令行工具 { #cli }

CLI 同样根据输出文件的扩展名自动选择格式：

```bash
quickthumb render spec.json -o card.svg
quickthumb render spec.json -o card.pptx
quickthumb render spec.json -o card.pdf

# Live HTML slides; open /?presenter for the presenter dashboard
quickthumb serve slides.py
```
