---
description: quickthumb Canvas 생성, 종횡비, 레이어 구성, 렌더링, JSON 불러오기와 이미지 출력을 설명합니다.
---

# Canvas { #canvas }

`Canvas`는 캔버스 크기와 레이어를 담는 최상위 객체입니다. 레이어는 그리는 순서대로 관리합니다.
제작 필드는 Deck 슬라이드와 정규 JSON에도 적용되는 [공통 레이어 용어](index.md#shared-layer-vocabulary)를 따릅니다.

## 생성 { #creation }

### `Canvas(width=None, height=None)` { #canvaswidthnone-heightnone }

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720)
```

| 매개변수 | 자료형 | 설명 |
| --- | --- | --- |
| `width` | `int \| None` | 캔버스 너비(픽셀). 양의 정수여야 합니다. |
| `height` | `int \| None` | 캔버스 높이(픽셀). 양의 정수여야 합니다. |

너비와 높이는 함께 지정하거나 둘 다 생략해야 합니다.
크기 **없이** 생성한 `Canvas()`는 *크기 미지정* 상태입니다.
레이어 빌더는 사용할 수 있지만 크기를 직접 지정하거나 크기가 있는 [`Deck`](deck.md)에 추가해 Deck 기본 크기를 상속하기 전에는 렌더링, 진단, 직렬화할 수 없습니다.
`canvas.has_size`로 두 상태를 구별할 수 있습니다.

### `Canvas.from_aspect_ratio(ratio, base_width)` { #canvasfrom_aspect_ratioratio-base_width }

종횡비 문자열과 기준 너비로 캔버스를 만듭니다. 높이는 자동으로 계산합니다.

```python
wide     = Canvas.from_aspect_ratio("16:9", base_width=1280)   # 1280×720
square   = Canvas.from_aspect_ratio("1:1",  base_width=1080)   # 1080×1080
vertical = Canvas.from_aspect_ratio("9:16", base_width=1080)   # 1080×1920
```

| 매개변수 | 자료형 | 설명 |
| --- | --- | --- |
| `ratio` | `str` | `"16:9"` 같은 `"W:H"` 형식의 종횡비 문자열입니다. |
| `base_width` | `int` | 캔버스 너비(픽셀)입니다. |

## 레이어 빌더 { #layer-builders }

모든 빌더 메서드는 캔버스를 변경하고 `self`를 반환하므로 메서드를 이어서 호출할 수 있습니다.

| 메서드 | 설명 |
| --- | --- |
| `.background(...)` | 캔버스 전체를 덮는 배경 레이어 추가 |
| `.text(...)` | 텍스트 레이어 추가 |
| `.image(...)` | 오버레이 이미지 레이어 추가 |
| `.shape(...)` | 도형 레이어 추가 |
| `.path(...)` | 채움 또는 선이 있는 [경로](path.md) 그리기 |
| `.svg(...)` | 렌더링 시 래스터화하는 SVG 레이어 추가 |
| `.video(...)` | 애니메이션 구성에 [동영상 클립](video.md) 추가 |
| `.counter(...)` | [숫자 애니메이션](#animated-counters) 추가 |
| `.group(...)` | 자식 레이어의 자동 레이아웃 그룹 추가 |
| `.outline(...)` | 캔버스 테두리 추가 |
| `.chart(...)` | 자료형이 있는 차트 명세로 결정적인 막대·선 차트 레이어 추가 |
| `.qr_code(...)` | 정사각형 QR 코드 레이어 추가 |
| `.custom(fn)` | Pillow 콜백 레이어 추가 |

전체 매개변수는 [데이터 시각화 레퍼런스](data-visualizations.md)와 각 개별 레퍼런스를 참고하세요.

### 숫자 애니메이션 { #animated-counters }

`.counter(from_, to, duration, ...)`로 숫자를 텍스트 레이어로 애니메이션화합니다.
`position`, `size`, `color` 같은 일반 텍스트 옵션을 전달합니다.

```python
from quickthumb import Canvas

canvas = Canvas(320, 180).background(color="#102030").counter(
    0, 100, 2, suffix="%", size=64, color="#FFFFFF", position=(40, 50)
)
canvas.render("counter.gif")
```

`delay`, `decimals`, `minimum_integer_digits`, `prefix`, `suffix`, `grouping`은 타이밍과 형식을 제어합니다.
`style`은 `"plain"`, `"odometer"`, `"flip"`을 받고 `easing`은 `"linear"`, `"ease_in"`, `"ease_out"`, `"ease_in_out"`을 받습니다.
정적 출력은 최종 정착 값을 표시합니다.

## `.diagnose()` { #diagnose }

파일을 쓰지 않고 레이아웃과 가독성 문제를 검사합니다.
`Diagnostic` 항목을 담은 `findings` 목록이 있는 `DiagnosticReport`를 반환합니다. 문제가 없으면 목록은 비어 있습니다.

```python
for finding in canvas.diagnose().findings:
    print(finding.severity, finding.code, finding.message)
```

진단 코드는 `off-canvas`, `tiny-text`, `text-overflow`, `text-clipped`, `missing-glyph`, `low-contrast`, `layer-overlap`, `layer-hidden`, `edge-crowding`입니다.
자세한 설명과 같은 기능의 `quickthumb lint` 또는 `quickthumb diagnose`는 [진단과 CLI](../diagnostics.md)를 참고하세요.

## `.prefetch_assets()`(선택 사항) { #prefetch_assets-optional }

이 메서드를 반드시 호출할 필요는 없습니다.
`render()`와 `export()`가 원격 이미지, SVG, 텍스트 채우기, 글꼴을 직접 내려받으며 `export()`는 그 결과인 `asset_manifest`도 반환합니다.
긴 내보내기 전에 네트워크 실패나 오래된 캐시 항목을 확인하거나 이후 오프라인 렌더링을 위해 캐시를 미리 채울 때만 호출하세요.
렌더링하지 않고 매니페스트를 반환합니다.

```python
manifest = canvas.prefetch_assets().asset_manifest
if any(entry.status == "stale" for entry in manifest):
    ...  # decide whether to proceed with cached bytes
```

상태 값, `QUICKTHUMB_ASSET_MAX_AGE`, 오프라인 모드는 [원격 에셋과 캐시](../reference/export-assets.md#remote-assets-and-caching)를 참고하세요.

## 내보내기 메서드 { #export-methods }

### `.export(path, policy=None, *, format=None, quality=None, animation=None)` { #exportpath-policynone-formatnone-qualitynone-animationnone }

`render()`처럼 캔버스를 파일에 기록하고, 기록한 파일 하나가 `written_paths`에 담긴 `ExportResult`를 반환합니다.
경로는 문자열이나 `pathlib.Path`일 수 있습니다. `format`, `quality`, `animation`, `policy`의 의미는 `render()`와 같습니다.

```python
result = canvas.export("card.png")
print(result.written_paths)
```

결과 필드, 기능 사전 검사, 아래 메서드와의 관계는 [권장 출력 API](../reference/export-methods.md#recommended-output-api)를 참고하세요.

### `.render(path, format=None, quality=None, debug=False, animation=None, policy=None)` { #renderpath-formatnone-qualitynone-debugfalse-animationnone-policynone }

캔버스를 렌더링해 파일로 기록합니다. 형식은 파일 확장자로 감지합니다.
`.svg`, `.pptx`, `.pdf`는 벡터·문서 출력을 만들며 `.gif`, `.mp4`, `.webm`, `.mov`는 캔버스 레이어의 `animation` 효과를 재생하는 애니메이션을 만듭니다.
[SVG, PPTX, PDF와 동영상 내보내기](../exports.md)를 참고하세요.
Canvas의 `.lot` 출력은 [Lottie 벡터](../reference/export-lottie.md#lottie-vectors)에 설명된 제한된 네이티브 벡터 기능을 기록하며 `LottieOptions`로 fps와 마지막 유지 시간을 정합니다.
지원하지 않는 콘텐츠는 PNG 대체 표현 없이 쓰기 전에 거부합니다.

```python
from quickthumb import GifOptions, VideoOptions

canvas.render("output.png")
canvas.render("output.jpg", format="JPEG", quality=85)
canvas.render("output.webp", format="WEBP", quality=90)
canvas.render("debug.png", debug=True)  # raster output with public layer-id bboxes
canvas.render("output.svg")
canvas.render("output.pptx")  # requires quickthumb[pptx]
canvas.render("output.pdf")   # requires quickthumb[pdf]
canvas.render("output.gif")   # animated; .mp4/.webm/.mov require the ffmpeg binary
canvas.render(
    "preview.gif",
    animation=GifOptions(fps=8, max_size=(540, 960), colors=128),
)
canvas.render("preview.mp4", animation=VideoOptions(fps=30))
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `path` | `str` | — | 출력 파일 경로입니다. |
| `format` | `str \| None` | `None` | 대소문자를 구분하지 않는 래스터 인코딩 재정의. `"PNG"`, `"JPEG"`, `"WEBP"`이며 문서·애니메이션 확장자와 함께 쓰면 거부됩니다. |
| `quality` | `int \| None` | `None` | 압축 품질. JPEG는 1–95, WebP는 1–100이며 다른 대상은 거부합니다. |
| `debug` | `bool` | `False` | 시각적 검토를 위해 래스터 출력에 공개 레이어 ID의 경계 상자를 그립니다. |
| `animation` | `GifOptions \| VideoOptions \| LottieOptions \| None` | `None` | 형식별 옵션. GIF에는 `GifOptions`, MP4/WebM/MOV에는 `VideoOptions`, `.lot`에는 `LottieOptions`입니다. |
| `policy` | `ExportPolicy \| None` | `None` | 애니메이션·HTML·PPTX의 `reduced_motion` 같은 렌더러 정책입니다. `render()`와 `export()` 모두 쓰기 전에 `unsupported_motion`을 적용합니다. `export()`는 명시적으로 요청한 [정적 SVG 충실도 검사](../reference/export-validation.md#optional-static-svg-fidelity-report)를 보고합니다. |

!!! warning
    `format="PNG"`와 함께 `quality`를 전달하면 `RenderingError`가 발생합니다. 문서나 애니메이션 출력(`.svg`, `.pptx`, `.pdf`, `.html`, `.gif`, `.mp4`, `.webm`, `.mov`, `.lot`)에 `debug=True`를 전달해도 `RenderingError`가 발생합니다.

`GifOptions`, `VideoOptions`, `LottieOptions`는 `quickthumb`에서 가져올 수 있습니다.
`GifOptions`는 `fps`, `hold`, `matte`, `loop`, `max_size=(width, height)`, `colors`를 받습니다.
`VideoOptions`는 `fps`, `hold`, `matte`, `soundtrack=AudioTrack(...)`, `loop_audio`를 받습니다.
`VideoOptions(transparent=True)`는 VP9 WebM과 ProRes 4444 MOV의 알파를 보존합니다. 엄격한 불리언이며 기본값은 `False`입니다. 다른 출력 대상은 모두 이 옵션을 거부합니다.
두 옵션의 `hold`는 유한한 0 이상의 엄격한 값이며 기본 3초입니다. 기본값과 같으면 직렬화된 옵션에서 생략됩니다.
두 옵션은 렌더링에 `workers`(1–8의 엄격한 정수, 기본 1)와 `render_quality="standard"` 또는 `"high"`도 받습니다.
spawn 설정과 지원 입력은 [병렬 애니메이션 렌더링](../reference/export-frames.md#parallel-animated-rendering)을 참고하세요.
GIF 크기와 팔레트 옵션은 MP4/WebM/MOV에서 거부됩니다.

### `.to_svg(embed_fonts=False)` { #to_svgembed_fontsfalse }

캔버스를 SVG 문서 문자열로 반환합니다. `embed_fonts=True`이면 사용한 글꼴 파일을 `@font-face` 데이터 URL로 포함합니다.

```python
svg = canvas.to_svg(embed_fonts=True)
```

### `.to_pptx()` { #to_pptx }

편집 가능한 텍스트 상자와 자동 도형이 있는 슬라이드 한 장을 PowerPoint 파일 바이트로 반환합니다. `pptx` 추가 기능이 필요합니다.

```python
with open("deck.pptx", "wb") as f:
    f.write(canvas.to_pptx())
```

### `.to_pdf()` { #to_pdf }

캔버스를 PDF 파일 바이트로 반환합니다.
글꼴을 안전하게 포함할 수 있고 복잡한 문자 조형이 필요하지 않은 경우 네이티브 벡터 배경·도형과 선택 가능한 텍스트가 있는 한 페이지를 만듭니다.
지원하지 않는 텍스트는 픽셀이 정확히 일치하는 이미지 조각으로 포함합니다. `pdf` 추가 기능이 필요합니다.

```python
with open("card.pdf", "wb") as f:
    f.write(canvas.to_pdf())
```

### `.to_gif(...)` / `.to_mp4(...)` / `.to_webm(...)` / `.to_mov(...)` { #to_gif-to_mp4-to_webm-to_mov }

레이어의 `animation` 효과를 차례로 재생한 뒤 정착한 구성을 `hold`초 유지하는 애니메이션을 반환합니다.
[애니메이션 GIF와 동영상](../reference/export-animation.md#animated-gif-video)을 참고하세요.
애니메이션이 없는 캔버스는 한 프레임 GIF를 만듭니다.
`.to_mp4()`, `.to_webm()`, `.to_mov()`에는 `PATH`의 `ffmpeg` 바이너리나 `QUICKTHUMB_FFMPEG`로 지정한 바이너리가 필요합니다.

```python
gif_bytes = canvas.to_gif(fps=20, hold=3.0, loop=0, matte="#000000")
mp4_bytes = canvas.to_mp4(fps=30, hold=2.0, soundtrack="music.mp3")
webm_bytes = canvas.to_webm(fps=30, hold=2.0)
overlay_bytes = canvas.to_webm(fps=30, hold=2.0, transparent=True)
```

`.to_mp4()`, `.to_webm()`, `.to_mov()`는 동영상 길이에 맞춰 잘라 합치는 오디오 파일 `soundtrack`과 명시적인 재정의 `loop_audio`도 받습니다.
`AudioTrack(..., loop=True)`는 짧은 설정 트랙을 반복합니다. 기존 문자열 경로는 이전의 반복 기본 동작을 유지합니다.
GIF는 오디오를 담을 수 없습니다. 전체 매개변수 표는 [Deck API](deck.md)를 참고하세요.

모든 애니메이션 바이트 메서드는 키워드 전용 `workers=1`, `render_quality="standard"`를 받습니다. `"high"`는 슈퍼샘플링을 활성화합니다.
`.to_gif()`는 비율을 유지한 크기 조절용 `max_size=None`과 팔레트 크기 `colors=None`(지정 시 2–256)도 받습니다.
기존 위치 인수는 바뀌지 않습니다.

`.to_webm()`과 `.to_mov()`의 키워드 전용 `transparent` 플래그는 내보내기 매트만 생략하며 제작한 배경은 계속 보입니다.
코덱, 알파 디코딩, 전환 상세는 [투명 WebM](../reference/export-transparency.md#transparent-webm)을 참고하세요.

`.to_mov()`의 매개변수와 타이밍은 `.to_webm()`과 같으며 ProRes 4444 영상과 AAC 오디오로 고정됩니다.
홀수 크기와 1픽셀 크기를 유지합니다. 입력 RGBA는 8비트입니다. 알파를 16비트로 인코딩했다가 디코딩하면, 8비트 알파 값에서 한 단계 차이가 날 수 있습니다.
색상은 손실이 있는 4:4:4 YUV입니다. 측정한 변환 한계와 인코더 요구 사항은 [ProRes MOV](../reference/export-transparency.md#prores-4444-mov)를 참고하세요.
`render()`와 `export()`는 불투명·투명 출력 모두 `VideoOptions`와 `.mov`를 받습니다.

### `.export_image_sequence(output_directory, *, format="png", quality=None, matte=None, lossless=None, options=None, policy=None)` { #export_image_sequenceoutput_directory-formatpng-qualitynone-mattenone-losslessnone-optionsnone-policynone }

기존 부모 디렉터리 아래의 새 디렉터리에 애니메이션 타임라인을 독립된 PNG(기본), JPEG, WebP 파일과 `manifest.json`으로 기록합니다.
`ImageSequenceOptions(fps=30, hold=3, workers=1, render_quality="standard")`는 타이밍과 합성을 제어하며 메서드 키워드는 이미지 인코딩을 선택합니다.
JPEG는 기본 흰색의 불투명 매트 위 RGB를 사용하고 `quality=1..95`를 받습니다.
WebP는 알파를 보존하고 `lossless=True`를 받으며 손실 WebP는 품질 값을 받습니다.
PNG와 무손실 WebP는 렌더러의 RGBA8 픽셀을 정확히 보존합니다.
불투명 WebP 파일은 RGB로 디코딩될 수 있으며 매니페스트 모드는 논리적인 RGBA 디코딩을 설명합니다.
결과에는 실제 프레임 수, 타이밍, 인코딩, 목적지가 보고됩니다.
검증, 형식별 메타데이터, 덮어쓰지 않는 원자적 게시 방식은 [이미지 시퀀스](../reference/export-frames.md#image-sequences)를 참고하세요.

### `.to_base64(format="PNG", quality=None)` { #to_base64formatpng-qualitynone }

렌더링한 이미지를 base64 인코딩 문자열로 반환합니다.

```python
b64 = canvas.to_base64(format="PNG")
b64 = canvas.to_base64(format="WEBP", quality=90)
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `format` | `str` | `"PNG"` | 출력 형식. `"PNG"`, `"JPEG"`, `"WEBP"` 중 하나입니다. |
| `quality` | `int \| None` | `None` | 압축 품질. JPEG는 1–95, WebP는 1–100입니다. |

### `.to_data_url(format="PNG", quality=None)` { #to_data_urlformatpng-qualitynone }

렌더링한 이미지를 데이터 URL(`data:<mime>;base64,...`)로 반환합니다.

```python
url = canvas.to_data_url(format="JPEG", quality=90)
# → "data:image/jpeg;base64,..."
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `format` | `str` | `"PNG"` | 출력 형식. `"PNG"`, `"JPEG"`, `"WEBP"` 중 하나입니다. |
| `quality` | `int \| None` | `None` | 압축 품질. JPEG는 1–95, WebP는 1–100입니다. |

### `.inspect()` { #inspect }

레이어 ID, 순서, 표시 여부, 경계 상자, 제작된 텍스트 레이아웃 메타데이터가 담긴 결정적인 `CanvasInspection`을 반환합니다.
출력 파일은 만들지 않습니다. 크기를 측정하려고 기존 글꼴이나 이미지 파일을 읽을 수는 있지만, 부모 레이어를 그리는 파이프라인은 실행하지 않습니다.

```python
report = canvas.inspect()
for layer in report.layers:
    print(layer.id, layer.bbox)
```

부모로 연결된 장면의 경계는 애니메이션 프레임이 아닌 제작된 정적 레이아웃을 나타냅니다.
보수적으로 실제 칠해진 픽셀 밖까지 확장될 수 있습니다.
`canvas.render("debug.png", debug=True)`로 상자를 확인하세요.
클립, 마스크, 카운터, 부모 변환은 [복잡한 레이아웃 검사](../reference/inspection-details.md)를 참고하세요.

### `.to_json()` { #to_json }

캔버스를 JSON 문자열로 직렬화합니다.

```python
json_str = canvas.to_json()
```

`.custom(fn)` 레이어가 있으면 콜백을 직렬화할 수 없으므로 `ValidationError`가 발생합니다.

### `Canvas.from_json(json_str)` { #canvasfrom_jsonjson_str }

JSON 문자열에서 캔버스를 역직렬화합니다.

```python
canvas = Canvas.from_json(json_str)
```

!!! note
    `from_json()`은 Python dict가 아닌 **JSON 문자열**을 받습니다. dict가 있다면 먼저 `json.dumps(data)`를 사용하세요.

## `.custom(fn)` { #customfn }

Pillow `Image`를 받아 반환하는 콜백을 추가합니다.

```python
from PIL import ImageDraw
from quickthumb import Canvas

def draw_badge(image):
    d = ImageDraw.Draw(image)
    d.polygon([(70, 70), (240, 70), (155, 180)], fill="#FF3B30")
    return image

canvas = Canvas(512, 512).custom(draw_badge)
```

| 규칙 | 상세 |
| --- | --- |
| `fn`은 호출 가능해야 함 | `PIL.Image.Image`를 받습니다. |
| 반환값 | 변경한 같은 이미지, 같은 크기의 새 이미지 또는 `None`을 반환할 수 있습니다. |
| 오류 | 콜백 예외는 `RenderingError`로 감쌉니다. |
| 직렬화 | 사용자 정의 레이어는 JSON으로 직렬화할 수 **없습니다**. |
