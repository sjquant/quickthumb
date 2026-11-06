---
description: 探索 quickthumb API 参考，涵盖 Canvas、图层、背景、文本、图像、形状、描边、效果、枚举以及渐变。
---

# API 参考 { #api-reference }

使用 `Canvas` 构建单个场景，使用 `Deck` 编排多个场景。两者实现了相同的文档级操作；各个图层文档详细说明了它们特有的创作字段。

## 受支持的公共接口 { #supported-public-surface }

从 `quickthumb` 导入文档中记载的创作类型与结果模型，从 `quickthumb.audio` 模块导入音频分析工具。某名称能够从其他内部模块被导入，并不代表它是受支持的公共入口点。

| 接口面 | 受支持的用法 |
| --- | --- |
| 创作构建 | `Canvas`、`Deck`、文档中记载的图层/效果模型、动效轨道、转场过渡与选项模型 |
| 文档操作 | 针对两类文档均支持 `validate()`、`inspect()`、`diagnose()`、`prefetch_assets()`、`sample()` 与 `export()`；为通用消费方提供 `inspect_document()` |
| 产物结果 | 强类型报告、`ExportResult`、`CanonicalFrame` / `FrameSequence` 以及 `ImageSequence*` 结果；可通过 `model_dump_json()` 进行序列化 |
| JSON 互转 | `to_json()`、`Canvas.from_json()`、`Deck.from_json()`、`canvas_json_schema()` 与 `document_json_schema()` |
| 音频响应创作 | [`quickthumb.audio.analyze_audio()` 与 `AudioAnalysis`](audio.md)；将源时钟起音（onset）时刻及基于 RMS 的振幅缩放融入数值动效中 |
| 专项输出 | 在其返回类型或控制机制适合当前任务时，使用文档中记载的 `render()`、`render_frame()`、`to_*()` 及 `export_image_sequence()` 方法 |

`export()` 是官方推荐的文件输出边界：它会预检功能策略，并返回已写入的文件路径及排版诊断。专用渲染方法有各自的返回值，且并不都会强制执行该策略；详见[输出 API](../reference/export-methods.md#recommended-output-api)。请在该边界处统一配置格式特定选项，避免直接调用底层导出器。

以 `_` 开头的模块、渲染器/上下文内部对象以及时间轴编译辅助类均为内部实现细节。它们可能在没有版本生命周期保证的前提下随时变更或移除。请使用 `sample()` 采样获取单帧画面，而不要自行拼装编译器与底层渲染器。各参考文档与生成的 Schema 描述了当前安装版本所支持的合法字段；“公开”并不等同于跨版本永久冻结不变。

### 统一文档工作流 { #one-document-workflow }

以下示例展示了在 Python、规范 JSON 以及 Deck 幻灯片之间流转相同的图层数据，无需接触底层渲染器对象或安装可选依赖：

```python
from quickthumb import Canvas, Deck, Document, ExportResult

canvas = Canvas(320, 180).background(color="#102030").shape(
    "rectangle", position=(24, 24), width=80, height=40, color="#42CEB7",
    id="badge", motion_key="brand", anchor=(0, 0),
)
restored = Canvas.from_json(canvas.to_json())
document: Document = Deck(slides=[restored])
result: ExportResult = document.export("slides.png")
print(result.written_paths)  # Numbered paths are reported by the result.
print(document.sample().frames[0].sha256)
```

## 通用图层术语体系 { #shared-layer-vocabulary }

Canvas 图层无论是放置在 Deck 幻灯片中还是序列化为规范 JSON，均采用相同的字段定义。Deck 仅负责扩充幻灯片顺序、转场、旁白和备注，绝不会重命名底层图层字段。Python 元组在 JSON 中对应为数组，枚举值对应为字符串，每个图层均包含一个 `type` 判别属性。

| 字段或概念 | 含义 |
| --- | --- |
| `id` | Canvas 场景内唯一的图层标识符（包含分组内的子图层）。每页 Deck 幻灯片拥有独立的 ID 命名空间。 |
| `motion_key` | 用于在 Morph 形状形变转场中跨场景匹配图层的可选键名；独立于场景内部的局部 `id`。 |
| `position`, `width`, `height` | 声明的排版位置与尺寸，在图层支持处可使用像素数值或百分比字符串。百分比相对于画布进行解析；必填字段与尺寸规则请参阅各图层参考。 |
| `align` | 图层边界框在 `position` 坐标点上的对齐基准点；同时控制文本排版的对齐方式。参阅 [Align](enums.md#align)。 |
| `rotation`, `anchor` | 旋转角度以度为单位。`anchor=(x, y)` 是规范动效中归一化在 0–1 范围内的旋转/缩放中心锚点，独立于排版对齐。静态旋转有自身的构图规则；参阅[变换锚点](video.md#transform-anchors-and-independent-scale)。 |
| `opacity` | 在支持的图层中表示 0 到 1 之间的不透明度。 |
| `animation` | 预设动效或包含类型化轨道与时间的 `AnimationSpec`。位置轨道是相对于设计排版位置的偏移量；缩放轨道变换外部对象，而 `ImageZoomTrack` 则在画框内缩放图片内容。 |
| Group（分组） | 自动布局容器负责为其子元素排版定位。请使用 `.group()` 构建行与列，避免手动计算各子元素坐标。 |
| `parent` / null | 针对顶层可动画图层的高级场景局部变换层级。子图层的位置相对于父级进行局部定位；百分比坐标依然相对于画布进行解析。这独立于分组布局机制。参阅[父级关联](video.md#parent-links-and-null-controllers)。 |

并非所有图层都支持全部字段。背景、描边、空控制器与常规可视绘制图层各自承担不同的职责。各个 API 参考文档以及 [JSON Schema](../json-schema.md#published-schema) 构成了字段级别的明确契约。[插件注册](../json-schema.md#plugin-layers)声明了扩展参数，并通过显式的 `PluginRegistry` 提供自定义渲染回调。仅解析 JSON 数据本身不会自动打包或安装这些外部代码。

## 文档列表 { #pages }

| 文档 | 涵盖内容 |
| --- | --- |
| [Canvas](canvas.md) | 画布实例化、全量图层方法、排版检查及文件导出方法 |
| [Deck](deck.md) | 将多个画布组合为单个 PDF、PPTX、HTML 幻灯片放映、视频或图像序列 |
| [文档检查](inspection.md) | `inspect_document()` 以及跨 Canvas/Deck 的通用采样分析 |
| [背景](background.md) | `.background()`：纯色、渐变与背景图片 |
| [文字](text.md) | `.text()` 与 `TextPart`：纯文本与富文本定制 |
| [图像](image.md) | `.image()`：图片放置、尺寸适配与抠图去背景 |
| [形状](shape.md) | `.shape()`：矩形、椭圆、胶囊形、三角形、星形及多边形 |
| [路径](path.md) | `.path()`：带填充与描边的 SVG 路径数据及受限动效 |
| [SVG](svg.md) | `.svg()`：来自 SVG 文件的图标与徽标矢量绘制 |
| [视频](video.md) | `.video()`：视频剪辑片段、外挂字幕与剪辑音频 |
| [分组（自动布局）](group.md) | `.group()`：行与列维度的自适应流式排版 |
| [描边](outline.md) | `.outline()`：围绕画布四周的描边边框 |
| [数据可视化](data-visualizations.md) | `.chart()` 与 `.qr_code()` 数据图表与二维码生成 |
| [效果](effects.md) | `Stroke`, `Shadow`, `Glow`, `Filter`, `Background`, `Grain`, `Duotone`, `InnerShadow`, `BackdropBlur` |
| [枚举与渐变](enums.md) | `Align`, `BlendMode`, `FitMode`, `LinearGradient`, `RadialGradient`, `TextFillImage` |

## 错误类型 { #error-types }

| 异常类 | 抛出时机 |
| --- | --- |
| `ValidationError` | 向图层构建方法传递非法参数时立即抛出。 |
| `RenderingError` | 在 `.render()`、`.to_base64()` 或 `.to_data_url()` 绘图导出期间发生底层故障时抛出。 |
