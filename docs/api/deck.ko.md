---
description: 캔버스를 여러 페이지 PDF, PPTX, HTML 슬라이드쇼, 동영상, 번호가 붙은 이미지 시퀀스로 모으는 quickthumb Deck을 설명합니다.
---

# Deck { #deck }

`Deck`은 순서가 있는 `Canvas` 슬라이드 모음입니다.
각 슬라이드는 개별적으로 렌더링할 때와 동일하게 그려지며 Deck은 같은 파이프라인에 여러 출력 형식의 내보내기를 더합니다.
슬라이드는 Canvas의 [레이어 용어와 장면 로컬 ID](index.md#shared-layer-vocabulary)를 유지합니다.

## 생성 { #creation }

### `Deck(width=None, height=None, slides=None, theme=None)` { #deckwidthnone-heightnone-slidesnone-themenone }

```python
from quickthumb import Canvas, Deck

deck = Deck()                          # empty, no default size
deck = Deck(1280, 720)                 # default slide size for unsized slides
deck = Deck(slides=[cover, body])      # from pre-built canvases
```

| 매개변수 | 자료형 | 설명 |
| --- | --- | --- |
| `width` | `int \| None` | 기본 슬라이드 너비. `height`와 함께 지정하거나 둘 다 생략합니다. |
| `height` | `int \| None` | 기본 슬라이드 높이입니다. |
| `slides` | `list[Canvas] \| None` | 순서대로 넣을 초기 슬라이드. 각 항목은 `Canvas`여야 합니다. |
| `theme` | `dict \| None` | 모든 슬라이드의 `$theme.*` 참조가 공유하는 토큰 그룹입니다. 슬라이드 수준 테마가 우선하며 `to_json()`/`from_json()` 왕복에서도 보존됩니다. |

### `Deck.from_aspect_ratio(ratio, base_width)` { #deckfrom_aspect_ratioratio-base_width }

`Canvas.from_aspect_ratio`처럼 종횡비 문자열로 기본 슬라이드 크기가 정해진 Deck을 만듭니다.

```python
deck = Deck.from_aspect_ratio("16:9", 1280)   # default 1280×720
```

## 슬라이드 추가 { #adding-slides }

생성자에 `Deck(slides=[...])`로 초기 슬라이드를 전달하거나 `.slide(canvas, transition=None, *, audio=None, duration=None, notes=None)`로 하나씩 추가합니다.
이 메서드는 Deck을 변경하고 연속 호출을 위해 `self`를 반환합니다.
Deck에 기본 크기가 있으면 **크기 미지정** `Canvas()`는 이를 상속합니다.
크기를 명시한 캔버스는 자신의 크기를 유지하며 기본 크기와 다르면 `mixed-slide-size` 경고가 발생합니다.

| 메서드 | 설명 |
| --- | --- |
| `.slide(canvas, transition=None, *, audio=None, duration=None, notes=None)` | `Canvas` 하나를 추가합니다. 선택적인 오디오·길이는 내레이션을 설정하며 메모는 HTML 발표자 모드에만 표시됩니다. |

```python
deck = (
    Deck(1280, 720)
    .slide(
        Canvas().background(color="#101820").text(content="Cover", size=96, color="#FFFFFF"),
        audio="voice.wav",
        duration=2.5,
        notes="Introduce the central thesis.",
    )
    .slide(Canvas().background(color="#1A1A2E").text(content="Body", size=64, color="#FFFFFF"))
)
```

기본 크기가 없는 Deck에 크기 미지정 캔버스를 추가하면 `ValidationError`가 발생합니다.
Deck이나 캔버스에 크기를 지정하세요.

Deck은 시퀀스이므로 `len(deck)`, `deck[i]`, 슬라이드 반복을 모두 사용할 수 있습니다.
`deck.slides`와 `deck.notes`는 순서가 맞춰진 슬라이드·발표자 메모 목록의 복사본을 반환하므로 반환된 목록을 바꿔도 Deck은 변하지 않습니다.

## 내보내기 메서드 { #export-methods }

### `.export(path, policy=None, *, format=None, quality=None, animation=None)` { #exportpath-policynone-formatnone-qualitynone-animationnone }

`render()`처럼 Deck을 기록하고 `ExportResult`를 반환합니다.
`written_paths`에는 래스터 출력의 번호가 붙은 슬라이드 파일들 또는 PDF, PPTX, HTML, 애니메이션 파일 하나가 담깁니다.
경로는 문자열이나 `pathlib.Path`일 수 있으며 `format`, `quality`, `animation`, `policy`의 의미는 `render()`와 같습니다.

```python
result = deck.export("slides.png")
print(result.written_paths)
```

결과 필드, 기능 사전 검사, 아래 메서드와의 관계는 [권장 출력 API](../reference/export-methods.md#recommended-output-api)를 참고하세요.

### `.render(path, format=None, quality=None, animation=None, policy=None)` { #renderpath-formatnone-qualitynone-animationnone-policynone }

출력 확장자에 맞춰 Deck을 렌더링합니다. 기록한 파일 경로 목록을 반환합니다.

```python
from quickthumb import GifOptions, VideoOptions

deck.render("deck.pdf")      # one multi-page PDF (a page per slide)
deck.render("deck.pptx")     # one multi-slide PPTX (a slide per slide)
deck.render("deck.gif")      # one animation playing transitions between slides
deck.render(
    "preview.gif",
    animation=GifOptions(fps=8, max_size=(540, 960), colors=128),
)
deck.render("deck.html")     # one self-contained HTML slideshow
deck.render("slides.png")    # slides_01.png, slides_02.png, …
deck.render("slides.jpg", quality=85)
```

| 확장자 | 동작 |
| --- | --- |
| `.pdf` | 여러 페이지 PDF 하나. `pdf` 추가 기능이 필요합니다. |
| `.pptx` | 여러 슬라이드 PPTX 하나. `pptx` 추가 기능이 필요합니다. |
| `.gif` / `.webm` / `.mov` | 기본 설정으로 레이어 애니메이션과 슬라이드 전환을 재생하는 애니메이션 하나. WebM과 MOV에는 `ffmpeg`가 필요하고 MOV는 `prores_ks`를 사용합니다. |
| `.mp4` | 선택적인 슬라이드별 내레이션이 있는 애니메이션 타임라인. H.264/yuv420p 영상과 AAC 오디오입니다. `ffmpeg`와 내레이션용 `ffprobe`가 필요합니다. 정지 슬라이드는 정적 캔버스와 `Cut()` 전환을 사용하세요. |
| `.html` / `.htm` | 자체 포함된 애니메이션 HTML 슬라이드쇼 하나입니다. |
| `.png` / `.jpg` / `.jpeg` / `.webp` | 0으로 채운 번호가 붙은 슬라이드별 파일입니다. |

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `path` | `str` | — | 출력 경로. 래스터 이름은 `<stem>_NN<ext>`가 됩니다. |
| `format` | `str \| None` | `None` | 대소문자 구분 없는 래스터 인코딩 재정의(`"PNG"`, `"JPEG"`, `"WEBP"`). 문서·애니메이션 확장자와 함께 쓰면 거부됩니다. |
| `quality` | `int \| None` | `None` | 압축 품질. JPEG는 1–95, WebP는 1–100이며 다른 대상은 거부합니다. |
| `animation` | `GifOptions \| VideoOptions \| None` | `None` | 형식별 옵션. GIF에는 `GifOptions`, MP4/WebM/MOV에는 `VideoOptions`입니다. |
| `policy` | `ExportPolicy \| None` | `None` | 애니메이션·HTML·PPTX의 `reduced_motion` 같은 렌더러 정책입니다. `render()`와 `export()` 모두 쓰기 전에 `unsupported_motion`을 적용합니다. |

!!! warning
    `.pdf`, `.pptx`, 애니메이션 출력에 `quality`를 전달하거나 빈 Deck을 렌더링하면 `RenderingError`가 발생합니다.

`GifOptions`와 `VideoOptions`는 `quickthumb`에서 가져옵니다.
`GifOptions`는 GIF 프레임률, `hold`, 반복 횟수, 매트, 비율을 유지한 `max_size`, 팔레트 `colors`를 제어합니다.
`VideoOptions`는 MP4/WebM/MOV 프레임률, `hold`, 매트, 사운드트랙, 오디오 반복을 제어합니다.
사운드트랙은 `AudioTrack(path="music.mp3", loop=True)`로 전달하세요.
`VideoOptions(transparent=True)`는 VP9 WebM이나 ProRes 4444 MOV의 알파를 보존합니다. 엄격한 불리언이고 기본값은 `False`이며 다른 출력 대상은 모두 이 옵션을 거부합니다.
두 옵션의 `hold`는 유한한 0 이상의 엄격한 값이며 기본값은 3초입니다. 기본값과 같으면 직렬화된 옵션에서 생략됩니다.
두 옵션 모두 렌더링에 `workers`(1–8의 엄격한 정수, 기본 1)와 `render_quality="standard"` 또는 `"high"`를 받습니다.
spawn 설정과 지원 입력은 [병렬 애니메이션 렌더링](../reference/export-frames.md#parallel-animated-rendering)을 참고하세요.
다른 애니메이션 형식의 전용 옵션을 전달하면 거부됩니다.

### `.to_html()` { #to_html }

자체 포함된 슬라이드쇼 문서를 반환합니다. 일반 청중 화면에서는 클릭, Space, 방향키로 탐색할 수 있습니다.
`quickthumb serve`에서 `?presenter` 쿼리로 문서를 열면 현재·다음 슬라이드 대시보드, 발표자 메모, 일시 정지·재개·초기화 타이머, 동기화된 청중 제어가 추가됩니다.

```python
html = deck.to_html()
deck.render("slides.html")
```

개발 중에는 `quickthumb serve slides.py`를 사용하세요.
Python 소스는 모듈 수준의 `deck`, `slides`, `canvas` 변수 중 하나로 Deck을 노출합니다.

### `.to_pdf()` / `.to_pptx()` { #to_pdf-to_pptx }

캔버스마다 한 페이지·슬라이드가 있는 문서 바이트를 반환합니다.

```python
with open("deck.pdf", "wb") as f:
    f.write(deck.to_pdf())   # requires quickthumb[pdf]
pptx_bytes = deck.to_pptx()  # requires quickthumb[pptx]
```

### `.to_gif(...)` / `.to_webm(...)` / `.to_mov(...)` { #to_gif-to_webm-to_mov }

Deck을 애니메이션으로 반환합니다. 각 슬라이드는 레이어 애니메이션을 재생한 뒤 정착 상태를 유지하며, 해당 슬라이드의 전환이 진입 변화를 애니메이션화합니다.
타이밍 모델은 [애니메이션 GIF와 동영상](../reference/export-animation.md#animated-gif-video)을 참고하세요.
`.to_webm()`과 `.to_mov()`에는 `PATH`의 `ffmpeg` 또는 `QUICKTHUMB_FFMPEG`로 지정한 바이너리가 필요합니다.

```python
gif_bytes = deck.to_gif(fps=20, hold=3.0, loop=0, matte="#000000")
webm_bytes = deck.to_webm(fps=30, hold=3.0)
overlay_bytes = deck.to_webm(fps=30, hold=3.0, transparent=True)
```

모든 애니메이션 바이트 메서드는 키워드 전용 `workers=1`, `render_quality="standard"`를 받습니다. `"high"`는 슈퍼샘플링을 활성화합니다.
`.to_gif()`는 비율을 유지한 크기 조절용 `max_size=None`, 팔레트 크기 `colors=None`(지정하면 2–256)도 받습니다.
기존 위치 인수는 바뀌지 않습니다.

이 제어는 `.to_mp4()`에도 적용됩니다. 정적인 내레이션 슬라이드는 정적 캔버스와 `Cut()`을 사용하세요.
파일 옵션과 바이트 메서드 모두 `hold`를 사용합니다.
슬라이드에 내레이션과 명시적인 길이가 모두 없으면 애니메이션 동영상에는 양수 기본 유지 시간이 필요합니다.
Deck GIF와 무음 이미지 시퀀스에서는 0도 유효합니다. Deck GIF는 슬라이드별 내레이션과 명시적 길이를 무시합니다.

`.to_webm()`과 `.to_mov()`의 키워드 전용 `transparent` 플래그는 내보내기 매트만 생략하며 제작한 배경은 계속 보입니다.
코덱, 알파 디코딩, 전환 상세는 [투명 WebM](../reference/export-transparency.md#transparent-webm)을 참고하세요.

`.to_mov()`은 `.to_webm()`과 같은 매개변수와 타이밍을 사용하며 ProRes 4444 영상과 AAC 오디오로 고정됩니다.
홀수 크기와 1픽셀 크기를 유지합니다. RGBA 소스는 8비트이며 16비트 알파 인코딩은 디코딩 시 8비트 알파에서 한 단계 차이를 만들 수 있습니다.
색상은 손실이 있는 4:4:4 YUV입니다. 측정된 변환 한계와 인코더 요구 사항은 [ProRes MOV](../reference/export-transparency.md#prores-4444-mov)를 참고하세요.
`render()`와 `export()`는 불투명·투명 출력 모두 `VideoOptions`와 `.mov`를 받습니다.

### `.export_image_sequence(output_directory, *, format="png", quality=None, matte=None, lossless=None, options=None, policy=None)` { #export_image_sequenceoutput_directory-formatpng-qualitynone-mattenone-losslessnone-optionsnone-policynone }

기존 부모 디렉터리 아래의 새 디렉터리에 애니메이션 타임라인을 독립된 PNG(기본), JPEG, WebP 파일과 `manifest.json`으로 기록합니다.
`ImageSequenceOptions(fps=30, hold=3, workers=1, render_quality="standard")`는 타이밍과 합성을 제어하며 메서드 키워드는 이미지 인코딩을 선택합니다.
JPEG는 기본 흰색의 불투명 매트 위 RGB를 사용하고 `quality=1..95`를 받습니다.
WebP는 알파를 보존하고 `lossless=True`를 받으며 손실 WebP는 품질 값을 받습니다.
PNG와 무손실 WebP는 렌더러의 RGBA8 픽셀을 정확히 보존합니다.
불투명 WebP는 RGB로 디코딩될 수 있으며 매니페스트 모드는 논리적인 RGBA 디코딩을 설명합니다.
결과는 실제 프레임 수, 타이밍, 인코딩, 목적지를 보고합니다.
검증, 형식별 메타데이터, 덮어쓰지 않는 원자적 게시 방식은 [이미지 시퀀스](../reference/export-frames.md#image-sequences)를 참고하세요.

### `.to_mp4(...)` { #to_mp4 }

`.to_webm()`과 같은 애니메이션 타임라인을 H.264 MP4 컨테이너로 반환하며, 예약된 슬라이드별 내레이션과 선택적인 혼합 사운드트랙을 포함합니다.
MP4/WebM/MOV 애니메이션 내보내기는 Deck당 내레이션 슬라이드를 최대 64개 지원합니다. 무음 슬라이드는 이 FFmpeg 입력 운영 제한에 포함되지 않습니다.
파일 내보내기는 `deck.export("deck.mp4", animation=VideoOptions(soundtrack=AudioTrack(path="music.mp3", loop=True)))`를 사용하세요.
렌더링 중 배경 트랙을 각 슬라이드의 `audio` 내레이션과 혼합합니다.
옵션을 지정하지 않은 `deck.export("deck.mp4")`는 같은 타임라인과 기본 `VideoOptions()`를 사용합니다.

## `.diagnose()` { #diagnose }

각 슬라이드의 [`Canvas.diagnose()`](canvas.md#diagnose) 항목을 모으고 Deck 전체 검사를 추가합니다.
`DeckDiagnostic` 항목을 담은 `findings` 목록이 있는 `DiagnosticReport`를 반환합니다.

```python
for finding in deck.diagnose().findings:
    print(finding.slide_index, finding.code, finding.message)
```

| 필드 | 자료형 | 설명 |
| --- | --- | --- |
| `code` | `str` | 슬라이드 코드(`off-canvas`, `tiny-text` 등) 또는 `mixed-slide-size` |
| `severity` | `str` | `"warning"` 또는 `"error"` |
| `message` | `str` | 사람이 읽을 수 있는 설명 |
| `slide_index` | `int \| None` | 발생 슬라이드. Deck 전체 항목이면 `None` |
| `layer_index` | `int \| None` | 해당하는 경우 슬라이드 내 발생 레이어 |
| `layer_id` | `str \| None` | 그룹 자식 ID를 포함한 안정적인 발생 레이어 ID |
| `layer_name` | `str \| None` | 존재하는 경우 발생 레이어 이름 |
| `bbox` | `dict \| None` | 측정된 캔버스 좌표계 경계 상자 |
| `related_layers` | `list[str]` | 진단에 관련된 레이어 ID |
| `measured` | `dict` | 규칙별 측정값 |
| `suggestion` | `str \| None` | 사용할 수 있는 경우 수정 힌트 |

슬라이드 크기가 모두 같지 않으면 `mixed-slide-size` 경고가 추가됩니다.
PDF는 페이지마다 슬라이드 크기를 사용하지만 PPTX는 첫 슬라이드 크기를 Deck 전체에 사용하므로 뒤의 큰 슬라이드는 PowerPoint에서 잘립니다.
`.pptx`를 대상으로 할 때는 슬라이드 크기를 통일하세요.

## `.prefetch_assets()`(선택 사항) { #prefetch_assets-optional }

[`Canvas.prefetch_assets()`](canvas.md#prefetch_assets-optional)처럼 모든 슬라이드의 원격 에셋을 미리 내려받고 Deck 수준 `asset_manifest` 하나를 반환합니다.
렌더링과 내보내기도 에셋을 직접 가져오므로 긴 내보내기 전에 네트워크 실패나 오래된 캐시 항목을 드러낼 때만 호출하세요.

## JSON { #json }

### `.to_json()` / `Deck.from_json(json_str)` { #to_json-deckfrom_jsonjson_str }

각 Canvas의 직렬화를 재사용해 Deck을 정규 JSON으로 왕복합니다.
형식은 `{"kind": "deck", "width": ..., "height": ..., "theme": {...}, "slides": [<canvas spec>, ...]}`이며 모든 슬라이드는 `"kind": "canvas"`를 포함합니다.
기본 슬라이드 크기인 `width`/`height`와 `theme`는 설정된 경우에만 출력됩니다.
JSON으로 작성한 슬라이드는 Deck이 기본 크기를 제공하면 크기를 생략할 수 있습니다. 정규 직렬화는 상속한 크기를 실제 값으로 기록합니다.
슬라이드별 `transition`, `audio`, `duration`, `notes`는 Canvas 필드와 함께 보존됩니다.
최상위 `theme`는 모든 슬라이드가 공유하므로 `Canvas.from_json`과 똑같이 `$theme.*` 토큰을 사용할 수 있습니다.

```python
spec = deck.to_json()
restored = Deck.from_json(spec)
```

!!! note
    `Canvas.to_json()`처럼 `.custom(fn)` 슬라이드가 있는 Deck은 콜백을 등록하지 않으면 직렬화할 수 없습니다. `from_json()`은 dict가 아닌 **JSON 문자열**을 받습니다.
