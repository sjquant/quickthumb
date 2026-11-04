---
description: Canvas, 레이어, 배경, 텍스트, 이미지, 도형, 테두리, 효과, 열거형과 그라디언트에 대한 quickthumb API 레퍼런스입니다.
---

# API 레퍼런스 { #api-reference }

`Canvas`로 장면을 만들고, 여러 장면을 `Deck`에 담아 순서대로 보여 줄 수 있습니다. 두 객체는 같은 문서 연산을 제공하며, 각 레이어에 지정할 수 있는 필드는 개별 레퍼런스에 설명되어 있습니다.

## 지원되는 공개 인터페이스 { #supported-public-surface }

문서화된 제작 자료형과 결과 모델은 `quickthumb`에서, 오디오 분석은 문서화된 `quickthumb.audio` 모듈에서 가져오세요.
다른 모듈에서 어떤 이름을 가져올 수 있다는 사실만으로 지원되는 진입점이 되는 것은 아닙니다.

| 인터페이스 | 지원되는 사용법 |
| --- | --- |
| 제작 | `Canvas`, `Deck`, 문서화된 레이어·효과 모델, 모션 트랙, 전환, 옵션 모델 |
| 문서 연산 | 두 문서 종류의 `validate()`, `inspect()`, `diagnose()`, `prefetch_assets()`, `sample()`, `export()`. 범용 처리에는 `inspect_document()` |
| 결과 | 자료형이 있는 보고서, `ExportResult`, `CanonicalFrame` / `FrameSequence`, `ImageSequence*` 결과. `model_dump_json()`으로 직렬화합니다. |
| JSON | `to_json()`, `Canvas.from_json()`, `Deck.from_json()`, `canvas_json_schema()`, `document_json_schema()` |
| 오디오 제작 | [`quickthumb.audio.analyze_audio()`와 `AudioAnalysis`](audio.md). 소스 시계 기준 시작점과 RMS 기반 크기를 숫자형 모션으로 기록합니다. |
| 전문 출력 | 반환 자료형이나 제어 방식이 작업에 맞을 때 사용하는 문서화된 `render()`, `render_frame()`, `to_*()`, `export_image_sequence()` 메서드 |

파일 출력에는 `export()`를 권장합니다. 기능 정책을 사전 검사하고 기록한 경로와 진단을 반환합니다.
전문 메서드는 자체 반환값을 가지며 모두 같은 정책을 적용하지는 않습니다.
[출력 API](../reference/export-methods.md#recommended-output-api)를 참고하세요.
내부 내보내기 함수를 직접 호출하지 말고, 이 API에 형식별 옵션을 전달하세요.

`_`로 시작하는 모듈, 렌더러·컨텍스트 객체, 타임라인 컴파일 도우미는 구현 세부 사항입니다.
지원 수명주기 없이 변경되거나 사라질 수 있습니다.
컴파일러와 렌더러를 직접 조율하는 대신 `sample()`로 프레임을 사용하세요.
레퍼런스와 생성된 스키마는 설치한 버전의 지원 필드를 설명합니다. 공개 인터페이스라고 해서 버전 사이에 고정된다는 뜻은 아닙니다.

### 하나의 문서 작업 흐름 { #one-document-workflow }

같은 레이어 데이터를 Python, 정규 JSON, Deck에서 사용합니다. 렌더러 객체나 선택 의존성이 필요하지 않습니다.

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

## 공통 레이어 용어 { #shared-layer-vocabulary }

Canvas 레이어는 Deck 슬라이드나 정규 JSON에서도 같은 필드를 사용합니다.
Deck은 슬라이드 순서, 전환, 내레이션, 메모를 추가하며 레이어 필드 이름을 바꾸지 않습니다.
Python 튜플은 JSON 배열로, 열거형 값은 문자열로 바뀌며 각 레이어에는 `type` 구분자가 있습니다.

| 필드 또는 개념 | 의미 |
| --- | --- |
| `id` | 그룹 하위 요소를 포함해 Canvas 장면 내에서 고유한 선택 식별자입니다. 각 Deck 슬라이드는 독립적인 ID 범위를 가집니다. |
| `motion_key` | Morph 전환에서 장면 사이를 대응시키는 선택 키입니다. 장면 로컬 `id`와 다릅니다. |
| `position`, `width`, `height` | 제작 시 지정하는 위치와 크기. 지원하는 레이어에서는 픽셀이나 백분율 문자열을 사용합니다. 백분율은 캔버스를 기준으로 해석합니다. 필수 필드와 크기 규칙은 각 레이어 문서를 참고하세요. |
| `align` | `position`에 놓이는 레이어 레이아웃 상자의 기준점이며 텍스트 정렬도 제어합니다. [Align](enums.md#align)을 참고하세요. |
| `rotation`, `anchor` | 회전은 도 단위입니다. `anchor=(x, y)`는 정규 모션의 0–1 정규화 피벗이며 레이아웃 정렬과 다릅니다. 정적 회전은 자체 프레임 규칙을 따릅니다. [변환 기준점](video.md#transform-anchors-and-independent-scale)을 참고하세요. |
| `opacity` | 지원되는 경우 0부터 1까지의 레이어 불투명도입니다. |
| `animation` | 자료형이 있는 트랙과 타이밍을 담은 프리셋 또는 `AnimationSpec`입니다. 위치 트랙은 제작 위치로부터의 오프셋입니다. 크기 트랙은 바깥 객체를 변환하고 `ImageZoomTrack`은 프레임 안의 이미지 콘텐츠를 바꿉니다. |
| 그룹 | 자동 레이아웃이 자식 배치를 담당합니다. 각 자식을 배치하기보다 `.group()`으로 행과 열을 구성하세요. |
| `parent` / null | 최상위 애니메이션 레이어를 위한 고급 장면 로컬 변환 계층입니다. 자식 배치는 부모 로컬이지만 백분율 좌표는 여전히 캔버스를 기준으로 합니다. 그룹 레이아웃과는 별개입니다. [부모 변환](video.md#parent-links-and-null-controllers)을 참고하세요. |

모든 레이어가 모든 필드를 받는 것은 아닙니다. 배경, 테두리, null, 그릴 수 있는 레이어는 역할이 다릅니다.
각 레퍼런스와 [JSON 스키마](../json-schema.md#published-schema)가 필드 수준의 계약입니다.
[플러그인 등록](../json-schema.md#plugin-layers)은 매개변수를 선언하고 명시적인 `PluginRegistry`를 통해 렌더링 콜백을 제공할 수 있습니다.
JSON을 파싱한다고 이 콜백을 패키징하거나 설치하지는 않습니다.

## 문서 목록 { #pages }

| 문서 | 다루는 내용 |
| --- | --- |
| [Canvas](canvas.md) | 캔버스 생성, 모든 레이어 메서드, 검사, 내보내기 메서드 |
| [Deck](deck.md) | 여러 캔버스를 하나의 PDF, PPTX, HTML 슬라이드쇼, 동영상, 이미지 시퀀스로 구성 |
| [문서 검사](inspection.md) | `inspect_document()`와 범용 Canvas/Deck 표본 처리 |
| [배경](background.md) | `.background()`: 색상, 그라디언트, 이미지 |
| [텍스트](text.md) | `.text()`와 `TextPart`: 텍스트와 서식 있는 텍스트 |
| [이미지](image.md) | `.image()`: 이미지 배치와 배경 제거 |
| [도형](shape.md) | `.shape()`: 사각형, 타원, 캡슐, 삼각형, 별, 다각형 |
| [경로](path.md) | `.path()`: 채움·선 SVG 경로 데이터와 제한된 모션 |
| [SVG](svg.md) | `.svg()`: SVG 파일의 아이콘과 로고 |
| [동영상](video.md) | `.video()`: 동영상 클립, 자막, 오디오 |
| [그룹](group.md) | `.group()`: 행과 열의 자동 레이아웃 |
| [테두리](outline.md) | `.outline()`: 캔버스 테두리 |
| [데이터 시각화](data-visualizations.md) | `.chart()`와 `.qr_code()` |
| [효과](effects.md) | `Stroke`, `Shadow`, `Glow`, `Filter`, `Background`, `Grain`, `Duotone`, `InnerShadow`, `BackdropBlur` |
| [열거형과 그라디언트](enums.md) | `Align`, `BlendMode`, `FitMode`, `LinearGradient`, `RadialGradient`, `TextFillImage` |

## 오류 종류 { #error-types }

| 예외 | 발생 시점 |
| --- | --- |
| `ValidationError` | 레이어 빌더에 잘못된 인수를 전달하면 즉시 발생합니다. |
| `RenderingError` | `.render()`, `.to_base64()`, `.to_data_url()` 중 실패하면 발생합니다. |
