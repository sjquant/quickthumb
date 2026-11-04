---
description: quickthumb JSON 명세의 문서 구조, 공개 JSON Schema, 테마 토큰, 플러그인 레이어, 모든 레이어와 효과를 설명합니다.
---

# JSON Schema와 AI 작업 흐름 { #json-schema-ai-workflow }

quickthumb의 모든 캔버스는 JSON으로 작성할 수 있습니다.
LLM이나 템플릿으로 생성하고 데이터베이스에 저장하거나 API로 보내거나 콘텐츠와 함께 버전 관리할 수 있습니다.

첫 명세를 생성·검증·렌더링하려면 [AI 작업 흐름](cookbook/ai-workflow.md)을 따르세요.
이 문서는 [레이어 필드](#layer-schemas), [효과](#effect-schemas), [공개 스키마](#published-schema)를 찾아볼 때 사용합니다.
`quickthumb` 명령에는 `pip install "quickthumb[cli]"`가 필요하지만 Python 스키마 도우미는 CLI 추가 기능 없이도 동작합니다.

## 왕복 직렬화 { #round-trip-serialization }

정규 JSON은 내보내기 결과와 별개로 제작된 문서를 저장합니다.

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
    `Canvas.from_json()`은 **JSON 문자열**을 받습니다. Python dict가 있다면 먼저 `json.dumps(data)`를 호출하세요.
    Python 함수를 JSON에 저장할 수 없으므로 `.custom(fn)` 레이어가 있는 캔버스는 직렬화할 수 없습니다.

같은 해석된 문서의 정규 직렬화 결과는 결정적입니다.
글꼴, 이미지, 미디어, 캐시 다운로드를 패키징하지는 않으므로 참조 파일을 보관하고 다른 곳에서 렌더링할 때 경로에 접근할 수 있게 하세요.
플러그인 JSON도 Python 콜백이 아닌 선언된 매개변수와 에셋 참조를 유지하므로 불러올 때 대응하는 [명시적 레지스트리](#plugin-layers)를 제공하세요.
장면 JSON이 같아도 글꼴, 렌더러 버전, 플랫폼이 다르면 같은 픽셀을 보장하지 않습니다.

## JSON 구조 { #json-structure }

Canvas JSON 문서는 최상위 필수 필드 네 개와 선택적인 `theme` 블록을 가집니다.

```json
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "theme": { ... },
  "layers": [ ... ]
}
```

`Canvas.from_json()`, `Deck.from_json()`, CLI에는 최상위 `"kind"` 구분자가 필수이며 값은 `"canvas"` 또는 `"deck"`여야 합니다.
Canvas는 `layers`, Deck은 `slides`를 포함하며 Deck은 공통 기본 크기, 테마, 전환도 정의할 수 있습니다.
각 레이어 객체에는 자체 `"type"` 구분자가 필요합니다.
레이어는 배열 순서대로 그리며 첫 항목이 맨 뒤입니다.
레이어 ID, 배치, 정렬, 모션은 Python, Canvas JSON 루트, 모든 Deck 슬라이드에서 같은 [공통 용어](api/index.md#shared-layer-vocabulary)를 사용합니다.
Deck이 별도 레이어 스키마를 도입하지는 않습니다.

## 공개 스키마 { #published-schema }

`Canvas.from_json()`과 같은 Pydantic 모델에서 현재 JSON Schema를 출력합니다.

```bash
quickthumb schema > quickthumb.schema.json
quickthumb schema --output quickthumb.schema.json
quickthumb schema --document --output quickthumb.document-schema.json
```

같은 스키마를 Python의 `canvas_json_schema()`, `document_json_schema()`로 얻을 수 있으며 이 문서와 함께 다음 주소에도 제공합니다.

- <https://quickthumb.solaqua.dev/schema.json> (Canvas)
- <https://quickthumb.solaqua.dev/document-schema.json> (Canvas 또는 Deck)

VS Code에서 명세를 편집할 때 자동 완성과 검증을 사용하려면 `.vscode/settings.json`에 명세 파일과 공개 스키마의 매핑을 추가하세요.

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

명세 안의 `"$schema"` 키 대신 이와 같은 파일 매핑을 사용하세요.
`Canvas.from_json()`은 `$schema`를 포함한 알 수 없는 최상위 필드를 거부합니다.

호스팅 파일은 `main` 브랜치를 따르는 문서 배포마다 다시 생성됩니다.
설치한 버전의 스키마는 `quickthumb schema`로 얻으세요.

!!! note "스키마 범위"
    `quickthumb schema`는 외부 도구와 제약된 생성에 사용할 구체적인 Canvas 명세를 설명합니다.
    결합된 Canvas/Deck 구분자 스키마에는 `quickthumb schema --document`를 사용하세요.
    실제로 불러올 수 있는 내용의 기준은 `Canvas.from_json()`입니다.

    CLI, `serve`, `Canvas.from_json()`, `Deck.from_json()`에는 모두 맞는 최상위 `kind` 구분자가 필요합니다.
    새로 직렬화한 문서는 Deck 슬라이드를 포함해 모든 문서 경계에 구분자를 포함합니다.

    Deck이 기본 크기를 제공하면 슬라이드의 `width`, `height`는 생략할 수 있습니다.
    문서 스키마도 이를 허용하고 정규 JSON은 각 슬라이드에 상속된 크기를 출력합니다.
    전환 객체는 `Deck.from_json()`과 같은 엄격한 구분자 계약을 사용합니다.

    `$theme.*` 같은 제작 편의 기능은 모델 검증 전에 quickthumb가 해석합니다.
    따라서 quickthumb가 불러올 수 있는 미해결 제작 명세도 일반 JSON Schema 검증기는 거부할 수 있습니다.

명령은 결정적인 JSON만 출력하므로 저장소에 넣거나 편집기로 파이프하거나 제약된 생성 API에 직접 전달할 수 있습니다.
Canvas 스키마에는 현재 캔버스 필드, 내장 레이어 구분자, 효과, 애니메이션, 지원 플랫폼 프리셋, 선택적인 최상위 `theme`가 포함됩니다.
`--document` 스키마는 Deck 루트를 추가하고 `kind`로 두 문서 종류를 매핑합니다.

## 플러그인 레이어 { #plugin-layers }

플러그인은 하나의 명시적인 `PluginRegistry`에 등록합니다.
등록은 레이어 종류와 매개변수를 설명하며 신뢰할 수 있는 별도의 동기식 `raster` 콜백이 정규 RGBA 픽셀로 렌더링합니다.
콜백은 애플리케이션 코드이며 JSON으로 직렬화하거나 JSON에서 가져오지 않습니다.

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

플러그인 레이어에는 `type: "plugin"`, `renderer`, `version`, 객체형 `params`, 양의 정수 `width`/`height`가 필요합니다.
`position`은 일반 픽셀·백분율 좌표를 받으며 `align`, `opacity`는 로컬 상자에 적용됩니다.
렌더링 후 표준 `clip`, `mask` 경계를 적용합니다.
Group은 자식 위치를 정하고 정적 플러그인 픽셀을 포함한 그룹 전체를 애니메이션화할 수 있습니다.
문서 파서와 Schema 도우미에 같은 명시적 레지스트리를 제공해야 합니다.

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

`raster` 콜백은 params dict와 `context.size`를 받고 원시 RGBA8 바이트(`width * height * 4`)를 반환합니다.
레이어의 `assets={"texture": "assets/texture.png"}`로 외부 에셋을 선언하고 `context.read_asset("texture")`로 접근하세요.

### 선택적인 네이티브 SVG { #optional-native-svg }

벡터 출력에는 SVG 문자열을 반환하는 선택적 `svg=` 콜백을 등록합니다.

```python
def badge_svg(params, context):
    width, height = context.size
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<rect width="{width}" height="{height}" fill="{params["color"]}"/></svg>'
    )

registry.register("badge", "1", raster=badge, svg=badge_svg)
```

네이티브 SVG 플러그인을 지원하지 않는 형식에서는 자동으로 `raster` 콜백 렌더링으로 대체합니다.

### 플러그인 params Schema v1 { #plugin-params-schema-v1 }

`params_schema`는 문서화된 `quickthumb plugin-params v1` 부분집합을 받습니다.
JSON 자료형 `object`, `array`, `string`, `number`, `integer`, `boolean`, `null`과 `required`, `properties`, `additionalProperties`, `items`, `const`, `enum`, `oneOf`, `anyOf`, 문자열 패턴·크기 제한, 숫자 최솟값·최댓값을 지원합니다.
`$ref`, `allOf`, `not` 같은 미지원 키워드는 등록 시 거부해 공개 Schema와 런타임 검증이 일치하도록 합니다.

공통 기본값을 원하는 애플리케이션을 위해 프로세스 전역 `plugin_registry`도 유지합니다.
테스트, 서비스, 라이브러리는 등록을 격리하고 재현할 수 있도록 명시적 `PluginRegistry`를 권장합니다.

제약된 생성에서는 자료형이 있는 필드에 해석된 구체적인 값을 사용하세요.

```text
Use quickthumb.schema.json as the JSON response schema.
Generate one valid quickthumb canvas spec for a 1280x720 YouTube thumbnail.
Return only the JSON object.
Use concrete hex colors and numeric sizes in layer fields.
Use only these layer type discriminators: background, text, image, shape, svg, group, outline.
```

## 테마 토큰 { #theme-tokens }

최상위 `theme` 블록에 브랜드 토큰을 한 번 정의하고 명세 어디에서든 `$theme.path`로 참조합니다.

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

규칙은 다음과 같습니다.

- `theme`는 그룹을 자유롭게 중첩할 수 있습니다. 참조 경로는 `$theme.colors.primary`처럼 점으로 구분합니다.
- 문자열 전체가 참조이면 원래 JSON 자료형을 유지합니다. `"size": "$theme.sizes.title"`은 숫자 `96`으로 해석되며 토큰은 목록도 가질 수 있습니다.
- 스칼라 토큰(문자열, 숫자)은 더 긴 문자열 안에 삽입할 수도 있습니다.
- 테마 값이 다른 토큰을 참조하는 별칭도 가능합니다. 순환 참조는 `ValidationError`를 발생시킵니다.
- 정의하지 않은 토큰 참조는 `ValidationError`를 발생시킵니다.
- 토큰은 파싱 시 해석됩니다. `to_json()`은 `theme` 없이 실제 값을 출력합니다.
- 테마 토큰은 `$var` 템플릿 치환(`quickthumb render --var KEY=VALUE`)과 함께 동작하며 `$theme.*`는 절대로 변수로 처리하지 않습니다.

## 레이어 스키마 { #layer-schemas }

자주 사용하는 레이어는 아래와 같습니다.
동영상, 차트, QR 코드, 카운터, 플러그인도 같은 패턴을 따릅니다.
필드는 [공개 스키마](#published-schema)와 각 API 레퍼런스에 있습니다.

### 배경 레이어 { #background-layer }

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

필요한 필드만 포함하세요. 나머지는 기본값을 사용합니다.

**그라디언트 변형:**

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

**이미지 배경:**

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

### 텍스트 레이어 { #text-layer }

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

**`TextPart` 목록으로 서식 지정:**

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

**그라디언트로 채운 텍스트:**

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

**이미지로 채운 텍스트:**

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

`fill` 구분자는 배경 그라디언트와 같은 `"linear"`, `"radial"`, `"image"`를 사용합니다.
같은 구분자 객체로 각 `TextPart`의 `fill`도 설정할 수 있습니다.

**Align 값:** `"center"`, `"left"`, `"right"`, `"top-left"`, `"top-center"`, `"top-right"`, `"bottom-left"`, `"bottom-center"`, `"bottom-right"`

---

### 이미지 레이어 { #image-layer }

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

### 도형 레이어 { #shape-layer }

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

`"shape"` 값은 `"rectangle"`, `"ellipse"`, `"pill"`, `"triangle"`, `"star"`, `"polygon"`입니다.

**별과 다각형 변형:**

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

`points`는 `"polygon"`에서만 유효하며 필수입니다.
도형 상자 안의 `0.0`–`1.0`으로 정규화한 정점이 최소 3개 있어야 합니다.
`star_points`(3 이상)와 `inner_radius`(0보다 크고 1보다 작음)는 `"star"`에만 적용됩니다.

---

### SVG 레이어 { #svg-layer }

렌더링 시 래스터화합니다. `quickthumb[svg]` 추가 기능이 필요합니다.
[SVG 레퍼런스](api/svg.md)를 참고하세요.

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

`width`/`height`는 래스터 크기를 정합니다. 하나만 지정하면 종횡비를 유지합니다.
SVG 레이어는 이미지 레이어와 같은 `effects`를 받습니다.

---

### 그룹 레이어 { #group-layer }

자식을 측정해 행이나 열로 쌓는 자동 레이아웃 컨테이너입니다.
따라서 자식은 `position`을 설정하면 안 됩니다. [그룹 레퍼런스](api/group.md)를 참고하세요.

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

- `direction`: 기본 `"column"` 또는 `"row"`
- `gap`: 자식 사이 픽셀 간격. `padding`은 정수, `[vertical, horizontal]`, `[top, right, bottom, left]`
- `item_align`: 교차축 배치로 `"start"`, `"center"`, `"end"` 중 하나
- `children` 종류: `"text"`, `"image"`, `"shape"`, `"svg"`, 중첩된 `"group"`

---

### 테두리 레이어 { #outline-layer }

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

## 효과 스키마 { #effect-schemas }

효과는 각 레이어의 `"effects"` 배열에 들어가며 `"type"` 구분자를 사용합니다.

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

=== "Background(텍스트)"
    ```json
    { "type": "background", "color": "#111827CC", "padding": [16, 24], "border_radius": 14, "opacity": 1.0 }
    ```

=== "Grain"
    ```json
    { "type": "grain", "intensity": 0.12, "monochrome": true, "blend_mode": "overlay", "opacity": 1.0 }
    ```

    `blend_mode`는 `"overlay"`, `"screen"`, `"multiply"`, `"normal"`입니다. 결정적인 출력에는 선택 정수 `"seed"`를 사용합니다.

=== "Duotone"
    ```json
    { "type": "duotone", "shadows": "#0A1730", "highlights": "#7FADFF", "opacity": 1.0 }
    ```

=== "내부 그림자"
    ```json
    { "type": "inner_shadow", "offset_x": 0, "offset_y": 6, "color": "#00000080", "blur_radius": 12, "opacity": 1.0 }
    ```

=== "배경 흐림"
    ```json
    { "type": "backdrop_blur", "radius": 24, "opacity": 1.0 }
    ```

레이어별 지원 효과는 [효과 레퍼런스](api/effects.md)에 있습니다.

## 전체 예제 { #complete-example }

YouTube 스타일 썸네일의 전체 명세입니다.

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

## LLM으로 명세 생성 { #generating-specs-with-an-llm }

[AI 작업 흐름](cookbook/ai-workflow.md) 레시피는 모델에 공개 스키마 제공, 검증 오류와 `diagnose()` 결과 피드백, 새 디자인 대신 수정 요청까지 전체 과정을 설명합니다.

## 직렬화 참고 { #serialization-notes }

| 필드 | 직렬화 형식 |
| --- | --- |
| `align` | 문자열: `"center"`, `"top-left"` 등 |
| `blend_mode` | 문자열: `"multiply"`, `"normal"` 등 |
| `fit` | 문자열: `"cover"`, `"contain"`, `"fill"` |
| `position` | JSON 배열: `[640, 360]` 또는 `["50%", "50%"]` |
| 그라디언트 정지점 | `["#color", 0.0]` 쌍의 JSON 배열 |
| `null` 필드 | 생략한 필드는 `null` 또는 기본값 사용 |
| `theme` 블록 | 파싱 시 해석되며 `to_json()`은 `theme` 없이 실제 값 출력 |
