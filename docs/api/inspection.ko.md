---
description: Canvas와 Deck을 같은 결과 형식으로 검사하고 기준 샘플을 페이지 레이아웃과 연결합니다. 결과는 JSON으로 저장할 수 있으며 문서 종류에 따라 코드를 나눌 필요가 없습니다.
---

# 문서 검사와 표본 추출 { #document-inspection-and-sampling }

Canvas와 Deck을 모두 다루는 도구나 에이전트에는 `inspect_document()`를 사용하세요.
기존 레이아웃, 모션, 진단 보고서와 관찰된 에셋 매니페스트를 `DocumentInspection` 결과에 모읍니다.

```python
from quickthumb import Canvas, Deck, inspect_document

document = Deck(slides=[Canvas(320, 180).background(color="#FFFFFF")])
report = inspect_document(document, target="video", fps=24, max_samples=100)
print(report.model_dump_json(indent=2))

for page_index, page in enumerate(report.pages):
    print(page_index, page.width, page.height, len(page.layers))
```

## 공통 필드 { #common-fields }

| 필드 | 두 문서 종류에 공통인 의미 |
| --- | --- |
| `version` | 결과 스키마 버전. 현재는 `"1"`입니다. |
| `kind` | 소스 문서 구분자. `"canvas"` 또는 `"deck"`입니다. |
| `width`, `height` | 애니메이션 출력 무대와 같은 첫 페이지의 픽셀 크기입니다. |
| `pages` | Canvas는 `CanvasInspection` 하나, Deck은 문서 순서의 모든 슬라이드입니다. |
| `motion` | 타이밍, 표본 속성 상태, 슬라이드별 상세, 기능 행, 내보내기 진단을 포함한 기존 `MotionInspection`입니다. |
| `diagnostics` | 기존 `DiagnosticReport`입니다. Deck 항목은 문서 전체 항목의 `null`을 포함해 `slide_index`를 유지합니다. |
| `asset_manifest` | 관찰된 에셋 참조, 해석 상태, 사용 가능한 식별자·해시·캐시 정보입니다. |

각 페이지는 레이어 ID, 순서, 중첩된 자식, 경계 상자, 텍스트 측정값을 유지합니다.
크기가 섞인 Deck 페이지는 각자의 크기를 유지합니다.
결과의 최상위 크기는 첫 페이지를 기준으로 합니다. 작성한 Deck의 기본 크기와 다를 수도 있습니다. 기존 `deck.inspect()`는 이와 달리 작성 시 지정한 기본 크기를 그대로 보고합니다.

`target`에는 내보내기 계열 하나(`raster`, `html`, `pptx`, `video`), 계열의 이터러블, 또는 네 계열 모두를 뜻하는 `None`을 전달합니다.
`policy`, `fps`, `max_samples`는 변경 없이 `inspect_motion()`으로 전달됩니다.
모션 관찰은 `max_samples`로 제한되며 래스터 프레임이 아닌 속성 상태입니다.
빈 Deck이나 올바르지 않은 옵션은 기존의 구조화된 Quickthumb 오류를 발생시킵니다.

호출은 내보내기 파일을 쓰지 않습니다.
개별 검사·진단 메서드처럼 측정을 위해 글꼴을 불러오거나 에셋을 해석하거나 미디어를 디코딩할 수 있습니다.
매니페스트는 작업 후 상태를 설명하며 별도의 사전 다운로드를 시작하거나 해석되지 않은 리소스가 사용 가능하다고 보증하지 않습니다.
명시적인 해석이 필요하면 `prefetch_assets()`, 환경 준비 여부를 확인하려면 `doctor`를 사용하세요.

`canvas.inspect()`와 `deck.inspect()`는 기존 결과 자료형과 JSON 필드를 유지합니다.
레이아웃만 필요하면 이처럼 범위가 좁은 메서드를 사용하세요.

`DocumentInspection.model_json_schema()`는 이 결과 구조를 설명합니다.
문서 제작 스키마는 여전히 이 결과가 아닌 입력 명세를 설명합니다.
`DiagnosticReport`처럼 진단 항목도 역직렬화하면 일반 JSON 객체가 됩니다.
JSON 왕복 후 Python 진단 클래스에 의존하기보다 `code`, `severity`, `message`, 위치 필드를 읽으세요.

## 정규 표본과 레이아웃 연결 { #join-canonical-samples-to-layout }

두 문서 종류의 `sample()`은 이미 같은 `FrameSequence`를 반환합니다.
균일한 표본 격자는 인코딩된 프레임 인덱스가 아닌 관찰 시계입니다.
GIF/동영상 양자화와 내레이션의 차이는 [애니메이션 타이밍](../timing.md)을 참고하세요.
페이지 인덱스는 0부터 시작하며 `frames[].slide`, `timeline[].slide`와 일치합니다.

```python
from quickthumb import DocumentInspection, FrameSequence

layout = DocumentInspection.model_validate_json(report.model_dump_json())
samples = FrameSequence.model_validate_json(document.sample().model_dump_json())
for frame in samples.frames:
    page = layout.pages[frame.slide]
    print(frame.index, frame.time, frame.width, frame.height, len(page.layers))
```

이 루프는 문서 종류에 따라 분기할 필요가 없습니다.
`kind`는 여전히 소스를 식별하며 페이지별·프레임별 세부 정보도 모두 사용할 수 있습니다.

- `sample()`은 페이지별로 고유 크기와 투명도를 유지하는 제작된 정적 RGBA 프레임 하나를 캡처합니다. `time`은 `None`, `duration`은 0, `timeline`은 빈 목록입니다.
- `sample(time=[0, 0.5])`나 `sample(fps=24)`는 애니메이션 타임라인을 캡처합니다. 시간순 프레임, 첫 페이지 무대 크기, 불투명 매트를 사용합니다.
- `frames[].index`는 관찰 순서를, `frames[].slide`는 활성 페이지를 나타냅니다. 타임라인 구간은 페이지 타이밍과 전환을 설명합니다.
- `environment`는 렌더러 버전을 기록합니다. 각 프레임에는 해당 환경에서 결정적으로 비교할 수 있도록 원시 RGBA 데이터와 SHA-256 다이제스트가 포함됩니다.

시간 값은 목적에 따라 구분해야 합니다. `report.motion.duration`은 기존 모션 검사와 마찬가지로 작성된 모션의 길이를 나타냅니다.
`samples.duration`은 `hold` 인수와 해석된 내레이션 타이밍을 포함한 정규 캡처 길이입니다.
예를 들어 정적 Canvas의 모션 길이는 0이지만 `hold=2`로 시간을 지정한 표본은 2초 동안 지속됩니다.
재생을 비교할 때는 표본의 `duration`, `fps`, `timeline`, 프레임 `time`을 사용하세요.
레이아웃 보고서나 모션 속성 표본에서 이 값을 추측하지 마세요.
