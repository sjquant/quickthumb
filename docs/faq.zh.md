---
description: quickthumb 常见问题解答，涵盖安装、文本、字体、图像、输出格式、JSON 规范以及错误排查。
---

# 常见问题 { #faq }

## 安装 { #installation }

### 支持哪些 Python 版本？ { #which-python-versions-are-supported }

Python 3.11 或更高版本。该软件包明确支持 3.11 和 3.12，且 CI 在 3.11 上运行。这包括背景移除功能（`rembg` 额外依赖）。

### 找不到 `quickthumb` 命令？ { #the-quickthumb-command-isnt-found }

命令行工具属于可选额外依赖：执行 `pip install "quickthumb[cli]"` 进行安装。[安装](installation.md)列出了所有可选依赖。

### 为什么 SVG 图层会抛出 `RenderingError`？ { #why-does-my-svg-layer-raise-renderingerror }

绘制 SVG 文件需要安装 `svg` 额外依赖：`pip install "quickthumb[svg]"`。
将画布导出*为* SVG 文件则无需此依赖。

## 画布与图层 { #canvas-and-layers }

### 渲染一个没有任何图层的画布会怎样？ { #what-happens-if-i-render-a-canvas-with-no-layers }

你会得到一张与画布尺寸相同的全透明图片。这不会报错。

### 为什么分组子元素会报错 "group children must not set position"？ { #why-does-a-group-child-raise-group-children-must-not-set-position }

分组（group）会自动为其子元素排版定位。请移除子元素上的 `position` 参数，转为设置分组本身的定位：

```python
canvas.group(
    children=[{"type": "text", "content": "TITLE", "size": 96, "color": "#FFFFFF"}],
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

子元素设置的 `align` 也会被忽略。请使用分组容器的 `item_align` 沿交叉轴对齐各个子元素。

### 如何在渲染前检查设计中潜在的问题？ { #how-do-i-check-a-design-for-problems-before-rendering }

调用 `canvas.diagnose()`，或者针对 JSON 规范运行 `quickthumb lint spec.json`。
它会报告字号过小、文字溢出画布、对比度不足、图层被遮挡等常见问题。详情参阅[诊断与 CLI](diagnostics.md)。

## 文字与字体 { #text-and-fonts }

### 文字跑出画布外面了怎么办？ { #my-text-runs-off-the-canvas }

设置 `max_width` 让文本自动换行：

```python
canvas.text(content="A longer title that needs two lines", size=72, color="#FFFFFF", max_width="60%")
```

也可以加上 `auto_scale=True`（配合 `max_width`、`max_height` 或两者），使文字在超出时自动缩小字号直到合适为止。

### 同时设置 `bold=True` 和 `weight=900` 时为什么报错？ { #i-set-boldtrue-and-weight900-and-got-an-error }

它们控制的是同一个属性，二选一即可。`weight` 能更精确地控制字重：
`TextPart(text="STRONG", weight=900)`。

### 如何使用 Google Fonts？ { #how-do-i-use-a-google-font }

指定字体名称并将 `font_source="google"`。字体在首次使用时会自动下载并缓存，`weight` 会自动匹配对应的字体文件：

```python
canvas.text(content="Hello", font="Inter", font_source="google", weight=800, size=72, color="#FFFFFF")
```

你也可以直接传入字体文件的 URL，或者通过环境变量 `QUICKTHUMB_FONT_DIR` 指向本地字体目录。参阅[网络字体与背景移除](cookbook/webfonts-rembg.md)。

## 图像 { #images }

### 可以使用网络 URL 图片吗？ { #can-i-use-images-from-a-url }

可以。`background(image=...)` 和 `image(path=...)` 均支持 `http(s)` URL。图片会在渲染期间下载并缓存。如需管理缓存，请参阅[远程资源与缓存](reference/export-assets.md#remote-assets-and-caching)。

### 如何抠除人像背后的背景？ { #how-do-i-remove-the-background-behind-a-person }

在图像图层上设置 `remove_background=True` 即可。该功能需要安装 `rembg` 额外依赖：

```python
canvas.image(path="portrait.jpg", position=("75%", "55%"), width=420, height=520, remove_background=True)
```

### `cover`、`contain` 和 `fill` 有什么区别？ { #whats-the-difference-between-cover-contain-and-fill }

`cover` 会填满指定区域，超出部分自动裁切；`contain` 会完整容纳整张图片，留出空白区域；`fill` 会忽略原始宽高比，直接拉伸图片填满区域。

## 输出 { #output }

### 支持导出哪些格式？ { #which-formats-can-i-export }

格式由传递给 `render()` 或 `export()` 的文件后缀名决定：

| 类别 | 格式 | 依赖要求 |
| --- | --- | --- |
| 图像 | PNG, JPEG, WebP | 无 |
| 矢量与文档 | SVG, PDF, PPTX | PDF 和 PPTX 需要 `pdf` / `pptx` 额外依赖 |
| Web | HTML | 无 |
| 动画 | GIF, MP4, WebM | MP4 和 WebM 需要 `ffmpeg` |

初次导出请参阅[选择输出格式](output-guide.md)；各格式支持保留和丢失的特性请参阅[导出参考](exports.md)。

### 可以为 PNG 设置 `quality` 参数吗？ { #can-i-set-quality-for-a-png }

不可以。`quality` 仅适用于 JPEG 和 WebP；为 PNG 传入该参数会抛出 `RenderingError`。

### 如何不写文件直接获取图像数据？ { #how-do-i-get-the-image-without-writing-a-file }

```python
png_base64 = canvas.to_base64(format="PNG")
jpeg_data_url = canvas.to_data_url(format="JPEG", quality=90)
```

## JSON { #json }

### 可以直接传 dict 给 `Canvas.from_json()` 吗？ { #can-i-pass-a-dict-to-canvasfrom_json }

不可以，它接收 JSON 字符串。请先使用 `json.dumps(data)` 进行转换。

### 为什么 `to_json()` 会抛出 `ValidationError`？ { #why-does-to_json-raise-validationerror }

说明画布中包含 `.custom(fn)` 图层。Python 函数无法序列化为 JSON，因此必须先移除该图层。

### 为什么执行 `to_json()` 后 `theme` 块消失了？ { #my-theme-block-disappeared-after-to_json }

规范加载时，主题变量（tokens）会被直接替换为实际解析后的数值，因此 `to_json()` 输出的是具体数值，不再包含 `theme` 块。如果想继续编辑主题变量，请保留原始规范文件。

## 错误排查 { #errors }

### 不同的错误类型分别代表什么含义？ { #what-do-the-different-errors-mean }

- `ValidationError`：参数或规范字段不合法。在添加图层或加载规范时立即抛出。
- `RenderingError`：绘图过程中发生异常，例如网络图片下载失败。
- `MissingAssetError`：规范中引用的本地文件不存在。

每个错误都包含 `details` 属性，提供稳定的错误代码、字段的 JSON 指针路径以及图层 ID。详情参阅[结构化错误](errors.md)。
