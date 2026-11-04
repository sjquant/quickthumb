---
description: LLM으로 quickthumb JSON 명세를 작성하고 검증·진단한 뒤 오류를 다시 전달해 결과를 렌더링합니다.
---

# AI 작업 흐름 { #ai-workflow }

LLM은 레이아웃을 JSON으로 작성하는 데는 능숙하지만 필드 이름을 추측하는 데는 약합니다.
quickthumb는 공개 JSON Schema를 제공하고, 잘못된 명세에는 정확한 필드를 가리키는 오류를 반환하며, 유효한 명세도 렌더링 전에 레이아웃 문제를 검사할 수 있어 이 작업에 적합합니다.

반복 과정은 다음과 같습니다.

1. 모델에 스키마를 제공하고 원하는 이미지를 설명합니다.
2. `Canvas.from_json()`으로 응답을 불러옵니다. 실패하면 오류를 다시 전달합니다.
3. `diagnose()`를 실행하고 문제가 있으면 진단도 전달합니다.
4. 렌더링합니다.

## 1. 모델에 스키마 제공 { #1-give-the-model-the-schema }

스키마를 한 번 내보냅니다.

```bash
python -m pip install "quickthumb[cli]"
quickthumb schema --output quickthumb.schema.json
```

Python의 `canvas_json_schema()`로도 얻을 수 있습니다.
스키마는 약 100 KB로 크므로, 제공자가 지원한다면 구조화된 출력이나 도구 호출 기능의 응답 스키마로 사용하는 것이 좋습니다.
강제 수준은 제공자에 따라 다릅니다. 반환된 명세를 검증하고 렌더링 결과를 검토하세요.
프롬프트에 직접 넣는다면 `layers`와 `effects` 정의가 중요합니다.

다음과 같은 프롬프트를 사용할 수 있습니다.

```text
Write a quickthumb canvas spec as JSON, following the attached schema.

Canvas: 1280×720 YouTube thumbnail.
- Dark navy background (#0F172A).
- Left-aligned two-line headline: "AI-GENERATED" in cyan (#22D3EE),
  "THUMBNAILS" in white, 96px, weight 900.
- Cyan outline around the canvas, 12px.

Use percentage strings like "8%" for positions. Return only the JSON.
```

## 2. 불러오기와 오류 피드백 { #2-load-it-and-send-back-errors }

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

`error.details`의 각 항목에는 필드의 JSON Pointer(`path`), 존재하는 경우 레이어 `id`, 안정적인 `code`, 때에 따라 `suggestion`이 포함됩니다.
각 레이어에 `id`를 지정하면 모델이 메시지에 따라 수정하기 쉽습니다.

```text
/layers/1/size (layer 'headline'): Input should be greater than 0
```

전체 코드는 [구조화된 오류](../errors.md)를 참고하세요.

## 3. 레이아웃 검사 { #3-check-the-layout }

명세가 유효해도 너무 작은 글자, 가장자리를 벗어난 단어, 밝은 사진 위의 흰 글자처럼 보기에 문제가 있을 수 있습니다.
`diagnose()`는 이런 문제를 찾아냅니다.

```python
findings = canvas.diagnose().findings
for finding in findings:
    print(finding.severity, finding.code, finding.message)
```

```text
warning low-contrast text worst-tile contrast ratio 1.04 against the layers below it is under 2.0; the text may be hard to read
```

검증 오류와 같은 방식으로 진단을 다시 전달하세요.
전체 검사 목록은 [진단과 CLI](../diagnostics.md)를 참고하세요.

## 4. 렌더링 { #4-render }

```python
canvas.render("thumbnail.png")
```

## 변경 요청 { #asking-for-changes }

마음에 드는 명세가 생기면 새 디자인 대신 수정을 요청하세요.
현재 명세와 구체적인 변경 하나를 전달합니다.

```text
Here is the current spec:

<spec>

Change the outline color to #B8FF00 and the headline size to 104.
Keep everything else the same. Return only the JSON.
```

작게 수정하면 나머지 레이아웃을 안정적으로 유지할 수 있고 두 JSON 파일의 차이를 비교해 모델이 바꾼 내용을 정확히 확인할 수 있습니다.

## Python 대신 JSON을 사용하는 이유 { #why-json-rather-than-python }

모델은 quickthumb Python 코드도 작성할 수 있지만 그때는 생성된 코드를 실행해야 합니다.
JSON 명세는 데이터이므로 모델이 작성한 코드를 실행하지 않고도 검증, 저장, 비교, 렌더링할 수 있습니다.
