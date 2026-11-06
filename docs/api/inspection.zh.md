---
description: 通过统一的 JSON 安全信封检查 Canvas 与 Deck 文档，无需针对文档类型分支即可将规范采样结果与页面布局关联。
---

# 文档检查与采样 { #document-inspection-and-sampling }

当工具或 Agent 需要同时处理 Canvas 和 Deck 文档时，请使用 `inspect_document()`。它将原有的布局、动效和诊断报告与观察到的资源清单合并封装在 `DocumentInspection` 信封中：

```python
from quickthumb import Canvas, Deck, inspect_document

document = Deck(slides=[Canvas(320, 180).background(color="#FFFFFF")])
report = inspect_document(document, target="video", fps=24, max_samples=100)
print(report.model_dump_json(indent=2))

for page_index, page in enumerate(report.pages):
    print(page_index, page.width, page.height, len(page.layers))
```

## 通用字段 { #common-fields }

| 字段 | 两种文档类型的通用含义 |
| --- | --- |
| `version` | 结果 Schema 版本，当前为 `"1"` |
| `kind` | 源文档判别字段：`"canvas"` 或 `"deck"` |
| `width`, `height` | 第一页的像素尺寸，与动画输出舞台尺寸一致 |
| `pages` | Canvas 对应单个 `CanvasInspection`，Deck 对应按文档顺序排列的所有幻灯片 |
| `motion` | 原有 `MotionInspection`，包含时序、属性采样状态、每页详情、功能支持行以及导出诊断 |
| `diagnostics` | 原有 `DiagnosticReport`；Deck 诊断项保留 `slide_index`（文档级诊断为 `null`） |
| `asset_manifest` | 观察到的资源引用、解析状态以及可用的唯一标识/哈希/缓存信息 |

每个页面均保留图层标识、顺序、嵌套子图层、边界框以及文本测量数据。不同尺寸的 Deck 页面保留各自的实际尺寸。最外层的尺寸取自第一页，即便 Deck 在创建时指定了不同的默认尺寸也是如此；原有的 `deck.inspect()` 仍会报告创建时指定的默认尺寸。

`target` 可接收单个导出器系列（`raster`、`html`、`pptx` 或 `video`）、系列的迭代器，或者传入 `None` 表示全部四个系列。`policy`、`fps` 和 `max_samples` 会原样传递给 `inspect_motion()`。动效观察数量受 `max_samples` 限制；采样得到的是属性状态而非光栅化帧。空 Deck 或无效选项会抛出原有的结构化 Quickthumb 错误。

该调用不会写入导出文件。与各个独立的检查/诊断方法类似，它可能会加载字体、解析资源或解码媒体以进行测量。清单反映的是这些操作完成后的状态；它不会主动发起额外的预取，也不会将尚未解析的资源认证为可用。如果需要显式解析资源，请使用 `prefetch_assets()`；若要确认运行环境就绪状态，请使用 `doctor`。

`canvas.inspect()` 和 `deck.inspect()` 保留原有的返回类型与 JSON 字段。若仅需要布局信息，请使用这些粒度更细的方法。

`DocumentInspection.model_json_schema()` 描述了此结果信封的结构。文档创作 Schema 仍用于描述输入规范，而非此检查结果。与 `DiagnosticReport` 类似，诊断项反序列化后为普通 JSON 对象；在 JSON 往返序列化后，请直接读取其 `code`、`severity`、`message` 及位置字段，而不是依赖 Python 诊断异常类。

## 将规范采样与布局关联 { #join-canonical-samples-to-layout }

两种文档类型的 `sample()` 方法均返回相同的 `FrameSequence`。其均匀的采样网格是一个观测时钟，并非编码后的帧索引；有关 GIF/视频量化和旁白差异的说明，请参见[动画时序](../timing.md)。页面索引从 0 开始，与 `frames[].slide` 及 `timeline[].slide` 一致：

```python
from quickthumb import DocumentInspection, FrameSequence

layout = DocumentInspection.model_validate_json(report.model_dump_json())
samples = FrameSequence.model_validate_json(document.sample().model_dump_json())
for frame in samples.frames:
    page = layout.pages[frame.slide]
    print(frame.index, frame.time, frame.width, frame.height, len(page.layers))
```

在此循环中无需针对文档类型编写分支逻辑。`kind` 仍可标识来源，且所有单页与单帧的详细信息均完整保留。

- `sample()` 为每页捕获一帧创作时的静态 RGBA 画面，保留各自的尺寸与透明度；此时 `time` 为 `None`，`duration` 为 0，`timeline` 为空列表
- `sample(time=[0, 0.5])` 或 `sample(fps=24)` 捕获动画时间轴，帧按时间顺序排列，使用第一页的舞台尺寸，并带有不透明底衬
- `frames[].index` 对观测帧进行排序，而 `frames[].slide` 标识当前活跃页面；时间轴分段描述了页面时序与过渡转场
- `environment` 记录渲染器版本信息；每帧携带原始 RGBA 数据和 SHA-256 摘要，以便在该环境中进行确定性比对

时间字段具有不同语义：`report.motion.duration` 保留原有的创作动效检查语义；`samples.duration` 则是规范捕获时长，包含其 `hold` 参数及已解析的旁白时长。例如，静态 Canvas 的动效时长为 0，但指定 `hold=2` 的定时采样时长为 2 秒。在比对播放行为时，请使用采样的 `duration`、`fps`、`timeline` 以及帧的 `time` 字段；切勿从布局报告或动效属性采样中推测这些值。
