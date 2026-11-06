---
description: 带有父级链接的场景与复杂布局的检查行为及边界框度量参考。
---

# 检查复杂布局 { #inspecting-complex-layouts }

标准检查 API 请参见 [Canvas 检查](../api/canvas.md#inspect) 与 [文档检查](../api/inspection.md)。

## 带有父级链接的场景 { #parent-linked-scenes }

在检查带有父级链接的层级结构或执行 `canvas.diagnose()` 时：

- **创作时的静态边界**：图层边界框描述的是世界坐标系下的静态布局坐标。
- **Null 控制器**：Null 控制器图层（`Canvas.null()`）作为不可见的几何变换枢轴点存在，不会产生可视边界框。
- **可视化调试叠加层**：使用 `canvas.render("debug.png", debug=True)` 可视化查看为每个图层测量的精确边界框。

## 编组与裁剪边界 { #groups-and-clipped-boundaries }

- **编组边界框**：编组测得的边界框包络其所有子图层，同时综合计算图层间距、内边距以及附加的任何裁剪框或遮罩。
- **嵌套裁剪与遮罩**：作用于父编组或后代图层的裁剪框与遮罩会在不改变相对布局坐标的前提下约束其可视区域。
- **动态计数器**：内置计数器文本图层（`Canvas.counter()`）基于其最终定型值计算边界框，确保在整个动效播放期间整体布局保持绝对稳定。
