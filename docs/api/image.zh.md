---
description: quickthumb 图像图层参考，涵盖本地与远程图片、适配模式、定位、遮罩、效果以及背景去除。
---

# 图像 { #image }

`.image()` 用于在指定位置添加叠加图像。支持本地文件与远程 URL，并提供背景去除、适配模式、混合模式以及各类效果。

## 方法签名 { #signature }

```python
canvas.image(
    path,
    position,
    width=None,
    height=None,
    fit=None,
    opacity=1.0,
    rotation=0.0,
    align=Align.TOP_LEFT,
    remove_background=False,
    border_radius=0,
    blend_mode=None,
    effects=None,
)
```

## 参数 { #parameters }

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `path` | `str` | **必填** | 本地文件路径或远程 `http(s)://` URL。 |
| `position` | `tuple` | **必填** | `(x, y)` 坐标。取值可为整数（像素）或百分比字符串（`"50%"`）。 |
| `width` | `int \| None` | `None` | 目标宽度（像素）。若仅指定单侧尺寸，将保持原始宽高比。 |
| `height` | `int \| None` | `None` | 目标高度（像素）。若仅指定单侧尺寸，将保持原始宽高比。 |
| `fit` | `str \| FitMode \| None` | `None` | 同时指定 `width` 和 `height` 时的缩放模式。参见 [FitMode](enums.md#fitmode)。 |
| `opacity` | `float` | `1.0` | 图层不透明度，范围为 `0.0` 至 `1.0`。 |
| `rotation` | `float` | `0.0` | 旋转角度（度数）。 |
| `align` | `str \| Align \| tuple` | `Align.TOP_LEFT` | `position` 对应的图像对齐参考点。参见 [Align](enums.md#align)。 |
| `remove_background` | `bool` | `False` | 使用 AI 去除图像背景。需要安装 `quickthumb[rembg]`。 |
| `border_radius` | `int` | `0` | 圆角半径（像素）。非负整数。 |
| `blend_mode` | `str \| BlendMode \| None` | `None` | 图像合成混合模式。参见 [BlendMode](enums.md#blendmode)。 |
| `effects` | `list \| None` | `[]` | 效果列表：`Stroke`、`Shadow`、`Glow`、`Filter`、`Grain`。 |

## 示例 { #examples }

### 基础叠加图层 { #basic-overlay }

```python
canvas.image(
    path="portrait.png",
    position=("74%", "54%"),
    width=420,
    height=520,
    fit="cover",
    align=("center", "middle"),
)
```

### 配合效果使用 { #with-effects }

```python
from quickthumb import Filter, Shadow

canvas.image(
    path="portrait.png",
    position=("74%", "54%"),
    width=420,
    height=520,
    fit="cover",
    align=("center", "middle"),
    border_radius=28,
    effects=[
        Filter(contrast=1.1, saturation=1.05),
        Shadow(offset_x=0, offset_y=12, color="#000000", blur_radius=24),
    ],
)
```

### 去除背景 { #background-removal }

```python
canvas.image(
    path="portrait.jpg",
    position=("75%", "55%"),
    width=430,
    height=540,
    align=("center", "middle"),
    remove_background=True,
)
```

!!! note "说明"
    `remove_background=True` 需要 Python 3.11 或更高版本，并执行 `uv pip install "quickthumb[rembg]"`。首次使用时会自动下载并缓存 ONNX 模型（约 170 MB）。

### 远程图片 { #remote-image }

```python
canvas.image(
    path="https://example.com/avatar.png",
    position=("50%", "50%"),
    width=300,
    height=300,
    align=("center", "middle"),
    border_radius=150,  # circle
)
```

### 保持宽高比 { #preserve-aspect-ratio }

```python
# Only width: height keeps the image's proportions
canvas.image(path="logo.png", position=(40, 40), width=200)

# Only height: width keeps the image's proportions
canvas.image(path="logo.png", position=(40, 40), height=80)
```

## 适配模式 { #fit-modes }

当同时指定 `width` 和 `height` 时生效：

| 取值 | 行为 |
| --- | --- |
| `"cover"` | 填满容器，必要时裁剪超出部分 |
| `"contain"` | 完整容纳于容器内，边缘可能留白 |
| `"fill"` | 忽略原始比例，拉伸填满整个容器 |

## 校验规则 { #validation-rules }

- `path` 和 `position` 为必填项。
- `position` 必须为包含 2 个元素的元组。百分比字符串必须符合 `-?N%` 格式。
- `border_radius` 不能为负数。
- `opacity` 必须介于 `0.0` 至 `1.0` 之间。
- `path` 无效或远程下载失败时，将在渲染阶段抛出 `RenderingError`。
