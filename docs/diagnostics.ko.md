---
description: canvas.diagnose()로 레이아웃과 가독성 문제를 찾고 quickthumb CLI로 명세 검사, 렌더링, 변경 감시, 비교, 미리보기를 수행합니다.
---

# 진단과 CLI { #diagnostics-cli }

quickthumb는 파일을 렌더링하지 않고도 일반적인 레이아웃·가독성 문제를 검사합니다.
Python에서는 `canvas.diagnose()`, 터미널에서는 `quickthumb lint`를 사용합니다.

Python에서 검사하려면 아래 예제로 시작하세요. JSON 파일은 [CLI를 설치하고 `quickthumb lint`를 실행](#quickthumb-lint)합니다.
내보내기 의존성은 [`quickthumb doctor`](#quickthumb-doctor), 출력 기록은 [`quickthumb render`](#quickthumb-render)를 사용하세요.
자세한 진단 규칙과 나머지 CLI 명령은 아래에 있습니다.

## `canvas.diagnose()` { #canvasdiagnose }

`Diagnostic` 항목을 담은 `findings` 목록이 있는 `DiagnosticReport`를 반환합니다.
목록이 비어 있으면 검사 항목에 해당하는 문제가 발견되지 않은 것입니다. 모든 문제를 찾았다거나 디자인의 시각적 완성도가 보장된다는 뜻은 아니므로, 렌더링한 결과도 직접 확인하세요.

```python
from quickthumb import Canvas

with open("spec.json", encoding="utf-8") as f:
    canvas = Canvas.from_json(f.read())

for finding in canvas.diagnose().findings:
    print(finding.severity, finding.code, finding.message)
```

각 `Diagnostic`은 안정적이고 사람이 읽을 수 있는 필드와 자동화용 선택 구조화 필드를 제공합니다.

| 필드 | 자료형 | 설명 |
| --- | --- | --- |
| `code` | `str` | `"off-canvas"`, `"tiny-text"`, `"text-overflow"`, `"text-clipped"`, `"missing-glyph"`, `"low-contrast"`, `"layer-overlap"`, `"layer-hidden"`, `"edge-crowding"`, `"near-alignment"`, `"caption-safe-area"`, `"caption-timing"`, `"caption-overlap"`, `"caption-reading-time"`, `"clip-stretch"`, `"motion-path-unused-handle"` 중 하나 |
| `severity` | `str` | `"warning"` 또는 `"error"` |
| `layer_index` | `int` | `canvas.layers` 안의 문제 레이어 인덱스 |
| `message` | `str` | 측정값을 포함한 사람이 읽을 수 있는 설명 |
| `layer_id` | `str \| None` | `"layer:3"` 또는 그룹 자식의 `"layer:3:0"` 같은 안정적인 측정 레이어 ID |
| `layer_name` | `str \| None` | 레이어 모델이 제공하는 경우 레이어 이름 |
| `bbox` | `dict \| None` | `x`, `y`, `width`, `height`가 있는 캔버스 좌표계 경계 상자 |
| `related_layers` | `list[str]` | 진단에 관련된 레이어 ID |
| `measured` | `dict` | 대비율, 글꼴 크기, 캔버스 크기 같은 규칙별 원시 값 |
| `suggestion` | `str \| None` | 규칙이 제공할 수 있는 경우 수정 힌트 |

### 검사 항목 { #what-gets-checked }

| 코드 | 발생 조건 |
| --- | --- |
| `off-canvas` | 레이어 경계 상자의 일부 또는 전체가 캔버스 밖에 있음 |
| `motion-path-unused-handle` | 첫 위치 키프레임의 진입 핸들이나 마지막 키프레임의 진출 핸들에 인접 구간이 없음 |
| `tiny-text` | 텍스트 크기가 캔버스 높이의 2.5% 미만이라 썸네일 크기에서 읽기 어려울 가능성이 있음 |
| `text-overflow` | 단어 하나가 레이어의 `max_width`보다 넓어 줄바꿈할 수 없음 |
| `text-clipped` | 줄바꿈된 텍스트가 캔버스 또는 선언된 텍스트 상자를 벗어남 |
| `missing-glyph` | 선택한 글꼴이 일부 문자를 글리프 누락 표시로 렌더링함 |
| `low-contrast` | 아래에 합성된 레이어 대비 텍스트 색상의 대비율이 2.0 미만임 |
| `layer-overlap` | 보이는 두 레이어가 서로 가릴 정도로 크게 겹침 |
| `layer-hidden` | 표시 상태의 레이어가 뒤에 추가한 불투명 레이어에 완전히 가림 |
| `edge-crowding` | 보이는 레이어가 캔버스 안전 여백이나 플랫폼 오버레이에 너무 가까움 |
| `near-alignment` | 관련된 회전하지 않은 레이어의 측정된 x/y 시작점이 3픽셀 이내지만 정확히 맞지 않음 |
| `caption-safe-area` | 동영상 자막이 캔버스 안전 영역 여백 안에 있음 |
| `caption-timing` | 동영상 자막 종료 시각이 클립 종료 후라 표시되지 않음 |
| `caption-overlap` | 동영상 자막 두 개가 같은 시각과 렌더링된 배경을 공유함 |
| `caption-reading-time` | 표시 시간이 0.8초 미만이거나 초당 표시 열이 20개를 넘어 읽을 시간이 부족함. 한국어·일본어 같은 넓은 문자는 문자당 2열, 결합자·결합 표시는 0열로 셉니다. 클립보다 오래 지속되는 큐는 실제 보이는 구간으로 측정합니다. |
| `clip-stretch` | 클립이 원래 속도의 0.5배 미만 또는 2배 초과로 재생됨. 보통 장면에 맞춰 늘린 경우지만 의도적인 슬로모션·타임랩스도 같은 방식으로 보고됩니다. |

!!! tip "LLM과 함께 사용"
    새 디자인을 요청하기보다 진단을 구체적인 수정 사항으로 모델에 다시 전달하세요. [AI 작업 흐름](cookbook/ai-workflow.md)을 참고하세요.

근접 정렬 검사는 렌더링된 레이어 위치를 비교해 의도하지 않은 1–3픽셀 어긋남을 찾습니다.

!!! note "대비와 정렬 검사"
    - **대비 검사**는 텍스트 레이어의 `Background` 캡슐 효과를 포함해 아래의 합성 배경과 텍스트를 표본 비교합니다.
    - **근접 정렬**은 3px 이내로 거의 정렬된 레이어를 표시하므로 좌표를 추측하지 않고 정확히 맞출 수 있습니다.

## `quickthumb` CLI { #the-quickthumb-cli }

CLI에는 `cli` 추가 기능이 필요합니다.

```bash
pip install "quickthumb[cli]"
```

### `quickthumb inspect` { #quickthumb-inspect }

내보내기 파일을 쓰지 않고 Canvas나 Deck JSON 명세를 검사합니다.

```bash
quickthumb inspect spec.json
quickthumb inspect deck.json --format json
quickthumb inspect deck.json --target video --fps 24 --max-samples 100
quickthumb inspect spec.json --reduced-motion --var title="Hello"
```

텍스트 출력에는 순서가 있는 페이지·레이어 경계, 레이어별 모션 길이와 이벤트 수, 기능·대체 표현 행, 관찰된 에셋, 레이아웃 진단이 포함됩니다.
`--format json`은 `version`과 문서 `kind`를 포함해 Python의 [`inspect_document()` 결과](api/inspection.md)와 정확히 같은 구조를 출력합니다.
두 문서 종류가 같은 페이지 순서와 공통 필드를 사용하므로 스크립트가 입력 종류를 추측하지 않고 처리할 수 있습니다.

`--target`은 기능 계열(`raster`, `html`, `pptx`, `video`)을 선택하며 생략하면 네 계열 모두를 보고합니다.
`--fps`, `--max-samples`는 이미지 프레임 생성이 아닌 제한된 모션 속성 관찰을 제어합니다.
`--reduced-motion`은 접근성용 정적 정책을 검사합니다. `--var KEY=VALUE`는 다른 명세 명령과 같습니다.

검사 중 측정을 위해 글꼴·에셋을 해석하거나 미디어를 디코딩할 수 있습니다.
관찰된 에셋 상태를 보고하며 별도 사전 다운로드나 준비 상태 검사는 수행하지 않습니다.
모션 검사 길이는 인코딩된 동영상 길이가 아닙니다. 정규 프레임과 재생 타이밍은 Python `sample()` 타임라인을 사용하세요.

진단 결과는 참고 정보입니다. 경고가 있더라도 검사 자체가 성공하면 종료 코드는 `0`입니다.
입력·검증·에셋 누락 오류는 `1`, 빈 Deck의 모션 검사를 포함한 렌더링·내보내기 범주 오류는 `2`입니다.
JSON 출력에서는 기존 `{"errors": [...]}` 구조를 사용합니다.
진단을 통과 조건으로 쓰려면 `lint --fail-on`, 환경 준비 상태에는 `doctor`를 사용하세요.
`--fps abc` 같은 인수 파싱 오류는 여전히 Typer의 표준 텍스트를 stderr에 출력하고 `2`로 종료합니다.
JSON 오류 결과는 인수 파싱 이후에 적용됩니다.

### `quickthumb lint` { #quickthumb-lint }

JSON 명세에 `diagnose()`와 같은 검사를 수행합니다.

```bash
quickthumb lint spec.json
quickthumb lint spec.json --format json
quickthumb diagnose spec.json --format json
```

```text
[warning] layer 3: tiny-text: text size 14px is below 18px (2.5% of canvas height) ...
[warning] layer 4: low-contrast: text contrast ratio 1.47 against the layers below it ...
```

`--format json`으로 기계 판독형 결과를 출력합니다.

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

`lint`는 CI에서 사용할 수 있는 상태로 종료합니다.

| 종료 코드 | 의미 |
| --- | --- |
| `0` | 문제 없음 |
| `1` | 잘못된 명세: JSON·검증 오류, 에셋 누락, 잘못된 옵션 |
| `2` | 렌더링 실패 |
| `3` | 진단 항목 보고됨 |

`diagnose`는 `lint`의 별칭입니다. 두 명령은 같은 자동화 옵션을 받습니다.

```bash
quickthumb lint spec.json --fail-on error
quickthumb lint spec.json --ignore edge-crowding --ignore missing-glyph
```

기본값인 `--fail-on warning`은 남은 진단이 하나라도 있으면 3으로 종료합니다.
`--fail-on error`는 경고를 허용하되 오류가 있으면 실패하며 `--fail-on never`는 진단을 출력한 뒤 항상 0으로 종료합니다.
`--ignore`는 일치하는 진단 코드를 출력과 종료 상태 계산에서 모두 제외합니다.
`--format json`에서 유효하지 않은 명세는 추적 정보 대신 [구조화된 오류 상세](errors.md)의 `errors` 목록을 출력합니다.

JSON 입력에는 최상위 `kind` 구분자(`canvas` 또는 `deck`)가 필요합니다.
Deck 진단에는 `slide_index`가 포함되며 원래 레이어 ID, 경계 상자, 측정값, 관련 레이어, 제안도 유지됩니다.

### `quickthumb diff` { #quickthumb-diff }

시각적 변경을 받아들이기 전에 렌더링 이미지와 기준 이미지를 비교합니다.

```bash
quickthumb diff golden.png output.png
quickthumb diff golden.png output.png --format json --output diff.png
```

평균 지각 해시와 픽셀 단위 지표를 조합합니다.
기본적으로 채널별 차이가 2 이하면 무시하지만 한 픽셀이라도 허용 오차를 넘으면 비교가 실패합니다.
기본 지각 해시 유사도 기준은 `0.95`입니다. 렌더러에 맞춰 값을 엄격하게 또는 느슨하게 조절하세요.

```bash
quickthumb diff golden.png output.png \
  --threshold 0.98 \
  --pixel-tolerance 1 \
  --max-diff-ratio 0.005
```

CI나 에이전트 파이프라인은 `--format json`을 사용하세요.
`--max-diff-ratio`로 일부 픽셀의 차이를 허용할 수 있으며 `--output`은 시각적 검토용 차이 이미지를 기록합니다.
종료 코드는 다음과 같습니다.

| 종료 코드 | 의미 |
| --- | --- |
| `0` | 설정한 허용 오차 안에서 일치 |
| `1` | 이미지가 다르거나 입력이 잘못되었거나 출력을 쓸 수 없음 |

같은 비교를 Python 단언문으로도 사용할 수 있습니다.

```python
from quickthumb import assert_image_similar

assert_image_similar(
    "golden.png",
    "output.png",
    threshold=0.95,
)
```

단언문은 호출자가 더 자세히 보고할 수 있도록 이미지 크기, 변경된 픽셀 수, 정규화 평균 오차, 지각 해시, 유사도 지표가 있는 `ImageDiff`를 반환합니다.

### `quickthumb render` { #quickthumb-render }

JSON 명세를 이미지 파일로 렌더링합니다.

```bash
quickthumb render spec.json -o thumbnail.png
quickthumb render spec.json -o thumbnail.webp --format WEBP --quality 90
quickthumb render spec.json -o debug.png --debug
```

| 옵션 | 설명 |
| --- | --- |
| `-o, --output` | 출력 파일 경로. 기본값은 `output.png`입니다. |
| `--format` | `PNG`, `JPEG`, `WEBP` |
| `--quality` | 압축 품질. JPEG는 1–95, WebP는 1–100이며 렌더링 품질 설정이 아닙니다. |
| `--debug` | 래스터 출력에 공개 레이어 ID 경계 상자 표시 |
| `--var KEY=VALUE` | 명세의 `$KEY` 자리표시자 치환. 반복 사용 가능 |
| `--error-format` | 기본 `text` 또는 `json`. [구조화된 오류](errors.md)를 참고하세요. |

`render`는 명세 오류, 에셋 누락, 잘못된 옵션에 `1`, 지원하지 않는 출력 형식 같은 내보내기 실패에 `2`로 종료합니다.

### `quickthumb watch` { #quickthumb-watch }

파일이 바뀔 때마다 명세를 다시 렌더링하므로 레이아웃을 직접 조절할 때 편리합니다.

```bash
quickthumb watch spec.json -o preview.png
```

`watch`는 `--error-format`을 제외한 `render` 옵션을 동일하게 받습니다.
실패는 텍스트로 출력하며 감시는 계속됩니다.

### `quickthumb doctor` { #quickthumb-doctor }

내보내기 전에 패키지, 도구, 소스 요구 사항, 출력 권한을 확인합니다.

```bash
quickthumb doctor pdf -o out/thumbnail.pdf
quickthumb doctor mp4 --spec spec.json --format json
```

워크플로는 `png`, `jpeg`, `webp`, `gif`, `svg`, `html`, `pdf`, `pptx`, `mp4`, `webm`, `mov` 중 하나입니다.
`--spec`을 사용하면 명세의 플러그인 렌더러, 글꼴, SVG·동영상 레이어, 배경 제거, 원격 에셋의 요구 사항도 더합니다.
`-o`는 아무것도 생성하지 않고 출력 위치에 쓸 수 있는지 확인합니다.

각 항목은 `ok`, 누락된 글꼴이나 사용할 수 없는 에셋 캐시 같은 선택적 제한인 `warning`, 필수 실패인 `error` 중 하나입니다.
필수 실패에는 누락된 `quickthumb[pdf]`, ffmpeg, 미등록 플러그인, 쓸 수 없는 출력이 해당합니다.
모든 경고와 오류는 `fix`/`remedy`를 포함합니다.
플러그인은 CLI 프로세스의 레지스트리로 검사하므로 가져오기 시점에 등록된 플러그인만 알 수 있습니다.
따라서 코드에서 등록한 플러그인을 사용하는 명세는 미등록으로 보고됩니다.
필수 검사 실패가 없으면 종료 코드 `0`, 있으면 `1`입니다.

성공한 보고서는 내보내기나 충실도 인증서가 아닙니다.
패키지를 발견했다고 네이티브 Cairo가 로드된다는 보장은 없으며 FFmpeg를 찾았다고 필요한 인코더가 빌드에 있다는 보장도 없습니다.
`doctor`는 결과를 렌더링하거나 비교하지 않습니다.
실제 내보내기를 실행하고 결과와 파일을 검사하세요. 시각적 비교가 중요하면 명시적 충실도 정책이나 `quickthumb diff`를 사용하세요.

### `quickthumb serve` { #quickthumb-serve }

실시간 새로고침이 있는 로컬 HTML 슬라이드쇼 서버를 실행합니다.
소스 인수가 없으면 `slides.py`, `slides.json`, `slides.html`, `slides.htm` 순으로 찾습니다.

```bash
quickthumb serve
quickthumb serve examples/investor_deck.py
quickthumb serve deck.json --port 4040 --no-open
```

Python 소스는 모듈 수준의 `deck`, `slides`, `canvas` 중 하나로 `Deck` 또는 `Canvas`를 정의해야 합니다.
JSON 소스는 `kind: "canvas"` 또는 `kind: "deck"`를 선언해야 합니다.
Canvas에는 `layers`, Deck에는 최상위 `slides` 목록이 있습니다.
`--host`, `--port`로 수신 주소를 바꾸고 `--no-open`으로 처음 브라우저를 여는 동작을 생략하며 `--var KEY=VALUE`를 반복해 JSON 템플릿을 치환할 수 있습니다.

청중 화면은 `/`이며 `?presenter` 쿼리로 발표자 모드를 선택합니다.

```text
http://localhost:3030/?presenter
```

발표자 모드는 미리보기와 같은 밝은 테마를 사용합니다.
왼쪽에는 현재 슬라이드와 메모, 오른쪽에는 다음 슬라이드와 일시 정지·재개·초기화 타이머, 아래에는 탐색 기능이 있습니다.
슬라이드 미리보기는 원래 종횡비를 유지합니다.
탐색과 슬라이드별 애니메이션 진행 상황은 같은 서버에서 연 청중 탭에 전달되고 새로고침 후 복원됩니다.
청중 화면에서만 수행한 탐색은 해당 화면에만 적용됩니다.
Python의 `.slide(canvas, notes="...")` 또는 JSON 슬라이드의 `notes` 문자열로 메모를 추가하세요.

### 타임라인 탐색기 { #timeline-scrubber }

Python 또는 JSON 문서를 제작하면서 래스터 타임라인을 엽니다.

```bash
quickthumb serve examples/timeline_preview.py --timeline
quickthumb serve deck.json --timeline --no-open
```

일반 `serve` 세션에서도 `http://localhost:3030/timeline`로 타임라인을 열 수 있습니다.
기본 화면은 슬라이드 탐색, 클릭으로 시작하는 애니메이션, 동기화된 발표자 제어가 있는 HTML 프레젠테이션입니다.
프레젠테이션과 모션 검사는 같은 슬라이드 선택과 썸네일 탐색을 공유합니다.
프레젠테이션은 원래 종횡비로 슬라이드를 중앙에 두며 모션 검사는 아래에 프레임 탐색 패널을 엽니다.
발표자는 동기화된 발표자 화면, 발표는 전체 화면 HTML 슬라이드를 엽니다.
모션 안내는 HTML 출력이 정적이거나 근사화된 경우를 설명합니다.
이 제어는 로컬 제작 도구이며 내보낸 HTML에 추가되지 않습니다.
독립 HTML에는 표본을 추출할 원본 문서가 없으므로 타임라인에는 Python이나 JSON 소스를 사용하세요.

검사 화면에서는 내보내기 렌더러가 만든 프레임을 살펴볼 수 있습니다. 재생이나 오디오, 편집 기능은 제공하지 않습니다. 이 화면에서 프레임을 탐색해도 발표자 화면과 청중 화면의 동기화 위치는 바뀌지 않습니다.

- 시간 슬라이더를 끌거나 초를 입력하거나 슬라이드·전환·모션 경계를 클릭합니다.
- **Proxy**는 가장 긴 변을 640픽셀로 제한합니다. 예를 들어 1080×1920은 360×640이 됩니다. 재사용 가능한 레이어 이미지를 준비하고 축소된 표면에서 일반 모션을 합성합니다. 뒤의 다른 크기 슬라이드도 같은 출력 사각형에 맞춥니다.
- **Full**은 `Canvas.sample(time=...)` / `Deck.sample(time=...)`와 같은 표준 품질 정규 타임라인 샘플러로 첫 슬라이드 원래 크기를 보여 줍니다.
- 소스를 저장하면 URL 조각에 선택한 해상도와 시각을 보존해 타임라인을 다시 불러옵니다. 새 타임라인이 짧으면 시각을 범위 안으로 제한합니다.
- 브라우저 프레임 요청은 한 번에 하나만 실행됩니다. 빠르게 탐색하면 대기 작업을 최신 선택으로 대체합니다. 요청한 프레임이 준비될 때까지 표시 프레임 라벨은 이전 프레임을 가리킵니다. 잘못된 편집은 오류를 표시하고 다음 저장 후 복구됩니다.

타임라인 탐색기는 내보내기 타이밍에 맞는 순간 프레임 미리보기를 렌더링합니다.

- **Proxy 모드**: 빠르고 부드러운 탐색용으로 최대 640px의 축소 프레임을 렌더링합니다.
- **Full 모드**: 표준 내보내기 품질과 일치하는 전체 해상도 프레임을 렌더링합니다.
- 타임라인 탐색 중에는 오디오 재생이 비활성화됩니다.

!!! tip "로컬 보안"
    `quickthumb serve`는 컴퓨터에서 로컬 Python과 JSON 파일을 실행합니다. 신뢰할 수 없는 콘텐츠를 미리 볼 때는 기본 루프백 주소인 `127.0.0.1`을 유지하세요.

### 변수 치환 { #variable-substitution }

JSON 기반 명령은 파싱 전에 `$KEY` 또는 `${KEY}` 자리표시자를 채우는 `--var`를 받습니다.

```bash
quickthumb render template.json -o ep42.png \
  --var TITLE="EPISODE 42" \
  --var ACCENT="#B8FF00"
```

해결되지 않은 자리표시자는 종료 코드 `1`을 발생시킵니다.
`$theme.*` 참조는 변수가 아니며 명세 자체의 [테마 블록](json-schema.md#theme-tokens)이 해석합니다.
