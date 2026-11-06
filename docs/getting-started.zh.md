---
description: 基于同一份可复用的 Python 版式渲染三张节目卡片，随后修改内容制作属于你自己的卡片。
---

# 渲染第一组卡片 { #render-your-first-cards }

先搭建一个节目卡片版式，并用三组不同内容分别渲染。
接着修改标题，制作出属于你自己的版本。

<div class="qt-gallery" markdown>
![第 12 期：“Ship your first release”，橙色色带上带有巨大的数字 12](assets/home/episode-12.png)

![第 13 期：“Make room for better work”，黄色色带上带有巨大的数字 13](assets/home/episode-13.png)

![第 14 期：“Build less. Finish more.”，蓝色色带上带有巨大的数字 14](assets/home/episode-14.png)
</div>

## 1. 安装 quickthumb { #1-install-quickthumb }

你需要 **Python 3.11 或更高版本**。在你的 Python 环境中执行：

```bash
python -m pip install quickthumb
```

如果需要先创建独立环境，请参考[安装](installation.md#isolated-environment)，配置完成后再返回此处。
本示例仅使用基础包及其内置字体：安装后无需下载字体、图片或可选渲染器。

## 2. 保存并运行版式代码 { #2-save-and-run-the-layout }

在 quickthumb 源码仓库之外的工作目录中，将以下代码保存为 `episode_cards.py`：

```python
--8<-- "examples/episode_cards.py"
```

在同一目录下运行该脚本：

```bash
python episode_cards.py
```

打开同目录下的 `episode-12.png`、`episode-13.png` 和 `episode-14.png`。
每张图片尺寸均为 1280 × 720。脚本每次运行时都会写入这些文件名，并覆盖同名旧文件。

## 3. 制作下一张卡片 { #3-make-the-next-card }

保持函数不变，在 `episodes` 列表中再追加一行：

```python
(15, "Your next big idea", "#FF4B1F"),
```

再次运行脚本并打开 `episode-15.png`。你已成功复用同一个版式，生成了新的期数、标题和强调色。

标题会在 `max_width` 限制内自动换行。`auto_scale=True` 允许文字自动缩小以适应指定的宽度和高度。批量生成卡片前，建议先用实际可能出现的最长标题测试排版效果。

## 调整设计 { #adapt-the-design }

在 `episode_card()` 函数内修改颜色、数字或标题字号以及位置，即可一次性更新所有卡片。图层会严格按照添加顺序依次绘制。
如果想使用自己的字体，可以在每次 `.text()` 调用中传入本地字体路径，例如 `font="/path/to/your-font.ttf"`；如果字体本身字重足够，也可以移除 `Stroke` 描边效果。

扩展版式时，可使用 `canvas.diagnose()` 检查常见问题，如超出画布的图层或对比度过低。本示例故意裁切了数字，因此会报告一项 `off-canvas` 结果。有关检查项及其局限，请参阅[诊断](diagnostics.md)；诊断无告警并不等同于设计视觉效果出众。

## 选择后续方向 { #choose-your-next-step }

- [示例集](cookbook/index.md)：参考缩略图、社交卡片或播客版式。
- [核心概念](concepts.md)：理解图层、效果与定位。
- [自动布局](api/group.md)：在行和列中组织动态内容。
- [JSON 与 AI 工作流](json-schema.md)：以 JSON 形式加载和校验版式。
- [选择输出格式](output-guide.md)：制作图像、演示文稿和动画。
- [API 参考](api/index.md)：查阅类与参数。
