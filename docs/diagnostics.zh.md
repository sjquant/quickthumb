---
description: 使用 canvas.diagnose() 排查排版与可读性缺陷，并通过 quickthumb CLI 进行规范的代码检查（lint）、渲染、文件监听、视觉比对及本地预览。
---

# 诊断与 CLI { #diagnostics-cli }

无需实际渲染文件，quickthumb 即可检测设计中常见的排版与可读性问题：在 Python 中可调用 `canvas.diagnose()`，在终端中可使用 `quickthumb lint`。

若要在 Python 中检查设计，可从下方的示例开始。对于 JSON 规范文件，可[安装 CLI 并运行 `quickthumb lint`](#quickthumb-lint)。使用 [`quickthumb doctor`](#quickthumb-doctor) 检查导出依赖，或使用 [`quickthumb render`](#quickthumb-render) 执行渲染输出。详细的规则定义与更多 CLI 命令见下文。

## `canvas.diagnose()` { #canvasdiagnose }

返回一个 `DiagnosticReport`，其 `findings` 列表包含多个 `Diagnostic` 检查项。列表为空表示未发现任何问题；但这并不等同于视觉效果良好，也无法捕捉所有主观设计瑕疵。建议务必人工核对渲染产物。

```python
from quickthumb import Canvas

with open("spec.json", encoding="utf-8") as f:
    canvas = Canvas.from_json(f.read())

for finding in canvas.diagnose().findings:
    print(finding.severity, finding.code, finding.message)
```

每个 `Diagnostic` 均包含稳定的人类可读字段，以及用于自动化流程的可选结构化字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | `str` | 诊断代码，取值为 `"off-canvas"`、`"tiny-text"`、`"text-overflow"`、`"text-clipped"`、`"missing-glyph"`、`"low-contrast"`、`"layer-overlap"`、`"layer-hidden"`、`"edge-crowding"`、`"near-alignment"`、`"caption-safe-area"`、`"caption-timing"`、`"caption-overlap"`、`"caption-reading-time"`、`"clip-stretch"` 或 `"motion-path-unused-handle"` |
| `severity` | `str` | `"warning"` 或 `"error"` |
| `layer_index` | `int` | 出问题的图层在 `canvas.layers` 中的索引 |
| `message` | `str` | 包含实测数值的人类可读解释文案 |
| `layer_id` | `str \| None` | 稳定的图层测量 ID，例如 `"layer:3"`，对于分组子图层则为 `"layer:3:0"` |
| `layer_name` | `str \| None` | 图层模型中公开的图层名称（若有） |
| `bbox` | `dict \| None` | 画布空间中的实测边界框，包含 `x`、`y`、`width` 和 `height` |
| `related_layers` | `list[str]` | 该诊断项涉及的图层 ID 列表 |
| `measured` | `dict` | 针对特定规则的实测原始数据，如对比度、字号或画布尺寸 |
| `suggestion` | `str \| None` | 规则能够提供的修复建议提示 |

### 检查项 { #what-gets-checked }

| 代码 | 触发条件 |
| --- | --- |
| `off-canvas` | 图层边界框的部分或全部超出了画布边缘 |
| `motion-path-unused-handle` | 首个位置关键帧的入控制柄或末尾关键帧的出控制柄没有相邻曲线段 |
| `tiny-text` | 文本字号小于画布高度的 2.5%，在缩略图尺寸下可能难以辨认 |
| `text-overflow` | 单个词的宽度超过了图层的 `max_width` 限制且无法折行 |
| `text-clipped` | 折行后的文本超出了画布或所声明的文本框范围 |
| `missing-glyph` | 所选字体将一个或多个字符渲染为了“字形缺失”（豆腐块）占位符 |
| `low-contrast` | 文本颜色与下方合成图层之间的对比度小于 2.0 |
| `layer-overlap` | 两个可见图层发生显著重叠，导致互相遮挡 |
| `layer-hidden` | 可见图层被后添加的不透明图层完全覆盖遮挡 |
| `edge-crowding` | 可见图层距离画布安全边距或平台浮层过近 |
| `near-alignment` | 相关的未旋转图层其测量的 x/y 起点在 3 像素以内，但未完全精确对齐 |
| `caption-safe-area` | 视频字幕落在了画布安全区域边距以内 |
| `caption-timing` | 视频字幕的结束时间晚于其所属视频片段的结束时间，导致永远无法展示 |
| `caption-overlap` | 两个视频字幕同时出现并共享渲染背景 |
| `caption-reading-time` | 字幕在屏幕上停留时间不足 0.8 秒，或每秒超过 20 个显示列，阅读时间过短。中日韩等全宽字符每字符计为 2 列，连接符和变音符号计为 0 列；如果字幕超出其视频片段时长，仅按实际可见的片段部分计算 |
| `clip-stretch` | 片段播放速度慢于原速的 0.5 倍或快于 2 倍。通常这是为了凑齐场景时长而拉伸的结果，但故意的慢动作或延时快进也会以相同规则报告 |

!!! tip "搭配大语言模型（LLM）"
    可将诊断项作为具体的修改指示发回给模型，而不是要求它重新生成整套设计。详情参阅 [AI 工作流](cookbook/ai-workflow.md)。

近距离对齐检查通过比较已渲染图层的位置，发现无意中产生的 1–3 像素轻微偏差。

!!! note "对比度与对齐检查"
    - **对比度检查**会针对文本图层下方的合成背景进行采样分析（包含文本图层的 `Background` 胶囊框效果）。
    - **近距离对齐**会标出 3 像素以内接近对齐的图层，便于你直接精确调整对齐参数，避免盲目猜测坐标。

## `quickthumb` CLI { #the-quickthumb-cli }

命令行工具需要安装 `cli` 额外依赖：

```bash
pip install "quickthumb[cli]"
```

### `quickthumb inspect` { #quickthumb-inspect }

无需写入导出文件，即可直接检查 Canvas 或 Deck 的 JSON 规范。

```bash
quickthumb inspect spec.json
quickthumb inspect deck.json --format json
quickthumb inspect deck.json --target video --fps 24 --max-samples 100
quickthumb inspect spec.json --reduced-motion --var title="Hello"
```

纯文本输出包含有序的页面与图层边界、各图层的动效时长与事件计数、功能特性与降级呈现行、实测资源以及排版诊断。
`--format json` 输出与 Python 的 [`inspect_document()` 结果](api/inspection.md)结构完全一致，包含 `version` 与文档 `kind`。
由于两种文档类型采用统一的页面顺序与通用字段，脚本处理时无需额外推断输入类型。

`--target` 用于指定功能类别（`raster`、`html`、`pptx`、`video`）；省略时默认报告全部四种类别。
`--fps` 和 `--max-samples` 控制有限的动效属性观测过程，而非生成实际图像帧。
`--reduced-motion` 用于检查无障碍静态策略。`--var KEY=VALUE` 的用法与其他规范命令一致。

检查过程中为了计算测量数据，可能会解析字体、资源或解码媒体文件。
命令会报告已观察到的资源状态，但不会进行独立的前置下载或运行环境就绪检查。
动效检查时长并不等同于编码后的视频时长。若要获取标准单帧和回放时间，请使用 Python 的 `sample()` 时间轴。

诊断结果仅供参考。即便存在告警，只要检查过程本身执行成功，退出码依然为 `0`。
输入、校验或资源缺失错误退出码为 `1`；渲染与导出类别错误（包括针对空 Deck 的动效检查）退出码为 `2`。
JSON 格式输出下会使用规范的 `{"errors": [...]}` 结构。
如需将诊断结果作为通过/失败门禁，请使用 `lint --fail-on`；若需检查环境就绪状态，请使用 `doctor`。
参数解析错误（如 `--fps abc`）仍会通过 Typer 向 stderr 输出标准文本并以状态码 `2` 退出。
JSON 格式的错误结果仅在参数解析成功后生效。

### `quickthumb lint` {#quickthumb-lint}

对 JSON 规范执行与 `diagnose()` 相同的诊断检查。

```bash
quickthumb lint spec.json
quickthumb lint spec.json --format json
quickthumb diagnose spec.json --format json
```

```text
[warning] layer 3: tiny-text: text size 14px is below 18px (2.5% of canvas height) ...
[warning] layer 4: low-contrast: text contrast ratio 1.47 against the layers below it ...
```

使用 `--format json` 输出机器可读的结构化结果：

```json
{
  "summary": {
    "diagnostic_count": 1,
    "error_count": 0,
    "warning_count": 1
  },
  "diagnostics": [
    {
      "code": "tiny-text",
      "severity": "warning",
      "layer_index": 3,
      "message": "text size 14px is below 18px ...",
      "layer_id": "layer:3",
      "bbox": {"x": 80, "y": 64, "width": 120, "height": 17},
      "related_layers": ["layer:3"],
      "measured": {"font_size": 14, "threshold": 18.0},
      "suggestion": "increase text size to at least 18px"
    }
  ]
}
```

`lint` 会返回适合在 CI 流程中使用的退出状态码：

| 退出码 | 含义 |
| --- | --- |
| `0` | 无任何问题 |
| `1` | 规范无效：JSON/校验错误、资源缺失或选项非法 |
| `2` | 渲染执行失败 |
| `3` | 检测到了诊断告警或错误 |

`diagnose` 是 `lint` 的别名命令。两者支持相同的自动化选项：

```bash
quickthumb lint spec.json --fail-on error
quickthumb lint spec.json --ignore edge-crowding --ignore missing-glyph
```

默认设置 `--fail-on warning` 会在存在任何诊断项时以退出码 3 退出。
`--fail-on error` 允许警告通过，仅在存在错误时失败；`--fail-on never` 会正常输出诊断信息，但始终以退出码 0 结束。
`--ignore` 会从输出和退出状态码判定中一并排除匹配的诊断代码。
在 `--format json` 下，无效规范会输出[结构化错误详情](errors.md)中的 `errors` 列表，而非 Python 调用栈轨迹。

JSON 输入必须包含顶层的 `kind` 判别属性（`canvas` 或 `deck`）。
针对 Deck 的诊断输出中会包含 `slide_index`，并完整保留图层 ID、边界框、测量数据、关联图层及修复建议。

### `quickthumb diff` { #quickthumb-diff }

在合入视觉变更前，对比渲染出的新图像与基准基准图（golden image）。

```bash
quickthumb diff golden.png output.png
quickthumb diff golden.png output.png --format json --output diff.png
```

该工具结合了感知均值哈希与逐像素指标。
默认情况下，单个通道差值小于等于 2 会被忽略；但只要有任意一个像素超出容差，比对就会宣告失败。
默认的感知哈希相似度阈值为 `0.95`。你可以根据渲染器的特性放宽或收紧要求：

```bash
quickthumb diff golden.png output.png \
  --threshold 0.98 \
  --pixel-tolerance 1 \
  --max-diff-ratio 0.005
```

在 CI 或自动化 Agent 流水线中，建议搭配 `--format json` 使用。
`--max-diff-ratio` 允许一定比例的差异像素存在；`--output` 会将差异图写入文件以便人工复核。
退出码定义如下：

| 退出码 | 含义 |
| --- | --- |
| `0` | 在设定容差范围内匹配一致 |
| `1` | 图像差异超出容差、输入无效或无法写入输出文件 |

在 Python 测试中也可以使用相同的断言机制：

```python
from quickthumb import assert_image_similar

assert_image_similar(
    "golden.png",
    "output.png",
    threshold=0.95,
)
```

断言方法会返回包含图像尺寸、差异像素数量、归一化平均误差、感知哈希和相似度指标的 `ImageDiff` 对象，便于调用方做更详细的报告记录。

### `quickthumb render` {#quickthumb-render}

将 JSON 规范渲染为图像文件：

```bash
quickthumb render spec.json -o thumbnail.png
quickthumb render spec.json -o thumbnail.webp --format WEBP --quality 90
quickthumb render spec.json -o debug.png --debug
```

| 选项 | 说明 |
| --- | --- |
| `-o, --output` | 输出文件路径（默认 `output.png`）。 |
| `--format` | `PNG`、`JPEG` 或 `WEBP`。 |
| `--quality` | 压缩质量：JPEG 为 1–95，WebP 为 1–100；不控制渲染质量。 |
| `--debug` | 在光栅输出上叠加公开图层 ID 的边界框。 |
| `--var KEY=VALUE` | 替换规范中的 `$KEY` 占位符，可重复指定。 |
| `--error-format` | `text`（默认）或 `json`；见[结构化错误](errors.md)。 |

规范无效、资源缺失或选项非法时，`render` 以状态码 `1` 退出；不支持的输出格式等导出失败以状态码 `2` 退出。

### `quickthumb watch` { #quickthumb-watch }

文件发生变化时重新渲染规范，便于手动调整版式时预览结果：

```bash
quickthumb watch spec.json -o preview.png
```

`watch` 接受与 `render` 相同的选项，但不接受 `--error-format`。失败信息以文本输出，监听会继续。

### `quickthumb doctor` {#quickthumb-doctor}

导出前检查包、工具、源文件要求和输出位置权限：

```bash
quickthumb doctor pdf -o out/thumbnail.pdf
quickthumb doctor mp4 --spec spec.json --format json
```

工作流可选 `png`、`jpeg`、`webp`、`gif`、`svg`、`html`、`pdf`、`pptx`、`mp4`、`webm` 或 `mov`。使用 `--spec` 时，规范中的插件渲染器、字体、SVG/视频图层、背景移除和远程资源会带来各自的依赖要求。`-o` 检查输出位置是否可写，但不会创建文件。

每项检查的结果为 `ok`、`warning` 或 `error`。`warning` 表示可选限制，例如缺少字体或资源缓存不可用；`error` 表示必要条件不满足，例如缺少 `quickthumb[pdf]`、FFmpeg、未注册的插件或输出位置不可写。每条警告和错误都包含 `fix`/`remedy`。插件按 CLI 进程的注册表检查，其中只包含导入时注册的插件，因此在代码中注册的插件会被报告为未注册。没有必要检查失败时退出码为 `0`，否则为 `1`。

检查成功不等于导出成功或保真度认证。检测到 Python 包并不能证明原生 Cairo 可以加载；找到 FFmpeg 也不能证明其构建包含目标格式所需的编码器。`doctor` 不会渲染或比对输出。请执行实际导出并检查导出凭据和文件；需要视觉比对时，使用显式保真度策略或 `quickthumb diff`。

### `quickthumb serve` { #quickthumb-serve }

启动支持热重载的本地 HTML 幻灯片服务器。在不提供源码参数时，它会依次查找同目录下的 `slides.py`、`slides.json`、`slides.html` 或 `slides.htm`：

```bash
quickthumb serve
quickthumb serve examples/investor_deck.py
quickthumb serve deck.json --port 4040 --no-open
```

Python 源码应在模块作用域下将 `Deck` 或 `Canvas` 命名定义为 `deck`、`slides` 或 `canvas`。JSON 源码必须声明 `kind: "canvas"` 或 `kind: "deck"`；Canvas 文档包含 `layers`，Deck 文档则包含顶层 `slides` 列表。
使用 `--host` 和 `--port` 调整监听地址，`--no-open` 禁止自动打开浏览器，重复指定 `--var KEY=VALUE` 可进行 JSON 模板变量替换。

观众视图地址为 `/`。通过 `?presenter` 查询参数进入演讲者模式：

```text
http://localhost:3030/?presenter
```

演讲者模式与预览共用浅色主题：左侧为当前幻灯片与演讲备注，右侧为下一页幻灯片及暂停/继续/重置计时器，底部为简易翻页导航。幻灯片预览保留原始宽高比。翻页导航与每页动画进度会广播到该服务器下打开的所有观众标签页，并在刷新后恢复同步。仅在观众端执行的翻页操作只保留在本地。在 Python 中可使用 `.slide(canvas, notes="...")` 添加备注，在 JSON 中可为幻灯片添加 `notes` 字符串。

### 时间轴预览器 { #timeline-scrubber }

在编辑 Python 或 JSON 文档时打开栅格时间轴：

```bash
quickthumb serve examples/timeline_preview.py --timeline
quickthumb serve deck.json --timeline --no-open
```

在普通的 `serve` 会话中，也可以直接访问 `http://localhost:3030/timeline` 进入时间轴。默认视图仍为 HTML 演示文稿，包含幻灯片翻页、点击触发动画以及同步的演讲者控制。
演示模式（Presentation）与动效检查模式（Inspect motion）共享相同的幻灯片选择和缩略图导航。演示模式在中央按原始宽高比展示幻灯片；动效检查模式则在下方打开逐帧拖动面板。演讲者（Presenter）模式打开同步的讲者视图，放映（Present）按钮则全屏展示 HTML 幻灯片。
动效说明中会指出 HTML 输出处于静态还是近似呈现状态。这些控制按钮属于本地创作工具，不会被打包进导出的 HTML 文件中。
独立的 HTML 文件无法抽样检查原始文档；请针对其对应的 Python 或 JSON 源码使用时间轴。

检查面板展示导出渲染器生成的每一帧画面，不支持音频播放或在线编辑。其拖动指针独立于演讲者/观众同步状态。

- 拖动时间滑块、手动输入秒数，或直接点击幻灯片/转场/动效关键节点。
- **Proxy** 会将输出的最长边限制在 640 像素以内（例如 1080×1920 变为 360×640），用于预处理可复用图层图片并在降采样表面上合成普通动效。后续不同尺寸的幻灯片也会适应此输出矩形。
- **Full** 显示第一页幻灯片的原生尺寸，使用与 `Canvas.sample(time=...)` / `Deck.sample(time=...)` 完全相同的标准质量规范时间轴采样器。
- 保存源码会重新加载时间轴，并通过 URL 片段保留所选分辨率和时间点；若修改后的时间轴变短，指针会自动截断在有效范围内。
- 浏览器同一时刻仅发起一次单帧请求；快速拖动时会用最新的选择替换尚未完成的旧请求。在请求帧准备就绪前，显示的帧标签仍标识上一帧。若代码编辑破坏了运行，会显示错误信息，并在下一次保存修复后自动恢复。

!!! tip "本地安全提示"
    `quickthumb serve` 会在你本机运行本地 Python 和 JSON 文件。预览不受信任的内容时，请始终保留默认的本地回环地址（`127.0.0.1`）。

### 变量替换 { #variable-substitution }

基于 JSON 的命令行工具接受 `--var` 参数，在解析前填充 `$KEY`（或 `${KEY}`）占位符：

```bash
quickthumb render template.json -o ep42.png \
  --var TITLE="EPISODE 42" \
  --var ACCENT="#B8FF00"
```

存在未解析的占位符将导致命令以退出码 `1` 退出。
`$theme.*` 引用并非外部变量，它们由规范文件内部的[主题块](json-schema.md#theme-tokens)自行解析。
