---
description: quickthumb SVG 图层参考，在渲染时按指定尺寸将图标与徽标光栅化，支持尺寸调整、对齐、混合模式与效果。
---

# SVG { #svg }

`.svg()` 用于添加 SVG 叠加图层并在渲染时进行光栅化。适用于需要在任何输出尺寸下均保持清晰锐利的图标、徽标以及矢量装饰元素。

!!! note "可选依赖"
    SVG 图层需要安装 `svg` 可选依赖（[cairosvg](https://cairosvg.org/)）：

    ```bash
    pip install "quickthumb[svg]"
    ```

    未安装此依赖直接渲染包含 `svg` 图层的画布将抛出 `RenderingError`。

## 方法签名 { #signature }

```python
canvas.svg(
    path,
    position,
    width=None,
    height=None,
    opacity=1.0,
    rotation=0.0,
    align=Align.TOP_LEFT,
    effects=None,
    blend_mode=None,
)
```

## 参数 { #parameters }

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `path` | `str` | **必填** | SVG 文档的本地文件路径或 URL。 |
| `position` | `tuple` | **必填** | `(x, y)` 坐标。取值可为整数（像素）或百分比字符串（`"50%"`）。 |
| `width` | `int \| None` | `None` | 输出光栅宽度（像素）。省略 `height` 时保持原始宽高比。 |
| `height` | `int \| None` | `None` | 输出光栅高度（像素）。省略 `width` 时保持原始宽高比。 |
| `opacity` | `float` | `1.0` | 图层不透明度，范围为 `0.0` 至 `1.0`。 |
| `rotation` | `float` | `0.0` | 旋转角度（度数）。 |
| `align` | `str \| Align \| tuple` | `Align.TOP_LEFT` | `position` 对应的图层对齐参考点。参见 [Align](enums.md#align)。 |
| `effects` | `list \| None` | `[]` | 与图像图层相同的效果列表：`Stroke`、`Shadow`、`Glow`、`Filter`。 |
| `blend_mode` | `str \| BlendMode \| None` | `None` | 叠加到下方图层时的混合模式。 |

SVG 会按请求的目标尺寸直接进行光栅化，而非从固定尺寸位图拉伸放大，因此即便是大尺寸渲染，徽标依然纤毫毕现。

## 示例 { #examples }

### 角落徽标 { #logo-in-a-corner }

```python
canvas.svg(
    path="logo.svg",
    position=("95%", "6%"),
    width=120,
    align=("right", "top"),
)
```

### 带旋转与透明度的装饰元素 { #decorative-element-with-rotation-and-opacity }

```python
canvas.svg(
    path="assets/images/spark.svg",
    position=("70%", "20%"),
    width=44,
    align=("center", "middle"),
    rotation=20,
    opacity=0.8,
)
```

### 带投影的远程 SVG { #remote-svg-with-a-shadow }

```python
from quickthumb import Shadow

canvas.svg(
    path="https://example.com/badge.svg",
    position=("50%", "85%"),
    width=200,
    align=("center", "middle"),
    effects=[Shadow(offset_x=0, offset_y=8, color="#000000", blur_radius=16)],
)
```

## 校验规则 { #validation-rules }

- `path` 和 `position` 为必填项。
- `position` 必须为包含 2 个元素的元组。百分比字符串必须符合 `-?N%` 格式。
- `opacity` 必须介于 `0.0` 至 `1.0` 之间。
- 在未安装 `quickthumb[svg]` 的情况下渲染会抛出 `RenderingError`。
