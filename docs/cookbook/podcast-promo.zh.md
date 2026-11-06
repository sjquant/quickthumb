---
description: 使用满版人像照片与从 URL 加载的网络字体，用 quickthumb 制作一张 1280×720 的播客单集宣传图。
---

# 播客宣传图 { #podcast-promo }

![播客访谈宣传图](../assets/examples/podcast_interview_promo.png)

单集卡片：包含节目名、单集标题和嘉宾信息，右侧填满嘉宾照片。

安装 [uv](https://docs.astral.sh/uv/) 并克隆代码仓库即可运行此示例：

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/podcast_interview_promo.py
```

该脚本将写入 `examples/podcast_interview_promo.png`，并覆盖同名旧文件。

首次运行时需要联网下载节目名称所需的网络字体，之后将自动使用本地缓存。

## 构成方式 { #how-its-built }

- **人像照片作为背景。** `.background(image=..., fit=FitMode.COVER)` 用照片铺满整个画布。无需抠图，自然也没有需要修整的抠图边缘。
- **渐变留出文字空间。** 带有四个停靠点的 `LinearGradient` 在文案后方呈现纯黑，在面部上方完全透明。移动中间的停靠点可调整渐变消失的位置。
- **节目名称使用网络字体。** `font=SHOW_FONT_URL` 指向 Google Fonts 上的 `.ttf` 文件。由于 URL 指向的文件本身已具有特定样式，因此 `weight`、`bold` 和 `italic` 对字体 URL 不生效。
- **仅使用一种点缀色。** 节目名称下方简短的红线是卡片上唯一的彩色元素；其余部分均为白色或灰色。

## 代码 { #code }

```python
--8<-- "examples/podcast_interview_promo.py"
```

若想在同一版式中使用抠图后的人像而非满版照片，请参阅[网络字体与背景移除](webfonts-rembg.md)。
