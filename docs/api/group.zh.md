---
description: quickthumb 分组图层参考文档：支持间隙（gap）、内边距（padding）、交叉轴对齐及嵌套的行与列自动布局。
---

# 分组（自动布局） { #group-auto-layout }

`.group()` 添加自动布局容器，它自动测量子图层的尺寸并将它们沿行或列方向依次排列，无需手动计算每个子图层的绝对坐标。由于分组根据各子图层的自然尺寸动态计算布局位置，因此在标题文字变长或新增徽章时，同一份规范依然能够优雅工作。这使得分组格外适合大语言模型（LLM）生成的排版场景。

## 函数签名 { #signature }

```python
canvas.group(
    children,
    direction="column",
    gap=0,
    padding=0,
    position=None,
    align=None,
    item_align="start",
)
```

## 参数说明 { #parameters }

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `children` | `list` | **必填** | 堆叠顺序的子图层列表。支持字典或类型为 `text`、`image`、`shape`、`svg`、`chart`、`qr_code` 及嵌套 `group` 的图层模型。 |
| `direction` | `str` | `"column"` | 主轴排列方向：`"column"` 从上到下垂直堆叠，`"row"` 从左到右水平排列。 |
| `gap` | `int` | `0` | 主轴方向上相邻子图层之间的像素间隙。非负整数。 |
| `padding` | `int \| tuple` | `0` | 容器内边距：单个整数表示四边统一，`(vertical, horizontal)` 或 `(top, right, bottom, left)`。 |
| `position` | `tuple \| None` | `None` | 分组边界框的锚点位置，支持像素数值或百分比字符串。 |
| `align` | `str \| Align \| tuple \| None` | `None` | `position` 对应分组边界框的哪个基准点，机制与图像图层一致。详见 [Align](enums.md#align)。 |
| `item_align` | `str` | `"start"` | 各子图层在交叉轴方向上的对齐方式：`"start"`、`"center"` 或 `"end"`。 |

!!! warning "子图层绝不能设置 `position`"
    分组容器负责为其子图层分配位置。若子图层自行设置了 `position`，将抛出 `ValidationError`；子图层设置的 `align` 也会被忽略，请改用分组容器上的 `item_align`。

## 使用示例 { #examples }

### 垂直堆叠的标题块 { #stacked-headline-block }

```python
canvas = Canvas(1280, 720).background(color="#16213E").group(
    children=[
        {"type": "shape", "shape": "pill", "width": 120, "height": 36, "color": "#E94560"},
        {"type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900},
        {"type": "text", "content": "No coordinates were harmed", "size": 40, "color": "#A2A8D3"},
    ],
    direction="column",
    gap=24,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

### 水平徽章行 { #horizontal-badge-row }

```python
def chip(label):
    return {
        "type": "text",
        "content": label,
        "size": 24,
        "color": "#22D3EE",
        "weight": 700,
        "effects": [
            {"type": "background", "color": "#1D2547", "padding": [8, 14], "border_radius": 18},
        ],
    }

canvas.group(
    children=[chip("GROUPS"), chip("TOKENS"), chip("LINT")],
    direction="row",
    gap=14,
    position=("50%", "88%"),
    align=("center", "middle"),
)
```

### 嵌套分组 { #nested-groups }

分组支持嵌套，因此列容器内可以包含行容器（反之亦然）：

```python
canvas.group(
    children=[
        {"type": "text", "content": "RELEASE 0.5", "size": 96, "color": "#FFFFFF", "weight": 900},
        {
            "type": "group",
            "direction": "row",
            "gap": 14,
            "children": [chip("GROUPS"), chip("TOKENS"), chip("LINT")],
        },
    ],
    direction="column",
    gap=28,
    position=("7%", "50%"),
    align=("left", "middle"),
)
```

### 交叉轴对齐 { #cross-axis-alignment }

```python
canvas.group(
    children=[
        {"type": "text", "content": "CENTERED", "size": 80, "color": "#FFFFFF", "weight": 900},
        {"type": "text", "content": "Both children share a center line", "size": 36, "color": "#A2A8D3"},
    ],
    direction="column",
    gap=18,
    item_align="center",            # cross-axis: center each child horizontally
    position=("50%", "50%"),
    align=("center", "middle"),
)
```

## 尺寸计算原理 { #how-sizing-works }

1. 首先测量每个子图层的自然尺寸（文本边界、图像原始宽高、形状声明的 `width`/`height`）。
2. 将子图层沿主轴方向依次排列，相邻元素间保留 `gap` 间隙。
3. 分组总边界框为所有子图层的并集范围加上内边距 `padding`。
4. 整个边界框根据 `align` 对齐方式定位到画布的 `position` 坐标上。

## JSON 表现形式 { #json-form }

分组支持与其他普通图层完全一致的序列化机制。完整 Schema 详见 [JSON Schema 页面](../json-schema.md#group-layer)：

```json
{
  "type": "group",
  "direction": "column",
  "gap": 24,
  "position": ["8%", "50%"],
  "align": ["left", "middle"],
  "item_align": "start",
  "children": [
    { "type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900 }
  ]
}
```

## 校验规则 { #validation-rules }

- `children` 必须为非空列表。
- 子图层绝不能设置 `position`（由分组容器统一分配坐标）。
- 有效的子图层类型：`text`、`image`、`shape`、`svg`、`chart`、`qr_code` 以及嵌套的 `group`。
- `gap` 不能为负数；`padding` 的数值不能为负数，且内边距元组必须包含 2 个或 4 个元素。
