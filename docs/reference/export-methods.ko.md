---
description: quickthumb 내보내기 메서드, 결과 보고와 형식 선택 계약을 설명합니다.
---

# 내보내기 메서드와 결과 { #export-methods-and-receipts }

[내보내기 레퍼런스](../exports.md) · [출력 형식 선택](../output-guide.md)

## 권장 출력 API { #recommended-output-api }

`export()`로 Canvas나 Deck을 파일에 저장하면 `ExportResult`가 반환됩니다. 여기에는 저장한 경로(`written_paths`), 기능 지원 여부와 대체 표현에 관한 진단, 픽셀·타이밍 정보, 에셋, 실제 렌더링 환경이 담깁니다.
확장자가 형식을 선택합니다. MP4, WebM, MOV, GIF는 애니메이션 타임라인을 재생합니다.
Deck 동영상은 슬라이드별 내레이션도 혼합합니다.

```python
from quickthumb import VideoOptions

result = deck.export("slides.mp4", animation=VideoOptions(hold=2, render_quality="high"))
print(result.written_paths, result.fallback_diagnostics)
deck.export("slides.html")  # interactive slideshow with click-triggered motion
canvas.export("card.webp", quality=85)  # JPEG/WebP compression quality
```

| 필요한 작업 | 진입점 |
| --- | --- |
| 기능 정책과 결과 보고가 있는 파일 기록 | `export(path, ...)` |
| 디버그 상자 그리기 또는 저수준 파일 렌더러 사용 | `render(path, ...)` |
| 바이트나 메모리 내 문서 얻기 | `to_mp4()`, `to_gif()`, `to_html()` 등 |
| 내레이션 Deck 내보내기 | `export(path, animation=VideoOptions(hold=3))` / `to_mp4(hold=3)` |
| 무음 애니메이션 프레임과 매니페스트 기록 | `export_image_sequence(directory, options=...)` |
| 제한된 Canvas 전용 Lottie 벡터 기록 | `canvas.export("scene.lot", animation=LottieOptions(fps=30, hold=3))`. [Lottie 벡터](export-lottie.md#lottie-vectors)를 참고하세요. |

모든 애니메이션 바이트 메서드와 옵션은 최종 정착 시간에 `hold`를 사용합니다.
`render_quality="standard"` 또는 `"high"`는 애니메이션 합성을 제어하며 `export()`/`render()`의 `quality`는 압축을 제어합니다.
JPEG는 정수 1–95, WebP는 1–100을 받습니다.
고급 spawn 렌더링이 필요하지 않으면 `workers=1`을 유지하세요.
선택적인 [시간 노출](../timing.md#temporal-exposure)은 Canvas 내보내기에 모션 블러를 추가합니다.
`export()`와 `render()`는 쓰기 전에 `unsupported_motion="error"` 같은 파일 기능 정책을 적용하며 `export()`는 결과 보고도 반환합니다.
바이트 메서드는 공통 파일 결과 없이 대상별 제어를 제공합니다.
Deck 래스터 시퀀스는 번호가 붙은 파일이므로 반환된 `written_paths`를 사용하세요.
이미지 시퀀스는 목적지가 새 디렉터리이므로 별도 API를 유지합니다.

## 형식과 옵션 선택 { #format-and-option-selection }

Canvas와 Deck은 `.lot`가 Canvas 전용이라는 점을 제외하면 같은 선택 규칙을 따릅니다.
Deck은 Lottie 출력을 거부합니다.

| 입력 | 결과 |
| --- | --- |
| `format` 없는 파일 확장자 | 출력 선택. `.jpg`/`.jpeg`는 `output_format="jpeg"`, `.htm`/`.html`은 `"html"`로 보고합니다. |
| 대소문자 구분 없는 `format="PNG"`, `"JPEG"`, `"WEBP"` | 래스터·알 수 없는 확장자·확장자 없는 파일의 래스터 인코딩을 선택합니다. 요청한 파일 이름을 유지하며 인코딩에 맞춰 바꾸지 않습니다. |
| 문서·애니메이션 확장자와 래스터 `format` | SVG, PDF, HTML, PPTX, 동영상, `.lot` 이름에 이미지 바이트를 쓰는 대신 거부합니다. |
| `quality` | JPEG 정수 1–95 또는 WebP 정수 1–100. 다른 대상은 거부합니다. |
| `animation` | GIF는 `GifOptions`, MP4/WebM/MOV는 `VideoOptions`, Canvas `.lot`는 `LottieOptions`. 다른 정적·문서 대상에서는 거부합니다. |

형식 선택, 압축 품질, 애니메이션 옵션 계열 충돌은 에셋을 읽거나 파일을 쓰기 전에 거부합니다.
코덱별 제한은 내보내기 준비 중 검증합니다.
렌더링·인코딩 실패는 이후에도 발생할 수 있으며 일반 파일 내보내기는 원자적인 여러 파일 트랜잭션이 아닙니다.
Canvas나 번호가 붙은 Deck 파일 이름을 추측하지 말고 `written_paths`를 검사하세요.
Deck은 단일 SVG로 쓸 수 없으므로 Canvas 슬라이드를 개별 내보내세요.
새 디렉터리와 인코딩 옵션의 별도 계약은 [이미지 시퀀스](export-frames.md#image-sequences)를 참고하세요.

## 문서 레이어 경로 { #document-layer-routing }

Canvas·Deck HTML/PPTX와 Canvas SVG/PDF는 `result.capability_report`에 `feature="layer_representation"`으로 실제 실행한 레이어 경로를 보고합니다.
네이티브 HTML/CSS, SVG/PDF 기본 요소, 편집 가능한 PowerPoint 객체, 원본 포함 SVG는 `support="native"`입니다.
출력 PNG 조각은 `support="fallback"`, `fallback="rasterize"`입니다.
편집 가능한 전경과 고정 발광 이미지를 조합한 PPTX는 `support="partial"`, `fallback="rasterize"`이며 전경을 편집한 뒤 효과를 갱신하려면 다시 내보내야 합니다.
이 보고서는 어떤 방식으로 출력했는지를 알려 줍니다. 결과의 픽셀이 원본과 얼마나 같은지 측정한 것은 아닙니다.

`result.fallback_diagnostics`는 영향을 받은 검사 `layer_id`와 이유를 알려 줍니다.
유지된 그룹은 `layer_ids`에 하위 ID를 포함합니다.
배경에 의존하는 공통 앞부분은 단일 `layer_id`가 없고 모든 기여 소스를 `layer_ids`에 기록합니다.
모양이 결합된 픽셀에 의존하므로 이런 합성은 함께 보고합니다.
평탄화된 자동 레이아웃 자식도 원래 검사 ID를 유지합니다.
빈 래스터 조각과 빈 텍스트는 요소나 표현 관찰을 만들지 않습니다.

실행된 경로에서 `native_attempt=True`는 네이티브 콘텐츠 출력 또는 래스터로 대체된 네이티브 후보의 실행·검증을 포함합니다.
실제로 채택한 표현은 `support`, `fallback`으로 판단하세요.
`False`는 네이티브 생성·검증 전에 래스터 캡처를 선택했다는 뜻입니다.
기능만 설명하는 진단에서는 이 정보가 미상(`None`)일 수 있습니다.
부모 장면은 SVG/PDF/PPTX에서 정적 합성물을 보고하며 HTML은 아핀 CSS 모션이 반영된 PNG 소스도 보고할 수 있습니다.
기존 모션 기능 진단은 별개로 유지합니다.
SVG/PDF 관찰은 제작된 정적 출력을 설명합니다.
PDF 텍스트는 가능하면 글꼴을 포함하지만 문자 조형, 글리프 범위, 글꼴 포함 제한 때문에 이유를 명시한 래스터 조각을 선택할 수도 있습니다.

실행된 Deck 관찰에는 0부터 시작하는 `slide_index`도 있습니다.
레이어 ID는 `deck.inspect().slides[index]`와 같은 슬라이드 로컬 범위를 유지하므로 슬라이드 간 중복 ID는 두 필드를 함께 사용해 구분하세요.
Canvas 관찰은 `slide_index`를 생략합니다.
Deck HTML의 대화형 큐, 전환, 메모는 유지됩니다. 표현 기록이 클릭 기반 슬라이드쇼를 고정 길이 재생으로 바꾸지는 않습니다.

예를 들어 정적 마스크 도형은 `ExportPolicy(unsupported_motion="error")`로 거부되지 않습니다.
해당 HTML 경로가 PNG 조각으로 마스크를 보존하고 그 결정을 보고하기 때문입니다.
레이어 선택 정책은 추가되지 않습니다.
이 실행 경로 보고는 Canvas SVG/PDF와 Canvas·Deck HTML/PPTX를 다룹니다.
Deck PDF는 아직 이 관찰을 수집하지 않습니다.
충실도 지표는 문서 전체를 설명하며 개별 대체 레이어에 귀속되지 않습니다.
HTML 목적지를 열기 전에 모든 슬라이드를 렌더링하므로 뒤의 미지원 슬라이드나 엄격한 모션 거부도 기존 파일을 보존합니다.

PPTX 경로는 실제 OOXML 표현을 설명합니다.
네이티브 텍스트 상자와 자동 도형은 편집 가능하고 PNG 조각은 래스터 데이터와 위치를 보존하지만 글리프별·벡터 편집은 잃습니다.
래스터 선택 이유에는 마스크, 배경 합성, 이미지·방사형 텍스트 채우기, 지원하지 않는 글꼴 의미가 포함됩니다.
Canvas 관찰은 슬라이드 인덱스를 생략하며 Deck은 해당 슬라이드를 표시합니다.
PPTX 파일은 목적지를 열기 전에 전체 프레젠테이션을 만들므로 뒤의 소스 렌더링 실패도 기존 파일을 보존합니다.

이 구조 관찰은 특정 뷰어의 PowerPoint·Keynote 픽셀 일치, 글꼴 존재, 애니메이션 타이밍, 투명도를 인증하지 않습니다.
PPTX 충실도 정책이나 자동 애플리케이션 렌더러는 없습니다.
PPTX에서는 원본 1픽셀을 9,525 EMU로 변환합니다. 이는 인치당 96픽셀에 해당하며, PDF 단위로는 원본 1픽셀당 0.75포인트입니다.
이후 PDF 기반 뷰어 비교에서는 PDF 내보내기의 픽셀당 1포인트를 가정하지 말고 실제 페이지 크기로 배율을 계산해야 합니다.

## 출력 호출 마이그레이션 { #migrating-output-calls }

- `Deck.to_mp4()`는 이제 Canvas·파일 출력과 같이 애니메이션을 재생합니다. `to_animated_mp4()`, `to_narrated_mp4()`를 `to_mp4()`로 바꾸세요.
- `render_mp4()`, `render_narrated_mp4()`를 `export("deck.mp4")`로 바꾸세요. 별도 정지 슬라이드 인코더는 별칭 없이 제거되었습니다. 정지 장면을 유지하려면 정적 캔버스와 `Cut()`을 사용하세요. 이미 애니메이션이 있는 Deck을 정지시키거나 같은 인코딩 출력을 보장하지는 않습니다.
- `export_image_sequence()`가 `export_png_sequence()`를 대체하며 공개 옵션·매니페스트·결과 모델은 `ImageSequence*`입니다. 이전 별칭은 없습니다.
- 애니메이션 Deck의 `slide_duration=`과 내레이션의 `default_duration=`을 `hold=`로 바꾸세요. 저장한 GifOptions, VideoOptions, ImageSequenceOptions JSON을 포함해 애니메이션 `quality=`를 `render_quality=`로 바꾸세요. 별칭은 없습니다.

## 내보내기 동작 방식 { #how-export-works }

SVG, PDF, PPTX는 적합한 레이어를 **네이티브**로 유지하고 네이티브 표현이 없으면 정규 PNG 조각을 사용합니다.
위치, 줄바꿈, 정렬은 래스터 렌더러와 같은 레이아웃 계산을 사용합니다.
HTML도 같은 네이티브·래스터 방식을 사용합니다. 아래 [HTML](export-documents.md#html)을 참고하세요.

[Lottie](export-lottie.md#lottie-vectors)는 대신 제한된 네이티브 벡터만 받고 미지원 콘텐츠는 쓰기 전에 거부합니다.
PNG 프레임으로 대체하지 않습니다.

| 레이어 | SVG | PPTX | PDF |
| --- | --- | --- | --- |
| 배경 색상·그라디언트 | 네이티브 `rect`와 그라디언트 정의 | 네이티브 도형 채우기. 선형은 네이티브, 방사형은 이미지 포함 | 네이티브 채우기. 불투명 그라디언트는 네이티브, 반투명은 이미지 포함 |
| 테두리 | 네이티브 `rect` 선 | 네이티브 테두리 사각형 | 네이티브 사각형 선 |
| 모든 기본 도형 | 회전·외곽선·그림자·발광을 포함한 네이티브 요소 | 네이티브 자동 도형. 다각형은 자유형 | 회전을 포함한 네이티브 경로. 효과가 있는 도형은 이미지 포함 |
| 일반·서식 텍스트 | 줄·구간별 네이티브 `<text>`. 줄바꿈, 자간, 그라디언트 채우기, 효과 포함 | 구간별 서식이 있는 편집 가능한 텍스트 상자 | 글꼴을 포함할 수 있고 복잡한 조형이 필요하지 않으면 선택 가능한 네이티브 텍스트. 미지원 글꼴, 그라디언트·이미지 채우기, 흐림 효과는 픽셀로 포함 |
| 자동 레이아웃 그룹 | 자식을 레이아웃 위치에 네이티브로 내보냄 | 동일 | 동일 |
| 이미지와 이미지로 채운 텍스트 | 포함된 PNG 조각 | 포함된 그림 | 포함된 그림 |
| SVG 레이어 | 벡터 데이터 URL로 포함. 효과 적용 시 래스터 | 포함된 그림 | 포함된 그림 |
| 혼합 모드와 사용자 정의 레이어 | 마지막 혼합·사용자 정의 레이어 아래 전체를 PNG 하나로 평탄화 | 동일 | 동일 |

## Deck(여러 이미지와 슬라이드) { #decks-multiple-images-and-slides }

`Deck`은 순서가 있는 Canvas 목록입니다.
각 슬라이드는 완전한 `Canvas`이며 개별 렌더링과 정확히 같습니다.
전체 메서드는 [Deck API 레퍼런스](../api/deck.md)를 참고하세요.

Deck에 크기를 한 번 지정하면 각 슬라이드는 이를 상속하는 단순한 `Canvas()`일 수 있습니다.

```python
from quickthumb import AudioTrack, Canvas, Deck, VideoOptions

deck = (
    Deck(1280, 720)   # default slide size; Deck.from_aspect_ratio("16:9", 1280) also works
    .slide(Canvas().background(color="#101820").text(content="Cover", size=96, color="#FFFFFF"))
    .slide(Canvas().background(color="#1A1A2E").text(content="Body", size=64, color="#FFFFFF"))
)
# pre-built canvases work too: Deck(slides=[cover, body])

deck.render("deck.pdf")     # one multi-page PDF (a page per slide)
deck.render("deck.pptx")    # one multi-slide PPTX (a slide per slide)
deck.render("deck.gif")     # one animation playing transitions between slides
deck.export("deck.mp4")     # animated slides with per-slide narration
deck.render(
    "deck.mp4",
    animation=VideoOptions(soundtrack=AudioTrack(path="music.mp3", loop=True)),
)  # animated + mixed audio
deck.render("animated.mp4", animation=VideoOptions(fps=20))  # animated, silent
deck.render("slides.png")   # numbered sequence: slides_01.png, slides_02.png, …

pdf_bytes = deck.to_pdf()
pptx_bytes = deck.to_pptx()
gif_bytes = deck.to_gif()
webm_bytes = deck.to_webm()
mp4_bytes = deck.to_mp4()   # timeline with per-slide narration
```

`render()`는 확장자로 출력을 선택합니다.
`.pdf`, `.pptx`는 문서 하나, `.gif`, `.mp4`, `.webm`, `.mov`는 애니메이션을 만듭니다.
래스터 확장자에는 네이티브 다중 페이지 컨테이너가 없으므로 0으로 채운 번호가 붙은 슬라이드별 파일을 쓰고 기록한 경로를 반환합니다.

슬라이드는 크기가 달라도 됩니다.
`deck.diagnose()`는 `slide_index`가 표시된 각 슬라이드의 [진단](../diagnostics.md)을 모으고 크기가 다르면 `mixed-slide-size` 경고를 추가합니다.
PDF는 슬라이드별 크기를 쓰지만 PPTX는 첫 슬라이드의 단일 프레젠테이션 크기를 사용하므로 뒤의 큰 슬라이드가 PowerPoint에서 잘립니다.
`.pptx`에는 슬라이드 크기를 통일하세요.
Deck은 캔버스별 직렬화를 재사용해 `deck.to_json()` / `Deck.from_json(...)`으로 JSON 왕복합니다.

## CLI { #cli }

CLI도 출력 확장자로 형식을 정합니다.

```bash
quickthumb render spec.json -o card.svg
quickthumb render spec.json -o card.pptx
quickthumb render spec.json -o card.pdf

# Live HTML slides; open /?presenter for the presenter dashboard
quickthumb serve slides.py
```
