---
description: 在 quickthumb 中从 Google Fonts 或网络 URL 加载字体，并使用 remove_background 轻松抠除照片人像背景。
---

# 网络字体与背景移除 { #webfonts-background-removal }

## 字体 { #fonts }

文本图层的 `font` 属性支持指定字体家族名称或直接传入网络 URL。若要使用机器未安装的字体，可通过以下三种方式：

### 按名称使用 Google Fonts { #a-google-font-by-name }

设置 `font_source="google"`。quickthumb 会在首次使用时自动下载整个字体家族并缓存到本地，然后自动匹配对应的 `weight` 字重和 `italic` 斜体样式：

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720).background(color="#0A1730").text(
    content="Hello from Inter",
    font="Inter",
    font_source="google",
    weight=800,
    size=96,
    color="#FFFFFF",
    position=("50%", "50%"),
    align="center",
)
canvas.render("inter.png")
```

当你希望直接通过名称引用 Google Fonts 字体家族时，请使用此选项。

### 通过 URL 加载字体文件 { #a-font-file-by-url }

直接传入 `.ttf`、`.otf`、`.woff` 或 `.woff2` 文件的 URL。文件在初次下载后会自动缓存：

```python
SHOW_FONT_URL = "https://fonts.gstatic.com/s/dmserifdisplay/v17/-nFnOHM81r4j6k0gjAW3mujVU2B2K_c.ttf"

canvas.text(content="Signal to Noise", font=SHOW_FONT_URL, size=50, color="#F5F5F7")
```

由于 URL 精确指向单个具体文件，因此 `weight`、`bold` 和 `italic` 将被忽略。若同时需要粗体和常规体，可分别传入两个 URL（例如在不同 `TextPart` 中分别指定）。[播客宣传图](podcast-promo.md)示例即采用此方式加载其节目名称字体。

### 本地字体文件夹 { #a-local-font-folder }

通过环境变量 `QUICKTHUMB_FONT_DIR` 指向本地字体文件夹，即可直接按字体家族名称引用。`QUICKTHUMB_DEFAULT_FONT` 用于指定图层未配置 `font` 时使用的默认字体：

```python
import os

os.environ["QUICKTHUMB_FONT_DIR"] = "assets/fonts"
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

canvas.text(content="Hello", font="NotoSerif", weight=700, size=64, color="#FFFFFF")
```

示例集中的所有代码均采用此方式，直接使用代码仓库内置于 `assets/fonts` 目录下的字体文件。

## 背景移除（抠图） { #background-removal }

在图像图层上设置 `remove_background=True`，即可将主体从照片中精准抠出并剔除其余背景：

```python
from quickthumb import Canvas, Shadow

canvas = (
    Canvas(1280, 720)
    .background(color="#1C1C1E")
    .image(
        path="portrait.jpg",
        position=(1280, 720),
        width=620,
        height=710,
        fit="cover",
        align=("right", "bottom"),
        remove_background=True,
        effects=[Shadow(offset_x=-12, offset_y=12, color="#00000099", blur_radius=26)],
    )
)
```

`path` 同样支持 `http(s)` URL 网络图片。

该功能需要安装 `rembg` 额外依赖（支持 Python 3.11 或更高版本）：

```bash
pip install "quickthumb[rembg]"
```

首次调用时会自动下载主体分割模型（约 170 MB）并缓存至本地。

实用注意事项：

- **抠图优先处理。** quickthumb 会先去除背景，随后缩放处理结果，最后应用 `effects` 效果。因此 `Shadow` 投影会贴合人物轮廓边缘投射，而非原始的矩形边界框；`Filter` 滤镜会调整抠图后主体的色彩，但绝不影响分割抠图的轮廓判定。
- **人像抠图效果最佳。** 该模型主要针对人像照片进行了训练。与背景形成鲜明对比的主体能获得最干净利落的抠图边缘。
- **将主体固定至边界。** 配合使用 `position=(1280, 720)` 与 `align=("right", "bottom")`，无论人像实际尺寸多大，都能将其稳定固定在画面角落，正如[出镜人像](youtube-thumbnail.md#talking-head)与[反应 / 解说](youtube-thumbnail.md#reaction)缩略图所示。
