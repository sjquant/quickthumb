---
description: 确定性柱状图、折线图及二维码图层参考文档。
---

# 数据可视化 { #data-visualizations }

quickthumb 包含精简、确定性的图表图层与二维码图层，适用于仪表盘、卡片和自动生成的社交媒体配图。柱状图与折线图共用 `ChartData`，同时各自拥有专注的样式模型；它们经过专门设计，并非用于替代通用的数据绘图库。

```python
from quickthumb import (
    BarChartSpec,
    BarChartStyle,
    Canvas,
    LineChartSpec,
    LineChartStyle,
)

canvas = (
    Canvas(800, 400)
    .chart(
        spec=BarChartSpec(
            data=[-4, 8, 12, 6],
            style=BarChartStyle(color="#2563EB", negative_color="#DC2626"),
        ),
        position=(40, 40),
        width=220,
        height=120,
    )
    .chart(
        spec=LineChartSpec(
            data=[2, 5, 3, 7],
            style=LineChartStyle(color="#7C3AED", fill="#DDD6FE"),
        ),
        position=(40, 200),
        width=440,
        height=120,
    )
    .qr_code("https://example.com", position=(620, 40), size=140)
)
```

## 通用图表数据与样式 { #shared-chart-data-and-style }

当生成的规范需要显式命名的结构化数据对象时，`ChartData(values=[...])` 非常实用；构建器与 JSON 同样支持直接传入普通的纯数字列表。空序列、常数序列以及负数序列均为合法输入。数值必须为有限实数，传入 `NaN`、无穷大或非数字类型将抛出 `ValidationError`。

`BarChartStyle` 支持 `color`、`padding`、`opacity`、`negative_color` 与 `bar_gap`。
`LineChartStyle` 支持 `color`、`padding`、`opacity`、`fill`、`fill_opacity`、`stroke_width`、`point_radius` 与 `show_points`。
为所选图表类型传入不适用的无效选项会立即抛出 `ValidationError`，而非静默忽略。配置完成的规范直接传入统一的 `.chart()` 构建方法。

折线图的数值会自动按比例缩放适配绘图区域。常数序列居中显示在垂直中线。柱状图的取值范围始终包含零基准线，因此正值和负值会分别绘制在基准线的上下两侧。空数据序列不会绘制任何像素。

## 图层构建方法 { #layer-builders }

| 构建器 | JSON 类型 | 用途 |
| --- | --- | --- |
| `.chart(spec, position, width, height)` | `chart` / `bar` | 传入 `BarChartSpec` 时，绘制包含零基准线的垂直柱状图 |
| `.chart(spec, position, width, height)` | `chart` / `line` | 传入 `LineChartSpec` 时，默认绘制带有点标记的折线图 |
| `.qr_code(data, position, size)` | `qr_code` | 绘制包含明确容错级别与安全边距的正方形二维码 |

在 JSON 中，图层在 `"spec"` 字段下存储带类型判别的图表规范（例如 `{ "type": "bar", "data": [1, -2] }`）。

图表构建器支持像素或百分比定位、`align`、`opacity` 以及既有的 `clip` 裁切与 `mask` 蒙版合成原语。图表图层还可以直接作为 Group 分组的子元素使用，容器会自动为其计算排版。二维码支持配置 `foreground`、`background`、`error_correction`（`L`、`M`、`Q` 或 `H`）以及 `quiet_zone`。当请求的正方形尺寸过小无法完整容纳生成的二维码模块矩阵时，二维码渲染会抛出 `RenderingError`。图表与二维码图层同样支持既有的图层级 `animation` 动效契约，用于 PPTX 及 GIF/视频导出；省略动画参数时保持确定性的静态渲染。

图表与二维码图层可通过 `Canvas.to_json()` 序列化，通过 `Canvas.from_json()` 校验，并在 `quickthumb schema` 中完整呈现。SVG、HTML、PDF 和 PPTX 导出通过标准的像素级精确栅格降级方案保留其外观呈现。
