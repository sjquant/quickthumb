---
description: quickthumb 图像序列导出、高质量合成与多进程并行渲染参考。
---

# 图像序列与渲染质量 { #image-sequences-and-render-quality }

[导出参考](../exports.md) · [输出格式选择指南](../output-guide.md)

## 图像序列 { #image-sequences }

`Canvas.export_image_sequence()` 及对应的 Deck 方法将实际动画时间轴输出为独立的 PNG、JPEG 或 WebP 图像文件序列以及一个清单文件（manifest）。目标目录必须为不存在的全新路径，且其父级目录必须已存在。默认为 PNG 格式。

```python
from quickthumb import ImageSequenceOptions

options = ImageSequenceOptions(fps=24, hold=2, render_quality="high", workers=2)
result = canvas.export_image_sequence("overlay_frames", options=options)
canvas.export_image_sequence("review_frames", format="jpeg", quality=85, matte="white", options=options)
canvas.export_image_sequence("web_frames", format="webp", lossless=True, options=options)
print(result.frame_count, result.duration, result.manifest_path)
```

编码控制参数作为该方法的命名关键字实参传入，与 `ImageSequenceOptions(fps=30, hold=3, workers=1, render_quality="standard")` 中的时序与图层合成参数相互独立：

| 控制参数 | PNG | JPEG | WebP |
| --- | --- | --- | --- |
| `format`（大小写不敏感） | 默认为 `"png"` | `"jpeg"` | `"webp"` |
| `quality` | 拒绝传入 | 整数 1–95；默认为 90 | 有损压缩整数 1–95；默认为 80 |
| `matte` | 拒绝传入 | 不透明颜色字符串；默认为白色 | 拒绝传入 |
| `lossless` | 拒绝传入 | 拒绝传入 | 布尔值；默认为 `False` |

`lossless=True` 与 `quality` 不能组合使用：quality 指定的是有损压缩质量，而非无损 WebP 编码器的压缩努力级别。传入无效类型或不兼容选项会在创建任何输出或暂存目录之前直接报错。选项模型仅包含 `fps`（有限浮点数，>0 且 ≤120）、`hold`（有限非负秒数）、`workers`（严格整数 1–8）以及 `render_quality`（`"standard"` 或 `"high"`）。

PNG 格式完好保留渲染器精确的 **8 位直通 Alpha（straight-alpha）RGBA 字节**，包括隐藏的 RGB 数据。无损 WebP 同样保留这些像素，包括隐藏的 RGB 数据。JPEG 将 Alpha 通道压平合并至指定底衬色并编码为 RGB；JPEG 和有损 WebP 可能会轻微改变色彩，不保证与规范像素绝对一致。WebP 保留 Alpha 通道，但在完全不透明的文件中可能会省略冗余的 Alpha 平面，从而在某些图片查看器中识别为 RGB。当按照清单文件中声明的逻辑 `mode: "RGBA"` 使用这些文件时，请将其转换回 RGBA。在所有格式中，创作时指定的背景均保持可见。奇数尺寸及 1 像素尺寸均保留所有行与列。不同尺寸的幻灯片会适配第一张画布的完整尺寸，并在编码前填充透明边距（JPEG 填充底衬颜色边距）。导入的图像不作 ICC 归一化；导出文件会剔除继承的配置文件/元数据，且不对 sRGB 或色彩空间作任何特殊声明。

生成的目录包含 `000000.png`、`.jpg` 或 `.webp` 等连续命名的图像文件，以及一个紧凑的 `manifest.json` 文件。清单中记录了 `version: "1"`、`format: "image_sequence"`、文档 `kind`、`encoding: "png"|"jpeg"|"webp"`、相对文件名模板 `filename_pattern`（`%06d.png`、`%06d.jpg` 或 `%06d.webp`）以及 `start_index: 0`。实际写入的 `frame_count`、`fps`、`duration`、`width` 和 `height` 精确描述了生成的文件。像素字段描述逻辑解码模式：PNG/WebP 记录 `mode: "RGBA"` 与 `alpha: "straight"`；JPEG 记录 `"RGB"` 与 `"none"`；`bit_depth` 均为 8。`lossless` 报告所选编码；解析后的 `quality` 与 `matte` 在适用时记录，其余为 `null`。

`ImageSequenceResult` 在 `ImageSequenceManifest` 基础上增加了绝对路径 `output_directory`、`manifest_path` 以及 `capability_report` 诊断信息。这两个模型以及 `ImageSequenceOptions` 均支持完整的 JSON 往返转换与 `model_json_schema()`。它们不会向 Canvas/Deck 文档模型增加新字段，也不增加光栅格式枚举值。不会维护无休止增长的帧路径或时间戳列表。重复帧在每个规范镜头中仅编码一次，并作为独立的可编辑文件写入，而非硬链接。单帧内存占用保持受限；现有的场景准备及工作线程缓冲区依然会占用内存。

时序逻辑严格遵循动画导出规范，包括显式指定的幻灯片时长、`advance_after`、由旁白推导的视觉时序、转场及 Morph 变形。采用累积帧分配算法以防止小数值 hold 产生累积时间漂移；极短或零 hold 的静止幻灯片至少分配一帧。报告的持续时长精确等于 `frame_count / fps`，基于实际写入磁盘的文件计算得出。该数值可能与独立时间轴采样器的时长或采样点数量存在微小出入。`validate_export("image_sequence")` 与 `inspect_motion(target="image_sequence")` 使用视频动效能力集。现有的严格/减弱动效策略以及父级、Morph、字幕与工作线程限制依然适用。

图像序列为无声输出：不进行任何音频编码、混流、背景音乐或音频附带文件。旁白依然执行原有的文件校验与时长推断，但没有编码器的 64 个音频输入上限限制。仅含图片的场景无需安装 FFmpeg；推断旁白时长依然需要 ffprobe，且视频图层保留其常规的探测与解码要求。

所有图像帧与 `manifest.json` 在正式发布前均先渲染至原子化的临时暂存目录。目标目录必须为不存在的状态；若目标目录已存在，导出将安全报错退出，有效防止意外覆盖已有文件。

运行 `examples/image_sequence_overlay.py` 可生成无需 FFmpeg 依赖的 PNG、白底 JPEG 及无损 WebP 人名条底部图像序列。每次运行时这三个输出目录必须均为全新路径。

## 高质量动画图层合成 { #high-quality-animated-compositing }

`GifOptions(render_quality="high")` 与 `VideoOptions(render_quality="high")` 可开启 2 倍超采样图层合成表面，并在输出前执行一次高质量 LANCZOS 降采样。默认配置为 `render_quality="standard"`，保持原有的输出效果。该专属命名空间选项与用于控制 JPEG/WebP 压缩质量的 `render(..., quality=...)` 相互独立。字节导出方法同样接收命名关键字实参 `render_quality="high"`。

```python
canvas.render("smooth.mp4", animation=VideoOptions(fps=30, render_quality="high"))
deck.render("smooth.gif", animation=GifOptions(fps=12, colors=64, render_quality="high"))
```

高质量模式将预备图层与交错动效目标直接滤镜渲染至更大的超采样表面，而无需在内存中为每张源图片保留放大副本。它显著改善了旋转与缩放后边缘的平滑融合度；尺寸、时序、音频、GIF 调色板/尺寸控制以及 `workers` 参数含义保持不变。由于每帧及缓存的背景底板包含 4 倍像素量，高质量模式会消耗更多的渲染时间与内存。每个工作线程都会分配专属缓冲区，因此总内存占用会随工作线程数量增加而上升。

这是超采样的**图层合成**，而非更高分辨率的源排版布局：字体/资源以及依赖背景的源表面依然按原生尺寸准备。创作时指定的静态旋转已经烘焙进这些图层源中。字幕在降采样后以原生分辨率渲染，而幻灯片转场与带关键帧的 Morph 保持其现有的原生分辨率路径。高质量模式无法凭空还原源文件中缺失的细节，并且可能会使极小字号的文本略微变软。基准成本测量数据与排版文本裁剪对比图请参见[基准测试指南](https://github.com/sjquant/quickthumb/tree/main/benchmarks)。

## 多进程并行动画渲染 { #parallel-animated-rendering }

`GifOptions(workers=2)` 与 `VideoOptions(workers=2)` 可开启基于多进程的逐帧渲染。动画字节导出方法同样提供相同的命名关键字实参 `workers`。`workers` 必须为 1 至 8 的严格整数；默认为 1，不会根据 CPU 核心数自动扩张。对于小尺寸或静态导出，使用单工作线程可能更快，因为启动多进程、准备幻灯片及复制帧数据均存在时间开销。最终的编码与音频混音仍在父级导出进程中执行。

请编写可导入的独立脚本并使用 Python 的 `if __name__ == "__main__":` 保护：工作线程始终使用 `spawn` 方式启动（包括在 Linux 上），且不改变全局的默认启动方式。无法导入主模块的交互式环境（如 REPL）中应保持 `workers=1`。

```python
from quickthumb import Canvas, Fade, VideoOptions

def main():
    canvas = Canvas(640, 360).background(color="#123456")
    canvas.shape("rectangle", (40, 40), 200, 160, "#FF3355",
                 animation=Fade(duration=2))
    canvas.render("parallel.mp4", animation=VideoOptions(fps=30, workers=2))

if __name__ == "__main__":
    main()
```

各工作线程会使用独立的字体实例与视频解码器重新构建内置画布。系统仅在内存中维护有限且保序的待处理帧作业滑动窗口，完好保留原有的镜头时长、折叠停留时间、字幕边界及转场顺序。本地视频图层、字幕、带随机种子的噪点微粒以及内置动效均可并行处理。自定义/插件图层、Canvas 子类、远程视频源以及无随机种子的非零噪点要求必须使用 `workers=1`。幻灯片准备阶段解析的远程图片与字体会被固定提供给各工作线程；导出期间请保持本地资源和字体缓存文件不变。图层源或工作线程异常会导致导出失败，并完整保留预先存在的目标文件。

更多的工作线程需要更多的内存：除传输中的当前 RGB 帧外，每个工作线程均拥有独立的 Python 运行时、字体、准备好的幻灯片图像及解码器缓存。正常完成与捕获错误均会等待正在运行的作业完成并安全关闭其解码器。遇到错误时未开始的作业会被取消；异常退出的工作线程将作为渲染错误进行报告。操作系统级别的强杀操作（SIGKILL）无法触发正常清理流程。
