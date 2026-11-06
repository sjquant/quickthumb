---
description: quickthumb JSON 规范的文档结构、已发布的 JSON Schema、主题变量（tokens）、插件图层以及全部图层与效果。
---

# JSON Schema 与 AI 工作流 { #json-schema-ai-workflow }

quickthumb 的任意画布都可以用 JSON 进行表达。
JSON 规范可由大语言模型（LLM）或模板动态生成，存入数据库，通过 API 传递，或与你的内容一起存放在版本控制中。

如需生成、校验并渲染你的首个规范文件，请参考 [AI 工作流](cookbook/ai-workflow.md)。
查阅本页了解[图层字段](#layer-schemas)、[效果字段](#effect-schemas)或[公开发布的 Schema](#published-schema)。
使用 `quickthumb` 命令行工具需要执行 `pip install "quickthumb[cli]"`；Python 中的 Schema 辅助函数无需 CLI 额外依赖即可使用。

## 双向往返序列化 { #round-trip-serialization }

规范的 JSON 存储的是人工编写的文档本身，与导出报告独立分开：

```python
from pathlib import Path

from quickthumb import Canvas

# Python → JSON
canvas = Canvas(320, 180).background(color="#102030")
json_str = canvas.to_json()
Path("scene.json").write_text(json_str, encoding="utf-8")

# JSON → Python
restored = Canvas.from_json(Path("scene.json").read_text(encoding="utf-8"))
assert restored.to_json() == json_str
restored.export("from-json.png")
```

!!! note
    `Canvas.from_json()` 期望接收 **JSON 字符串**。如果你手头是 Python 字典，请先调用 `json.dumps(data)`。
    包含 `.custom(fn)` 图层的画布无法被序列化，因为 Python 函数无法存储为 JSON。

相同文档解析并保存为规范 JSON 后，每次都会得到确定一致的结果。但这并不包含打包字体、图片、媒体或缓存中下载的文件。请妥善保存引用的外部资源文件，并确保在其他环境中渲染时能够访问这些路径。
插件 JSON 也同样保留所声明的参数和资源引用而非 Python 回调，因此在加载时请提供对应的[显式注册表](#plugin-layers)。
即便场景 JSON 完全一致，若字体、渲染器版本或运行平台不同，也无法保证像素级完全一致。

## JSON 结构 { #json-structure }

Canvas JSON 文档包含四个顶层必填字段以及一个可选的 `theme` 块：

```json
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "theme": { ... },
  "layers": [ ... ]
}
```

`Canvas.from_json()`、`Deck.from_json()` 以及 CLI 都要求顶层必须包含 `"kind"` 判别字段，取值必须为 `"canvas"` 或 `"deck"`。
Canvas 包含 `layers`，Deck 包含 `slides`；Deck 还可以定义统一的默认尺寸、主题和转场设置。
每个图层对象都需要包含自身的 `"type"` 判别字段。
图层严格按照数组中的顺序绘制，第一项位于最底层。
图层 ID、定位、对齐与动效在 Python、Canvas JSON 根节点以及所有 Deck 幻灯片中均采用完全相同的[通用术语体系](api/index.md#shared-layer-vocabulary)。
Deck 并不会引入单独的图层 Schema。

## 发布的 Schema {#published-schema}

可以通过与 `Canvas.from_json()` 相同的 Pydantic 模型直接输出当前的 JSON Schema：

```bash
quickthumb schema > quickthumb.schema.json
quickthumb schema --output quickthumb.schema.json
quickthumb schema --document --output quickthumb.document-schema.json
```

也可以在 Python 中通过 `canvas_json_schema()` 和 `document_json_schema()` 获取相同的 Schema，并且本站随文档一并托管提供：

- <https://quickthumb.solaqua.dev/schema.json> (Canvas)
- <https://quickthumb.solaqua.dev/document-schema.json>（Canvas 或 Deck）

在 VS Code 中编辑规范文件时，若要启用代码自动补全与校验，请在 `.vscode/settings.json` 中添加规范文件与公开 Schema 的映射：

```json
{
  "json.schemas": [
    {
      "fileMatch": ["*.thumb.json"],
      "url": "https://quickthumb.solaqua.dev/schema.json"
    }
  ]
}
```

建议使用此类文件路径映射，而非在规范文件内部添加 `"$schema"` 键。
`Canvas.from_json()` 会拒绝包含 `$schema` 在内的未知顶层字段。

托管的在线 Schema 文件会在每次文档部署时跟随 `main` 分支自动重新生成。
要获取当前已安装版本的精确 Schema，请运行 `quickthumb schema`。

!!! note "Schema 适用范围"
    `quickthumb schema` 用于描述针对外部工具和受限生成场景的具体 Canvas 规范。
    若需要 Canvas/Deck 联合判别 Schema，请使用 `quickthumb schema --document`。
    关于实际可加载内容的最终权威依据，请参考 `Canvas.from_json()`。

    CLI、`serve`、`Canvas.from_json()` 和 `Deck.from_json()` 均要求匹配的顶层 `kind` 判别字段。
    新序列化的文档会在包括 Deck 幻灯片在内的所有文档边界处包含判别字段。

    如果 Deck 提供了默认尺寸，单页幻灯片中的 `width` 和 `height` 可以省略。
    文档 Schema 允许这种省略，规范 JSON 会在各页幻灯片中输出继承后的具体尺寸。
    转场对象使用与 `Deck.from_json()` 相同的严格判别契约。

    像 `$theme.*` 这类辅助书写特性会在模型校验前由 quickthumb 统一解析。
    因此 quickthumb 能够成功加载的未解析规范，通用 JSON Schema 校验器可能会将其判定为不合法。

该命令仅输出确定性的 JSON，便于放入代码仓库、管道传递至编辑器，或直接提交给受约束的生成式 API。
Canvas Schema 包含当前画布字段、内置图层判别项、效果、动画、受支持的平台预设以及可选的顶层 `theme`。
`--document` Schema 则增加了 Deck 根节点定义，并通过 `kind` 区分映射两种文档类型。

## 插件图层 {#plugin-layers}

插件需注册到一个显式的 `PluginRegistry` 中。
注册信息用于声明图层类型和参数，并由独立且受信任的同步 `raster` 回调函数负责渲染为规范的 RGBA 像素。
回调函数属于应用程序代码，既不能序列化为 JSON，也不能从 JSON 动态导入。

```python
from quickthumb import Canvas, PluginRegistry, canvas_json_schema

registry = PluginRegistry()
registry.register(
    "brand_badge",
    "1.0",
    params_schema={
        "type": "object",
        "required": ["label"],
        "properties": {"label": {"type": "string"}},
        "additionalProperties": False,
    },
)

canvas = Canvas.from_json(text, registry=registry)
schema = canvas_json_schema(registry=registry)
```

插件图层要求包含 `type: "plugin"`、`renderer`、`version`、对象类型的 `params` 以及正整数类型的 `width`/`height`。
`position` 支持普通像素与百分比坐标，`align` 和 `opacity` 会应用于图层的局部边界框。
渲染完成后会统一应用标准的 `clip` 裁切与 `mask` 蒙版边界。
Group 容器可为其子图层排版定位，并能对包含静态插件像素在内的整个分组应用动效。
必须向文档解析器和 Schema 辅助工具提供同一个显式注册表。

```python
from PIL import Image

def badge(params, context):
    with Image.new("RGBA", context.size, params["color"]) as image:
        return image.tobytes()

registry.register("badge", "1", raster=badge)
canvas = Canvas(320, 180, registry=registry).plugin(
    "badge", version="1", params={"color": "#42CEB7"},
    position=(20, 30), width=120, height=40,
)
canvas.export("badge.png")
```

`raster` 回调函数接收 params 字典与 `context.size`，并返回原始 RGBA8 字节数据（大小为 `width * height * 4`）。
可以在图层上通过 `assets={"texture": "assets/texture.png"}` 声明外部资源，并在回调内部通过 `context.read_asset("texture")` 进行读取访问。

### 可选的原生 SVG { #optional-native-svg }

对于矢量输出，可注册一个返回 SVG 字符串的可选 `svg=` 回调函数。

```python
def badge_svg(params, context):
    width, height = context.size
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<rect width="{width}" height="{height}" fill="{params["color"]}"/></svg>'
    )

registry.register("badge", "1", raster=badge, svg=badge_svg)
```

对于不支持原生 SVG 插件的导出格式，会自动降级调用 `raster` 回调进行栅格化渲染。

### 插件 params Schema v1 { #plugin-params-schema-v1 }

`params_schema` 遵循文档化公开的 `quickthumb plugin-params v1` 子集规范。
支持 JSON 数据类型 `object`、`array`、`string`、`number`、`integer`、`boolean`、`null`，以及 `required`、`properties`、`additionalProperties`、`items`、`const`、`enum`、`oneOf`、`anyOf`、字符串正则/长度限制以及数值极值范围。
像 `$ref`、`allOf`、`not` 等不受支持的关键字会在注册时直接拒绝，以确保公开 Schema 与运行时校验行为严格一致。

为了方便需要统一默认行为的应用程序，quickthumb 也维护了一个进程全局的 `plugin_registry`。
但对于测试、后台服务与共享库，强烈建议使用显式的 `PluginRegistry`，以实现隔离与确定性复现。

在使用受 Schema 约束的结构化生成功能时，建议在类型强校验字段中直接填入解析后的实际数值，而非使用变量字符串。

```text
Use quickthumb.schema.json as the JSON response schema.
Generate one valid quickthumb canvas spec for a 1280x720 YouTube thumbnail.
Return only the JSON object.
Use concrete hex colors and numeric sizes in layer fields.
Use only these layer type discriminators: background, text, image, shape, svg, group, outline.
```

## 主题变量（Tokens） { #theme-tokens }

在顶层 `theme` 块中统一定义品牌设计变量，即可在规范内的任意位置通过 `$theme.path` 进行引用。

```json
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "theme": {
    "colors": { "primary": "#B8FF00", "ink": "#111111" },
    "sizes": { "title": 96 }
  },
  "layers": [
    { "type": "background", "color": "$theme.colors.ink" },
    { "type": "text", "content": "Hello", "size": "$theme.sizes.title", "color": "$theme.colors.primary" }
  ]
}
```

具体规则如下：

- `theme` 支持自由嵌套对象组织变量。引用路径以点号分隔，例如 `$theme.colors.primary`。
- 当整个字符串完全由引用构成时，会保留原始的 JSON 数据类型。例如 `"size": "$theme.sizes.title"` 会被解析为数字 `96`；变量同样支持列表类型。
- 标量变量（字符串、数字）也可以插值到更长的字符串内部。
- 主题值还可以作为别名引用其他主题变量。循环引用将触发 `ValidationError`。
- 引用了未定义的主题变量将触发 `ValidationError`。
- 变量会在解析时立即替换展开。`to_json()` 输出的是替换后的实际值，不再包含 `theme` 块。
- 主题变量可与 `$var` 模板变量替换（`quickthumb render --var KEY=VALUE`）协同工作；`$theme.*` 永远不会被误当成命令行变量处理。

## 图层 Schema {#layer-schemas}

常用图层类型如下所示。
视频、图表、二维码、动态计数器和插件图层遵循相同的模式。
完整字段清单请查阅[公开发布的 Schema](#published-schema)及各 API 参考文档。

### 背景图层 { #background-layer }

```json
{
  "type": "background",
  "color": "#0F172A",
  "gradient": null,
  "image": null,
  "opacity": 1.0,
  "blend_mode": null,
  "fit": null,
  "effects": []
}
```

仅需包含要覆盖的字段，其余字段将使用默认值。

**渐变变体：**

```json
{
  "type": "background",
  "gradient": {
    "type": "linear",
    "angle": 120,
    "stops": [["#111827", 0.0], ["#11182700", 1.0]]
  }
}
```

```json
{
  "type": "background",
  "gradient": {
    "type": "radial",
    "stops": [["#00000000", 0.0], ["#000000CC", 1.0]],
    "center": [0.5, 0.5]
  }
}
```

**图片背景：**

```json
{
  "type": "background",
  "image": "https://example.com/photo.jpg",
  "fit": "cover",
  "blend_mode": "multiply",
  "effects": [
    { "type": "filter", "blur": 4, "brightness": 0.75, "contrast": 1.1, "saturation": 0.9 }
  ]
}
```

---

### 文本图层 { #text-layer }

```json
{
  "type": "text",
  "content": "Hello World",
  "font_source": "auto",
  "font_variations": {},
  "emoji_style": "monochrome",
  "size": 72,
  "color": "#FFFFFF",
  "position": ["50%", "50%"],
  "align": "center",
  "max_height": null,
  "min_size": 1,
  "balance_lines": false,
  "opacity": 1.0,
  "rotation": 0.0,
  "effects": []
}
```

**使用 `TextPart` 列表定制富文本：**

```json
{
  "type": "text",
  "content": [
    {
      "text": "5 ",
      "color": "#FBBF24",
      "font_source": null,
      "font_variations": null,
      "emoji_style": null,
      "weight": 900,
      "effects": []
    },
    {
      "text": "WARNING SIGNS",
      "color": "#FFFFFF",
      "font_source": "auto",
      "font_variations": {},
      "emoji_style": "monochrome",
      "weight": 900,
      "effects": []
    }
  ],
  "size": 80,
  "position": ["8%", "55%"],
  "align": "left",
  "max_width": "65%",
  "auto_scale": false,
  "rotation": 0.0,
  "opacity": 1.0,
  "effects": [
    { "type": "stroke", "width": 3, "color": "#000000" },
    { "type": "shadow", "offset_x": 4, "offset_y": 4, "color": "#000000", "blur_radius": 8 }
  ]
}
```

**渐变填充文本：**

```json
{
  "type": "text",
  "content": "GRADIENT",
  "size": 120,
  "fill": {
    "type": "linear",
    "angle": 90,
    "stops": [["#FF6B6B", 0.0], ["#4ECDC4", 1.0]]
  },
  "position": ["50%", "50%"],
  "align": "center",
  "effects": []
}
```

**图片填充文本：**

```json
{
  "type": "text",
  "content": "TEXTURE",
  "size": 140,
  "fill": {
    "type": "image",
    "path": "fire_texture.jpg",
    "fit": "cover"
  },
  "position": ["50%", "50%"],
  "align": "center",
  "effects": []
}
```

`fill` 判别值与背景渐变相同，支持 `"linear"`、`"radial"` 和 `"image"`。
可以通过相同的判别对象为各个 `TextPart` 分别配置 `fill`。

**对齐（Align）取值：** `"center"`、`"left"`、`"right"`、`"top-left"`、`"top-center"`、`"top-right"`、`"bottom-left"`、`"bottom-center"`、`"bottom-right"`

---

### 图像图层 { #image-layer }

```json
{
  "type": "image",
  "path": "portrait.png",
  "position": ["74%", "54%"],
  "width": 420,
  "height": 520,
  "fit": "cover",
  "align": "center",
  "opacity": 1.0,
  "rotation": 0.0,
  "remove_background": false,
  "border_radius": 24,
  "blend_mode": "normal",
  "effects": [
    { "type": "filter", "contrast": 1.1, "saturation": 1.05 },
    { "type": "shadow", "offset_x": 0, "offset_y": 12, "color": "#000000", "blur_radius": 24 }
  ]
}
```

---

### 形状图层 { #shape-layer }

```json
{
  "type": "shape",
  "shape": "rectangle",
  "position": [48, 48],
  "width": 320,
  "height": 96,
  "color": "#CC0000",
  "border_radius": 14,
  "opacity": 1.0,
  "rotation": 0.0,
  "align": "top-left",
  "effects": [
    { "type": "stroke", "width": 2, "color": "#FFFFFF" }
  ]
}
```

`"shape"` 的有效取值为 `"rectangle"`、`"ellipse"`、`"pill"`、`"triangle"`、`"star"` 和 `"polygon"`。

**星形与多边形变体：**

```json
{
  "type": "shape",
  "shape": "star",
  "position": ["80%", "50%"],
  "width": 280,
  "height": 280,
  "color": "#7C5CFF",
  "align": "center",
  "rotation": 12,
  "star_points": 5,
  "inner_radius": 0.45
}
```

```json
{
  "type": "shape",
  "shape": "polygon",
  "position": [600, 60],
  "width": 160,
  "height": 100,
  "color": "#53BF9D",
  "points": [[0.0, 0.25], [0.6, 0.25], [0.6, 0.0], [1.0, 0.5], [0.6, 1.0], [0.6, 0.75], [0.0, 0.75]]
}
```

`points` 仅对 `"polygon"` 有效且为必填项。
必须包含至少 3 个在形状边界框内归一化至 `0.0`–`1.0` 范围内的顶点坐标。
`star_points`（3 或更大）和 `inner_radius`（大于 0 且小于 1）仅适用于 `"star"`。

---

### SVG 图层 { #svg-layer }

在渲染时进行栅格化。需要安装 `quickthumb[svg]` 额外依赖。
详情参阅 [SVG 参考](api/svg.md)。

```json
{
  "type": "svg",
  "path": "logo.svg",
  "position": ["92%", "10%"],
  "width": 120,
  "align": "center",
  "opacity": 1.0,
  "rotation": 0.0,
  "blend_mode": null,
  "effects": []
}
```

`width`/`height` 用于指定栅格化尺寸。若仅指定其中一项，将保持原始宽高比。
SVG 图层支持与图像图层相同的 `effects` 效果列表。

---

### 分组图层 { #group-layer }

自动测量子元素并将其排布为行或列的自动布局容器。
因此子元素绝不能设置 `position`。详情参阅[分组参考](api/group.md)。

```json
{
  "type": "group",
  "direction": "column",
  "gap": 24,
  "padding": 0,
  "position": ["8%", "50%"],
  "align": ["left", "middle"],
  "item_align": "start",
  "children": [
    { "type": "shape", "shape": "pill", "width": 120, "height": 36, "color": "#E94560" },
    { "type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900 },
    { "type": "text", "content": "No coordinates were harmed", "size": 40, "color": "#A2A8D3" }
  ]
}
```

- `direction`：`"column"`（默认）或 `"row"`
- `gap`：子元素之间的像素间距。`padding` 支持单个整数、`[vertical, horizontal]` 或 `[top, right, bottom, left]`
- `item_align`：交叉轴上的对齐方式，取值为 `"start"`、`"center"`、`"end"` 之一
- `children` 支持的类型：`"text"`、`"image"`、`"shape"`、`"svg"` 以及嵌套的 `"group"`

---

### 描边图层 { #outline-layer }

```json
{
  "type": "outline",
  "width": 12,
  "color": "#B8FF00",
  "offset": 0,
  "opacity": 1.0
}
```

---

## 效果 Schema {#effect-schemas}

效果放置在各图层的 `"effects"` 数组中，并包含 `"type"` 判别属性。

=== "Stroke"
    ```json
    { "type": "stroke", "width": 4, "color": "#000000" }
    ```

=== "Shadow"
    ```json
    { "type": "shadow", "offset_x": 4, "offset_y": 8, "color": "#000000", "blur_radius": 12 }
    ```

=== "Glow"
    ```json
    { "type": "glow", "color": "#B8FF00", "radius": 16, "opacity": 0.35 }
    ```

=== "Filter"
    ```json
    { "type": "filter", "blur": 4, "brightness": 0.75, "contrast": 1.1, "saturation": 0.9 }
    ```

=== "Background（文本背景框）"
    ```json
    { "type": "background", "color": "#111827CC", "padding": [16, 24], "border_radius": 14, "opacity": 1.0 }
    ```

=== "Grain"
    ```json
    { "type": "grain", "intensity": 0.12, "monochrome": true, "blend_mode": "overlay", "opacity": 1.0 }
    ```

    `blend_mode` 可取 `"overlay"`、`"screen"`、`"multiply"`、`"normal"`。若要获得完全确定的噪点输出，可提供可选的整数 `"seed"`。

=== "Duotone"
    ```json
    { "type": "duotone", "shadows": "#0A1730", "highlights": "#7FADFF", "opacity": 1.0 }
    ```

=== "InnerShadow（内阴影）"
    ```json
    { "type": "inner_shadow", "offset_x": 0, "offset_y": 6, "color": "#00000080", "blur_radius": 12, "opacity": 1.0 }
    ```

=== "BackdropBlur（背景模糊）"
    ```json
    { "type": "backdrop_blur", "radius": 24, "opacity": 1.0 }
    ```

各图层支持的效果清单请参阅[效果参考](api/effects.md)。

## 完整示例 { #complete-example }

一个完整的 YouTube 风格缩略图规范示例：

```json
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "layers": [
    {
      "type": "background",
      "image": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3",
      "fit": "cover",
      "effects": [{ "type": "filter", "brightness": 0.6 }]
    },
    {
      "type": "background",
      "color": "#000000",
      "opacity": 0.35
    },
    {
      "type": "shape",
      "shape": "rectangle",
      "position": [52, 52],
      "width": 360,
      "height": 96,
      "color": "#CC0000",
      "border_radius": 14,
      "effects": []
    },
    {
      "type": "text",
      "content": [
        { "text": "AI ", "color": "#B8FF00", "weight": 900, "effects": [] },
        { "text": "THUMBNAILS", "color": "#FFFFFF", "weight": 900, "effects": [] }
      ],
      "size": 108,
      "position": ["8%", "52%"],
      "align": "left",
      "max_width": "58%",
      "rotation": 0.0,
      "opacity": 1.0,
      "effects": [
        { "type": "stroke", "width": 6, "color": "#000000" },
        { "type": "shadow", "offset_x": 4, "offset_y": 4, "color": "#000000", "blur_radius": 8 }
      ]
    },
    {
      "type": "image",
      "path": "portrait.png",
      "position": ["75%", "55%"],
      "width": 430,
      "height": 540,
      "fit": "cover",
      "align": "center",
      "border_radius": 24,
      "effects": [
        { "type": "shadow", "offset_x": 0, "offset_y": 14, "color": "#000000", "blur_radius": 24 }
      ]
    },
    {
      "type": "outline",
      "width": 12,
      "color": "#B8FF00",
      "offset": 0,
      "opacity": 1.0
    }
  ]
}
```

## 使用大语言模型（LLM）生成规范 { #generating-specs-with-an-llm }

[AI 工作流](cookbook/ai-workflow.md)示例详细演示了全流程：向模型提供公开 Schema、反馈校验错误与 `diagnose()` 结果，以及请求增量修改而非重新生成整套设计。

## 序列化注意事项 { #serialization-notes }

| 字段 | 序列化格式 |
| --- | --- |
| `align` | 字符串：`"center"`、`"top-left"` 等 |
| `blend_mode` | 字符串：`"multiply"`、`"normal"` 等 |
| `fit` | 字符串：`"cover"`、`"contain"`、`"fill"` |
| `position` | JSON 数组：`[640, 360]` 或 `["50%", "50%"]` |
| 渐变停靠点 | `["#color", 0.0]` 键值对组成的 JSON 数组 |
| `null` 字段 | 省略的字段在解析时使用 `null` 或默认值 |
| `theme` 块 | 在解析时立即解析替换，`to_json()` 输出不包含 `theme` 块的具体数值 |
