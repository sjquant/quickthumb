---
description: 使用带有主题变量与自动布局分组的 JSON 规范渲染 1280×720 发布卡片，并附带生成该卡片的完整规范定义。
---

# 发布公告（自动布局） { #launch-announcement-auto-layout }

![发布卡片文案为“Layouts that build themselves.”，右侧带有蓝色圆形图案](../assets/examples/launch_announcement.png)

一款无需手动测量绝对坐标的发布卡片。标题列与特性行均采用自动布局分组，所有颜色与字体尺寸均提取至 `theme` 块中统一定义，因此修改文案或品牌视觉时无需重新计算任何排版位置。

安装 [uv](https://docs.astral.sh/uv/) 并克隆代码仓库即可运行此示例：

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run --extra svg python examples/launch_announcement.py
```

该脚本将写入 `examples/launch_announcement.png`，并覆盖同名旧文件。

其中的星芒装饰为 SVG 文件，因此需要安装 `svg` 额外依赖。

## 构成方式 { #how-its-built }

- **主题设计变量（Tokens）。** 颜色和尺寸在 `theme` 下统一定义一次，并通过 `"$theme.colors.blue"` 或 `"$theme.sizes.title"` 引用。当整个属性值完全由变量构成时，会保留原始 JSON 数据类型，因此 `"$theme.sizes.title"` 会被解析为数字 `116`，而非字符串。
- **文本使用列式分组。** 版本标签、主标题和副标题作为同一个 `group` 的子图层，设置 `"direction": "column"` 与 `"gap": 22`。仅需将整个容器定位一次（`["7%", "44%"]`），子元素无需指定 `position`。即便副标题增加一行文本，整个列也会自动重新流动排版。
- **特性清单使用行式分组。** 从“01 GROUPS”到“04 DIAGNOSTICS”是第二个分组，设置 `"direction": "row"`，因此即便修改其中某项的名称，它们之间的间距也能保持严格均匀。
- **使用基础形状构建图形元素。** 圆形、四个色条和星形分别使用常规的 `ellipse`、`rectangle` 和 `star` 形状。星芒装饰引用 `assets/images/spark.svg`，并通过 `Filter(saturation=0, brightness=3)` 滤镜将其调白。
- **渲染前自动诊断。** 脚本在执行渲染前调用 `canvas.diagnose()` 并打印所有检测结果。在终端中也可通过 `uv run --extra cli quickthumb lint examples/launch_announcement.json` 执行相同的静态排版检查。

## 规范定义 { #the-spec }

```json
--8<-- "examples/launch_announcement.json"
```

## 脚本代码 { #the-script }

```python
--8<-- "examples/launch_announcement.py"
```
