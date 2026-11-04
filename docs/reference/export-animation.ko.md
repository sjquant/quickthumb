---
description: quickthumb의 GIF, 동영상, 슬라이드 내레이션 내보내기를 설명합니다.
---

# GIF, 동영상, 내레이션 { #gif-video-and-narration }

[내보내기 레퍼런스](../exports.md) · [출력 형식 선택](../output-guide.md)

## 애니메이션 GIF와 동영상 { #animated-gif-video }

정규 표본과 인코딩 프레임 수의 차이, 슬라이드·내레이션 시계, 자막, 대화형 HTML 동작은 [애니메이션 타이밍](../timing.md)을 참고하세요.

애니메이션 내보내기는 PNG 출력과 같은 픽셀 파이프라인으로 표본을 추출해 레이어별 `animation` 효과와 Deck 슬라이드 `transition`을 실제 래스터 프레임으로 렌더링합니다.
Canvas와 Deck의 GIF/MP4/WebM/MOV는 명시적 옵션 없는 파일 내보내기를 포함해 모두 이 애니메이션 타임라인을 재생합니다.

```python
from quickthumb import AudioTrack, Canvas, Deck, Fade, GifOptions, VideoOptions
from quickthumb.transitions import Push

canvas = Canvas(1280, 720).background(color="#101820").text(
    content="Hello", position=("50%", "50%"), size=96, color="#FFFFFF",
    animation=Fade(duration=0.6),
)
canvas.render("hello.gif")                     # defaults: 20 fps, 3s hold
canvas.render(
    "preview.gif",
    animation=GifOptions(fps=8, max_size=(540, 960), colors=128),
)
mp4 = canvas.to_mp4(fps=30, hold=2.0)          # tunable variants return bytes

other = Canvas(1280, 720).background(color="#204060")
deck = Deck(1280, 720).slide(canvas).slide(other, transition=Push(direction="left"))
gif = deck.to_gif(fps=20, hold=3.0, loop=0)
webm = deck.to_webm(fps=30, hold=3.0)
```

모든 효과는 `duration`, `delay`, `trigger`와 두 가지 타이밍 제어를 받습니다.

- `easing`은 공통 이징 용어(`"linear"`, `"ease"`, `"ease_out_cubic"`, `"ease_out_back"` 등)에서 등장 곡선을 선택합니다. 기존 효과의 기본값은 `"ease"`입니다. 정규 프리셋은 이징·느낌을 해석하며 그 외에는 `"linear"`를 사용합니다. 경과 시간을 나타내는 막대는 진행률을 정확히 표현하려면 `"linear"`가 필요합니다. HTML은 이름 있는 이징과 사용자 정의 cubic-bezier 함수를 CSS에 전달합니다. 이름 있는 다항 곡선은 기존 CSS cubic-bezier 근사를 사용하므로 모양은 비슷하지만 중간 픽셀 상태가 정규 표본과 정확히 같지는 않을 수 있습니다.
- `start`는 앞선 효과에 이어 붙이는 대신 슬라이드의 절대 시각에 고정합니다. 고정된 효과는 주변 상대 효과를 이어 붙일 때 쓰는 커서를 이동시키지 않으므로 두 방식을 섞을 수 있습니다.

```python
from quickthumb import Wipe

canvas.shape(
    shape="rectangle", position=(0, 700), width=1280, height=6, color="#E8A552",
    animation=Wipe(direction="right", duration=6.0, easing="linear"),
)
canvas.shape(
    shape="rectangle", position=(80, 180), width=180, height=14, color="#E8A552",
    animation=Wipe(direction="right", duration=2.4, start=0.9, easing="linear"),
)
```

`stagger`가 있는 정규 `AnimationSpec`은 대상을 각자의 시점에 이동시킵니다.
줄 대상은 레이어의 완성된 렌더링에서 잘라내므로 그려진 레이아웃을 유지하고 차례가 올 때까지 화면 밖에서 기다립니다.

```python
from quickthumb import AnimationSpec

canvas.text(
    content="가로로 한 번.\n세로로 한 번.\n미리보기로 또 한 번.",
    position=(80, 150), size=38, color="#F2EFE9", line_height=1.5,
    animation=AnimationSpec.rise(
        from_="bottom", distance=26, duration=0.45, stagger=0.32, target="lines"
    ),
)
```

줄이 닿을 정도로 촘촘하면 렌더링 결과에서 구별할 수 없으며 단어·문자 대상도 분리 가능한 띠가 없습니다.
이 경우 레이어 전체를 움직이는 방식으로 대체합니다.

정적 텍스트와 최상위 그룹은 명시적 부모 체인의 말단으로도 stagger할 수 있습니다.
분리된 띠는 조상의 전체 아핀 변환을 상속하면서 자체 기준점과 외형 트랙을 유지합니다.
위와 같은 부분 띠 어댑터와 전체 블록 대체 표현을 사용합니다. stagger 레이어 자체는 다른 레이어의 부모가 될 수 없습니다.
카운터와 stagger의 조합 및 동적 소스는 계속 제한됩니다.
[부모 변환 경계](../api/video.md#current-adapters-and-boundaries)와 실행 가능한 `examples/parent_stagger.py`를 참고하세요.

`Canvas.render()`와 `Deck.render()`는 애니메이션 파일 출력에 형식별 옵션 객체를 받습니다.
GIF는 `GifOptions`(`fps`, `hold`, `matte`, `loop`, `max_size=(width, height)`, `colors`), MP4/WebM/MOV는 `VideoOptions`(`fps`, `hold`, `matte`, `soundtrack=AudioTrack(...)`, `loop_audio`, WebM/MOV의 `transparent=True`)를 사용합니다.
둘 다 `workers=1`, `render_quality="standard"`를 받습니다.
GIF 크기·팔레트 제어는 동영상 출력에서, 동영상 옵션은 GIF에서 거부됩니다.
일반 `render(..., quality=...)`는 JPEG와 WebP 래스터 출력용으로만 유지됩니다.

두 모델은 Canvas·Deck 바이트 메서드의 `hold`와 같은 최종 정착 유지 시간 `hold=3.0`을 사용합니다.
유한한 0 이상 숫자여야 하며 불리언과 문자열은 거부됩니다.
기본 유지 시간은 직렬화에서 생략하고 불러올 때 복원하며 명시적인 0은 유지합니다.
내레이션과 명시적인 Deck 슬라이드 길이는 여전히 동영상 일정을 정하고 Deck GIF는 그 슬라이드별 길이를 계속 무시합니다.
Deck 애니메이션 동영상은 기존 제한을 유지합니다. 내레이션도 명시적 양수 길이도 없는 슬라이드가 있으면 양수 무음 바닥 트랙이 필요하므로 `hold=0`은 실패합니다.
그러한 슬라이드에는 양수 유지 시간을 사용하세요.
Canvas, Deck GIF, 무음 이미지 시퀀스는 계속 0을 허용합니다.

바이트 메서드는 같은 렌더링 제어를 키워드 전용 스칼라로 받습니다.
Canvas GIF/MP4/WebM/MOV와 Deck GIF·애니메이션 MP4/WebM/MOV의 `workers=1`, `render_quality="standard"`, GIF의 `max_size=None`, `colors=None`입니다.
이 메서드는 `hold`를 사용하며 옵션 객체는 받지 않습니다.
내레이션은 다른 동영상 출력과 같은 Deck MP4 타임라인을 사용합니다.

파일 실행은 내보내기 정책을 검사하기 전에 형식을 결정합니다.
Canvas와 Deck MP4는 항상 애니메이션 타임라인을 재생하고 옵션이 없으면 기본 `VideoOptions()`를 사용합니다.
실행하지 않는 제작된 Morph 전환은 정적 파일이나 모션 줄이기 실행에서 대체 표현 오류나 결과 진단을 만들지 않습니다.
모션을 줄여도 인코더의 유지 시간과 슬라이드 사이 기본 전환은 유지됩니다.
표본률과 인코딩된 시각적 프레임 수·길이는 [애니메이션 타이밍](../timing.md)을 참고하세요.

`ExportResult.pixel_metrics.width`, `height`는 정규 첫 캔버스의 래스터 크기입니다.
GIF 크기 조절이나 MP4/WebM 자르기를 설명하지 않습니다.
이미지 시퀀스 결과는 별도로 전체 출력 크기를 보고합니다.

`validate_export(target)`은 파일 실행 옵션과 독립된 선언된 모션 기능 질의입니다.
예를 들어 모션 줄이기 정책에서도 `validate_export("mp4")`는 애니메이션 동영상을 질의합니다.
구체적인 `svg`, `pdf` 질의는 기존 `raster` 계열 이름으로 정적 문서 대체 표현을 설명합니다.
대상은 대소문자를 구분하지 않으며 `jpg`, `jpeg`, `webp`, `png`, `gif`, `mp4`, `webm`, `mov`, `htm`, `image_sequence`를 해당 계열 별칭으로 받습니다.
GIF 질의는 `raster`이지만 호환성을 위해 GIF `ExportResult.target`은 `video`를 유지합니다.

## 내레이션이 있는 Deck 동영상 { #narrated-deck-video }

Deck을 슬라이드별 음성 해설이 있는 동영상으로 내보낼 수 있습니다.

- `Deck.slide()`에 `audio=`를 전달합니다. `duration=`이 없으면 `ffprobe`로 내레이션 길이를 측정합니다. 명시적 `duration=`은 오디오를 자르거나 무음으로 채웁니다. 오디오 없는 슬라이드는 `hold`(3초) 동안 무음으로 유지됩니다.
- `deck.export("deck.mp4")`, `deck.render("deck.mp4")`는 기본적으로 내레이션과 함께 레이어 애니메이션·전환을 재생합니다. `deck.to_mp4()`, `deck.to_webm()`, `deck.to_mov()`은 애니메이션 동영상 바이트를 반환합니다.
- 정지 슬라이드에 내레이션을 넣으려면 정적 캔버스와 명시적 `Cut()`을 사용합니다. 영상은 H.264/yuv420p이며 오디오가 있으면 AAC입니다. 전환 생략 시 컷이 아닌 기본 페이드를 사용합니다. `reduced_motion=True`도 기본 전환을 선택하며 정지 슬라이드 내보내기 모드가 아닙니다. 일반 MP4 경로에서는 기존 애니메이션 레이어가 계속 재생됩니다.
- `deck.export()` 또는 `deck.render()`에 `animation=VideoOptions(soundtrack=AudioTrack(path="music.mp3", volume=0.16, loop=True))`로 배경 음악을 추가합니다. Quickthumb가 슬라이드 내레이션과 혼합하므로 호출자가 미리 믹싱할 필요가 없습니다.

```python
from quickthumb import Canvas, Deck, VideoOptions
from quickthumb.transitions import Cut

deck = Deck(640, 360).transition(Cut())
deck.slide(Canvas(640, 360).background(color="#123456"),
           audio="voice.wav", duration=2.5)
deck.slide(Canvas(640, 360).background(color="#456789"), duration=1.0)
result = deck.export("narrated.mp4", animation=VideoOptions(fps=30))
mp4_bytes = deck.to_mp4(fps=30)
```

## 타이밍 { #timing }

클릭할 사람이 없다는 점을 제외하면 동영상과 GIF는 HTML 슬라이드쇼의 타이밍을 따릅니다.
`on_click` 애니메이션은 `after_previous`처럼 차례로 자동 재생합니다. PowerPoint 자체 동영상 내보내기도 같습니다.
각 슬라이드는 이전 슬라이드의 마지막 프레임 위에서 전환을 재생하고 HTML처럼 전환과 함께 시작하는 애니메이션을 실행한 뒤 정착 상태를 유지합니다.
유지 시간은 전환의 `advance_after`가 있으면 그 값, 없으면 `hold`입니다.
내레이션 MP4/WebM/MOV에서는 추론·명시한 내레이션 길이나 무음 슬라이드 기본값이 `advance_after`보다 길면 시각적 슬라이드를 연장합니다.
전환 없는 슬라이드는 0.5초 크로스페이드로 들어옵니다. 전환 없는 0번 슬라이드는 즉시 시작합니다.
0번 슬라이드에 전환을 지정하면 매트에서 등장하게 되어 반복 GIF의 끝과 시작도 자연스럽게 연결됩니다.

GIF는 Pillow가 프레임별 길이로 인코딩하므로 추가 의존성이 없습니다.
MP4(H.264), WebM(VP9), MOV(ProRes 4444)에는 `PATH`의 `ffmpeg` 또는 `QUICKTHUMB_FFMPEG` 환경 변수가 가리키는 바이너리가 필요합니다.

Canvas MP4/WebM/MOV는 ffmpeg가 디코딩하는 MP3, WAV, AAC, OGG 등의 오디오 파일을 사운드트랙으로 담을 수 있습니다.
MP4/MOV는 AAC, WebM은 Opus로 인코딩합니다.

```python
mp4 = canvas.to_mp4(soundtrack="music.mp3")                    # loops to fill the video
mp4 = canvas.to_mp4(soundtrack="jingle.wav", loop_audio=False) # plays once, then silence
```

오디오는 항상 동영상 길이에 맞춰 자릅니다.
`AudioTrack`의 `loop=True`는 짧은 트랙을 반복하고 `loop=False`는 한 번 재생한 뒤 무음으로 유지합니다.
`loop_audio`는 명시적 재정의입니다. 기존 문자열 경로는 이전의 반복 기본값을 유지합니다.
GIF 내보내기는 사운드트랙을 받지 않습니다.

!!! tip "형식별 팁"
    - **배경**: 프레임은 기본 검정인 불투명 매트에 합성합니다. 알파 오버레이에는 WebM 또는 MOV와 `transparent=True`를 사용하세요.
    - **해상도**: H.264/VP9 4:2:0 인코딩에는 1280×720 같은 짝수 픽셀 크기가 필요합니다.
    - **GIF 최적화**: `GifOptions`에 `max_size=(w, h)`, `colors=128` 또는 64를 사용해 파일을 작게 유지하세요.
    - **내레이션 Deck**: 한 Deck 동영상은 내레이션 슬라이드를 최대 64개 지원합니다. 더 긴 발표는 여러 동영상으로 나누세요.
