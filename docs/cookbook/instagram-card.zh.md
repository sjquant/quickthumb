---
description: 使用 quickthumb 构建的 1080×1080 Instagram 突发新闻卡片，并附带实际渲染所用的完整脚本。
---

# Instagram 卡片 { #instagram-card }

![正方形突发新闻卡片，火焰照片上方带有“Wildfires Spread Across 18,000 Acres”标题](../assets/examples/instagram_news_card.png)

正方形新闻卡片：底图照片、红色标签、衬线体主标题和新闻来源信息行。

安装 [uv](https://docs.astral.sh/uv/) 并克隆代码仓库即可运行此示例：

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/instagram_news_card.py
```

该脚本将写入 `examples/instagram_news_card.png`，并覆盖同名旧文件。

## 构成方式 { #how-its-built }

- **标签采用带有 `Background` 效果的文本。** `Background(color="#CC0000", padding=(11, 22))` 围绕“BREAKING NEWS”绘制红底边框，使其随文本长度自适应拉伸，而无需手动调整独立形状的尺寸。
- **标题使用有别于正文的独特字体。** `font="NotoSerif"` 从内置字体目录加载衬线体；其余图层均使用默认的 Roboto 字体。
- **红色装饰条是一个 9px 宽的矩形。** 作为一个独立的形状，其位置和高度（176px）经过手动调整以精准匹配两行标题文字。
- **新闻来源信息为单个文本图层。** 通过两个 `TextPart` 分别赋予“WORLD NEWS”与日期不同的颜色和字重。
- **大多数坐标使用百分比定位。** 例如 `("8%", "92%")`，以便随画布尺寸自适应缩放。红色装饰条属于特例：使用像素坐标以便与标题文字精确对齐。

## 代码 { #code }

```python
--8<-- "examples/instagram_news_card.py"
```
