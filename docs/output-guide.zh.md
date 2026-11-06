---
description: 选择适合的输出格式，使用 quickthumb 导出你的第一张图片、演示文稿或动画。
---

# 选择输出格式 { #choose-an-output-format }

使用同一个 Canvas 或 Deck，即可制作图片、演示文稿和动画。
根据你的使用场景选择合适的格式：

| 目标场景 | 推荐格式 | 所需环境 |
| --- | --- | --- |
| 发布图片 | PNG, JPEG 或 WebP | 基础包 |
| 在浏览器中演示幻灯片 | HTML | 基础包 |
| 在 PowerPoint 或 Keynote 中编辑幻灯片 | [PPTX](reference/export-documents.md#pptx) | `pptx` 额外依赖 |
| 分享便携文档 | PDF | `pdf` 额外依赖 |
| 分享短动效 | GIF | 基础包 |
| 发布视频 | MP4, WebM 或 MOV | FFmpeg；MOV 还需要 `prores_ks` 编码器 |
| 使用矢量素材 | SVG 或 Lottie | SVG 使用基础包；Lottie 仅支持 Canvas 的有限子集 |

## 导出图像 { #export-an-image }

文件后缀名决定了导出格式。以下示例需要 Python 3.11+ 并执行 `pip install quickthumb`：

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720).background(color="#155BD7").text(
    "Make an idea visible.", size=72, color="#FFFFFF", position=(80, 300)
)
result = canvas.export("image.png")
print(result.written_paths)
```

在当前工作目录下打开 `image.png`。再次导出将覆盖同名文件。
如需导出对应格式，使用 `.jpg` 或 `.webp` 后缀即可。若将 Deck 导出为图像格式，会依次写入带编号的各页幻灯片文件；`written_paths` 中包含生成的完整文件名列表。

## 制作幻灯片或动画 { #make-slides-or-animation }

参考[演示文稿与视频示例](cookbook/decks-and-video.md)，即可运行生成单张图片、双页 HTML 演示文稿以及 GIF 动图。若要导出为 PowerPoint 或 PDF，请先安装对应的[可选额外依赖](installation.md#optional-extras)。MP4 和 WebM 则需要单独安装 FFmpeg。

不同格式对效果或动画的还原度并不完全一致。PowerPoint 和 PDF 可能会退化为栅格图片降级显示，而 HTML 演示文稿不会播放 Deck 的旁白音频。请务必在目标应用中实际打开并验证效果。

关于格式特性支持、导出报告、高级选项及降级策略，请参阅[导出参考](exports.md)。
