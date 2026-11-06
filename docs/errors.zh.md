---
description: 通过统一的结构化错误机制处理 quickthumb 的校验、资源缺失、导出及 CLI 失败，包含稳定的错误代码与 JSON Pointer 位置。
---

# 结构化错误 { #structured-errors }

quickthumb 的每一次失败（非法字段、资源缺失、目标格式不支持的导出特性或错误的命令行选项）都携带相同的机器可读详情。Agent 与脚本无需解析自然语言文本即可精确定位有问题的输入并确定修复策略；人类用户也能获得清晰的一行错误摘要。

## 错误详情字段 { #error-detail-fields }

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `code` | string | 失败类型的稳定标识符（参见[错误代码](#error-codes)） |
| `category` | string | 错误类别：`validation`、`asset`、`export` 或 `input` |
| `message` | string | 人类可读的失败描述文案 |
| `path` | string 或 `null` | 指向输入文档内部的 [RFC 6901 JSON Pointer](https://www.rfc-editor.org/rfc/rfc6901) 路径（当失败具备文档具体位置时提供） |
| `layer_id` | string 或 `null` | 包含该 `path` 的最内层图层 ID（若已知） |
| `suggestion` | string 或 `null` | 具体的修复建议（若已知） |

`path` 是相对于正在解析或校验的文档根节点的。对于 `Canvas.from_json`、`Deck.from_json`、`validate()` 以及 CLI，该基准为文档根路径，因此 Deck 的失败路径以 `/slides/<index>` 开头。对于直接在 Python 中构建的模型（如 `TextLayer(...)`），该路径则相对于该模型本身。

## Python API { #python-api }

所有 quickthumb 异常均继承自 `QuickthumbError`，并暴露相同的结构化详情：

```python
from quickthumb import Canvas, QuickthumbError

try:
    Canvas.from_json(spec).render("out.png")
except QuickthumbError as error:
    for detail in error.details:
        print(detail.code, detail.path, detail.layer_id, detail.suggestion)
    print(error)  # "/layers/1/max_width (layer 'title'): max_width must be positive"
```

| 异常类 | 类别 | 触发原因 |
| --- | --- | --- |
| `ValidationError` | `validation` | 非法 JSON、未知或缺失字段、数值超出合法范围 |
| `MissingAssetError` | `asset` | 引用的本地图片、SVG、视频、文字填充图片或音频文件不存在；包含 `FileNotFoundError` |
| `RenderingError` | `export` | 不支持的输出格式、目标格式无法导出的功能特性、渲染器底层失败 |
| `InputError` | `input` | 非法的命令行选项或规范文件无法读取 |

`Canvas.validate()` 与 `Deck.validate()` 会在 `ValidationReport.errors` 中返回相同的 `ErrorDetail` 记录，因此事前预检与渲染失败对同一问题的描述完全一致。

## CLI { #cli }

`quickthumb render` 接收 `--error-format json` 参数；`quickthumb lint` 与 `quickthumb diagnose` 则使用其自带的 `--format json` 选项。所有失败详情均以包含完整字段的统一样式写入 stdout：

```bash
quickthumb render spec.json -o out.png --error-format json
```

```json
{
  "errors": [
    {
      "code": "asset_missing",
      "category": "asset",
      "message": "Asset not found: 'hero.png'",
      "path": "/slides/1/layers/0/path",
      "layer_id": "hero",
      "suggestion": "check the path relative to the working directory or use an http(s) URL"
    }
  ]
}
```

文本模式下每项详情在 stderr 中输出为一行，以错误代码开头：

```text
error[asset_missing] /slides/1/layers/0/path (layer 'hero'): Asset not found: 'hero.png'. Suggestion: check the path relative to the working directory or use an http(s) URL.
```

退出状态码按类别划分：`export` 失败以状态码 `2` 退出；`validation`、`asset` 与 `input` 失败以状态码 `1` 退出。

## 错误代码 {#error-codes}

| 代码 | 类别 | 含义 |
| --- | --- | --- |
| `invalid_json` | `validation` | 输入文档不是合法的 JSON 格式 |
| `invalid_document` | `validation` | 文档结构无法使用（例如不包含任何幻灯片的 Deck） |
| `invalid_field` | `validation` | 字段值类型错误或超出允许取值范围 |
| `missing_field` | `validation` | 缺少必填字段 |
| `unknown_field` | `validation` | 存在 Schema 规范中未定义的未知字段 |
| `unknown_plugin` | `validation` | 插件图层引用了未注册的渲染器 |
| `asset_missing` | `asset` | 引用的本地文件不存在 |
| `unsupported_format` | `export` | 输出文件后缀名不是受支持的导出格式 |
| `unsupported_capability` | `export` | 目标格式无法满足文档请求：尝试渲染插件图层（quickthumb 目前支持校验插件图层但尚未支持直接绘制），或者导出策略禁止了目标格式必须使用的降级方案（例如 `ExportPolicy(unsupported_motion="error")`） |
| `missing_dependency` | `export` | 缺少外部工具，例如系统未安装 FFmpeg |
| `export_failed` | `export` | 其他导出或渲染失败，包括输出路径无法写入 |
| `invalid_option` | `input` | 命令行选项的值非法 |
| `input_unreadable` | `input` | 无法读取指定的规范文件 |
| `unresolved_variable` | `input` | `$KEY` 占位符没有匹配的 `--var` 替换变量 |

错误代码保持稳定。描述文本未来可能会有微调，因此自动化脚本和 Agent 应当根据 `code` 和 `path` 进行条件分支判断，而非依赖 `message`。
