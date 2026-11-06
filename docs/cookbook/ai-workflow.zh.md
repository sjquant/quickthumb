---
description: 让大语言模型（LLM）编写 quickthumb JSON 规范，进行校验与排版诊断，反馈错误并最终渲染输出。
---

# AI 工作流 { #ai-workflow }

大语言模型（LLM）非常擅长以 JSON 格式输出排版结构，但不擅长凭空猜测字段名称。
quickthumb 的设计完美契合这一点：规范具备公开发布的 JSON Schema；错误的规范会报错并精确指出有问题的字段；而合法的规范在实际渲染之前还能预先检测排版缺陷。

整个闭环流程如下：

1. 向模型提供 Schema，并用自然语言描述你想要的图像。
2. 使用 `Canvas.from_json()` 加载模型返回的 JSON。如果失败，将错误详情反馈给模型。
3. 运行 `diagnose()`。若发现排版隐患，同样反馈给模型修正。
4. 渲染输出最终图像。

## 1. 为模型提供 Schema { #1-give-the-model-the-schema }

一次性导出当前 Schema：

```bash
python -m pip install "quickthumb[cli]"
quickthumb schema --output quickthumb.schema.json
```

或者在 Python 中调用 `canvas_json_schema()`。Schema 文件体积较大（约 100 KB），最理想的用法是在你的模型提供方支持结构化输出（Structured Outputs）或工具调用（Tool Calling）时，将其作为响应的 Response Schema。约束的严格程度取决于具体提供商；请务必对返回的规范进行校验，并人工审查最终渲染画面。若改为将 Schema 写入 Prompt 提示词中，核心关键部分为 `layers` 和 `effects` 的定义。

提示词可以参考以下形式编写：

```text
Write a quickthumb canvas spec as JSON, following the attached schema.

Canvas: 1280×720 YouTube thumbnail.
- Dark navy background (#0F172A).
- Left-aligned two-line headline: "AI-GENERATED" in cyan (#22D3EE),
  "THUMBNAILS" in white, 96px, weight 900.
- Cyan outline around the canvas, 12px.

Use percentage strings like "8%" for positions. Return only the JSON.
```

## 2. 加载规范并反馈错误 { #2-load-it-and-send-back-errors }

```python
import json
from quickthumb import Canvas, ValidationError

spec = """
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "layers": [
    {"type": "background", "color": "#0F172A"},
    {
      "type": "text",
      "id": "headline",
      "content": [
        {"text": "AI-GENERATED\\n", "color": "#22D3EE"},
        {"text": "THUMBNAILS", "color": "#FFFFFF"}
      ],
      "font": "Inter",
      "font_source": "google",
      "size": 96,
      "weight": 900,
      "position": ["8%", "50%"],
      "align": ["left", "middle"]
    },
    {"type": "outline", "width": 12, "color": "#22D3EE"}
  ]
}
"""

try:
    canvas = Canvas.from_json(spec)
except ValidationError as error:
    feedback = [
        f"{detail.path}: {detail.message}" + (f" ({detail.suggestion})" if detail.suggestion else "")
        for detail in error.details
    ]
    # Send `feedback` back to the model and ask for a corrected spec.
    raise
```

`error.details` 中的每项记录均包含字段的 JSON 指针路径（`path`）、图层 `id`（若已指定）、稳定的错误代码 `code`，以及可选的修复建议 `suggestion`。为每个图层分配显式的 `id` 能让模型更轻松地理解并执行修改：

```text
/layers/1/size (layer 'headline'): Input should be greater than 0
```

关于完整的错误代码清单，请参阅[结构化错误](../errors.md)。

## 3. 检查排版布局 { #3-check-the-layout }

一份合法的规范在视觉上仍可能存在瑕疵：文字字号太小难以辨识、某个词溢出画布边缘、在浅色照片上使用了白色文字等。`diagnose()` 可在渲染前及时发现这些隐患：

```python
findings = canvas.diagnose().findings
for finding in findings:
    print(finding.severity, finding.code, finding.message)
```

```text
warning low-contrast text worst-tile contrast ratio 1.04 against the layers below it is under 2.0; the text may be hard to read
```

可按照与校验错误相同的方式将诊断结果反馈给模型修正。各检查规则详见[诊断与 CLI](../diagnostics.md)。

## 4. 渲染输出 { #4-render }

```python
canvas.render("thumbnail.png")
```

## 请求增量调整 { #asking-for-changes }

一旦得到了满意的基础规范，后续应请求局部修改而非重新生成全新设计。向模型提供当前规范并附上明确的单一调整要求：

```text
Here is the current spec:

<spec>

Change the outline color to #B8FF00 and the headline size to 104.
Keep everything else the same. Return only the JSON.
```

小步微调能够保证版式其他部分的绝对稳定，而且两份 JSON 文件的 diff 能清晰展示模型的具体改动。

## 为什么使用 JSON 而非 Python 代码 { #why-json-rather-than-python }

大模型同样可以编写 quickthumb 的 Python 代码，但这意味着你必须在本地执行模型生成的未知代码。而 JSON 规范纯粹是数据：你可以校验它、持久化存储它、比对版本差异，并在无需执行任何模型生成代码的前提下安全地完成渲染。
