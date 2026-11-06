---
description: quickthumb 的 SVG、HTML、PowerPoint 与 PDF 导出功能参考。
---

# SVG、HTML、PowerPoint 与 PDF { #svg-html-powerpoint-and-pdf }

[导出参考](../exports.md) · [输出格式选择指南](../output-guide.md)

## SVG { #svg }

```python
svg = canvas.to_svg()
svg = canvas.to_svg(embed_fonts=True)
```

默认情况下，SVG 通过字体家族名称引用字体（`font-family="Roboto"`），这能保持极小的文件体积，但要求查看端设备已安装相应字体。设置 `embed_fonts=True` 后，所用到的字体文件将以内联 `@font-face` 数据 URL 的形式嵌入，确保文本在任何地方呈现效果完全一致。

!!! note "查看器兼容性"
    投影和发光效果使用 SVG 滤镜（`feGaussianBlur`）。现代浏览器均能忠实渲染；某些极简 SVG 光栅化工具可能仅支持部分滤镜效果。

## HTML { #html }

```python
html = canvas.to_html()
canvas.render("card.html")
```

导出结果为一个完全自包含的单一 HTML 文件。背景、形状、外边框与文本转换为标准 HTML 和 CSS；图像以及其他没有 CSS 等效表现的内容将嵌入为 PNG 切片。与 SVG、PDF 和 PPTX 不同，该网页支持播放图层 `animation` 动效，并通过点击向前推进。

画面设计采用固定尺寸的舞台，绝不发生重排。默认情况下（`responsive=True`），整个舞台会自动缩放以适配浏览器窗口；传入 `responsive=False` 可获得精确的原始像素尺寸。默认会嵌入字体（`embed_fonts=True`），因此页面在任何设备上呈现均完全一致。

Deck 以相同方式导出为带有演讲者视图的 HTML 幻灯片放映，详情请参见 [Deck](../api/deck.md)。

## PPTX { #pptx }

生成可在 PowerPoint 或 Keynote 中进一步二次精修的幻灯片，带有可编辑的文本与受支持的形状。首先安装 `pptx` 可选依赖：

```bash
pip install "quickthumb[pptx]"
```

```python
from quickthumb import Canvas

canvas = Canvas(640, 360).background(color="#101826").text(
    "Ready to share", font="Arial", size=36, color="#FFFFFF", position=(60, 120)
)
canvas.export("promo.pptx")
```

在幻灯片编辑器中打开 `promo.pptx`。单个 Canvas 对应单张幻灯片；如需导出多张幻灯片，请使用 `deck.export("promo.pptx")`。

!!! note "编辑带样式的元素"
    发光效果保存为固定图片，外边框可能由独立对象组合而成。修改带样式的文本或形状后，请重新从 Python 导出，以保持发光和边框完全对齐。某些复杂效果组合会被整体转为图片，因此受影响的内容无法作为单独的文字或形状进行编辑。详情请参见 [PPTX 兼容性](export-validation.md#pptx-compatibility)。

!!! note "字体与排版"
    PPTX 默认不嵌入字体。请选用 quickthumb 和幻灯片编辑器中均可用的字体。字体回退替换、不同字号的富文本混合以及旋转可能会微调间距或布局；请务必在最终使用的软件中实际查看最终效果。

## PDF { #pdf }

PDF 导出需要安装 `pdf` 可选依赖：

```bash
pip install "quickthumb[pdf]"
```

画布转换为单个 PDF 页面，尺寸与画布像素严格对应（每个像素对应 1 个点）。背景、外边框、形状以及符合条件的文本均使用与光栅渲染器相同的布局计算直接绘制为原生 PDF 矢量图元。可以安全嵌入且无需复杂塑形的文本所用字体会被子集化内嵌；不支持的文本则嵌入为像素完全一致的 PNG 切片，以确保最终视觉呈现绝对忠实。

```python
canvas.render("promo.pdf")
# or
with open("promo.pdf", "wb") as f:
    f.write(canvas.to_pdf())
```

!!! note "保真度说明"
    PDF 底纹（shading）无法表达透明度，因此半透明渐变（以及带有半透明色标的渐变）将嵌入为图片。模糊效果（投影、发光）、形状上的复杂描边以及渐变/图像文本字形填充均缺乏忠实的原生 PDF 矢量形式，同样会嵌入为像素级精确的 PNG 切片。
