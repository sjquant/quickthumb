---
description: quickthumb 外边框图层参考，支持配置宽度、颜色、不透明度与内缩距离来绘制画布边框。
---

# 外边框 { #outline }

`.outline()` 用于沿整个画布边缘绘制边框。通常作为最后一个图层添加，以确保覆盖在所有内容之上。

## 方法签名 { #signature }

```python
canvas.outline(
    width,
    color,
    offset=0,
    opacity=1.0,
)
```

## 参数 { #parameters }

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `width` | `int` | **必填** | 边框粗细（像素）。正整数。 |
| `color` | `str` | **必填** | 边框颜色。十六进制字符串（`"#RRGGBB"` 或 `"#RRGGBBAA"`）。 |
| `offset` | `int` | `0` | 距离画布边缘向内缩进的像素距离。非负整数。 |
| `opacity` | `float` | `1.0` | 图层不透明度，范围为 `0.0` 至 `1.0`。 |

## 示例 { #examples }

### 基础外边框 { #basic-outline }

```python
canvas.outline(width=12, color="#B8FF00")
```

### 内缩外边框 { #inset-outline }

```python
# Drawn 8px inside the canvas edge
canvas.outline(width=4, color="#FFFFFF", offset=8)
```

### 半透明外边框 { #semi-transparent-outline }

```python
canvas.outline(width=8, color="#FFFFFF", opacity=0.5)
```

### 完整构图中的典型用法 { #typical-usage-in-a-full-composition }

```python
canvas = (
    Canvas(1280, 720)
    .background(color="#0F172A")
    .text(content="TITLE", size=96, color="#FFFFFF", align="center")
    .outline(width=12, color="#22d3ee")  # always last
)
```

## 说明 { #notes }

- 边框默认从画布边缘向内绘制（`offset=0`）。
- 将较大的 `offset` 与较细的 `width` 结合使用，可以制作出悬浮画框效果。
- `opacity` 必须介于 `0.0` 至 `1.0` 之间。
