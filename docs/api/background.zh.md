---
description: quickthumb 背景图层参考文档，涵盖纯色、渐变、背景图片、不透明度、效果及渲染层叠顺序。
---

# 背景 { #background }

`.background()` 添加覆盖全画布的背景图层。多次调用该方法时，图层将按调用顺序依次从底层向顶层堆叠。

## 函数签名 { #signature }

```python
canvas.background(
    color=None,
    gradient=None,
    image=None,
    opacity=1.0,
    blend_mode=None,
    fit=None,
    effects=None,
)
```

## 参数说明 { #parameters }

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `color` | `str \| tuple \| None` | `None` | 纯色填充。十六进制颜色字符串（`"#RRGGBB"` 或 `"#RRGGBBAA"`）或 RGB/RGBA 元组。 |
| `gradient` | `LinearGradient \| RadialGradient \| None` | `None` | 渐变填充。详见[枚举与渐变](enums.md)。 |
| `image` | `str \| None` | `None` | 本地文件路径或远程网络 URL。 |
| `opacity` | `float` | `1.0` | 图层不透明度，取值范围为 `0.0`（完全透明）到 `1.0`（完全不透明）。 |
| `blend_mode` | `str \| BlendMode \| None` | `None` | 该图层与下方已有图层的混合模式。详见 [BlendMode](enums.md#blendmode)。 |
| `fit` | `str \| FitMode \| None` | `None` | 图片填充画布的适配方式。详见 [FitMode](enums.md#fitmode)。 |
| `effects` | `list \| None` | `[]` | 背景效果列表。支持 `Filter` 和 `Grain`。 |

## 使用示例 { #examples }

### 纯色填充 { #solid-color }

```python
canvas.background(color="#0F172A")
```

### 渐变叠加 { #gradient-overlay }

```python
from quickthumb import LinearGradient

canvas.background(
    gradient=LinearGradient(
        angle=120,
        stops=[("#111827", 0.0), ("#11182700", 1.0)],
    ),
    opacity=0.7,
)
```

### 带有效果的远程网络图片 { #remote-image-with-effects }

```python
from quickthumb import Filter

canvas.background(
    image="https://images.unsplash.com/photo-1516321318423-f06f85e504b3",
    fit="cover",
    blend_mode="multiply",
    effects=[Filter(blur=4, brightness=0.75, contrast=1.1, saturation=0.9)],
)
```

### 半透明黑色压暗遮罩 { #dark-overlay }

```python
canvas.background(color="#000000", opacity=0.4)
```

## 注意事项 { #notes }

- 背景图层始终完整覆盖整张画布。
- 在单个背景图层中，`color`、`gradient` 与 `image` 既可以独立使用，也可以组合叠加。
- `blend_mode` 在该图层与下方已有图层合成时生效。
- `image` 均支持本地绝对/相对文件路径及远程 `http(s)` URL。
- 可用效果的完整参数请参阅 [Filter](effects.md#filter) 和 [Grain](effects.md#grain)。
