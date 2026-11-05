---
description: quickthumb 동영상 레이어의 자르기, 크기 맞춤, 속도, 자막, 색보정, 마스킹과 애니메이션을 설명합니다.
---

# 동영상 { #video }

`.video()`는 캔버스에 동영상 클립을 추가합니다.
다른 시각적 레이어처럼 클립을 자르거나 크기와 위치를 바꾸고 반복할 수 있습니다. 모서리를 둥글게 만들거나 색보정, 마스크, 타임라인 애니메이션을 적용하는 것도 가능합니다.

동영상 레이어는 애니메이션 출력(GIF, MP4, WebM, MOV)과 `render_frame(...)`에서 네이티브로 렌더링됩니다.
정적 문서 대상(PPTX, PDF, SVG, HTML)에서는 클립을 정지 프레임으로 렌더링합니다.

## 시그니처 { #signature }

```python
canvas.video(
    source,
    position,
    width,
    height,
    fit="contain",
    trim_start=0.0,
    trim_end=None,
    start=0.0,
    duration=None,
    speed=1.0,
    volume=1.0,
    captions=None,
    border_radius=0,
    opacity=1.0,
    rotation=0.0,
    align=None,
    blend_mode=None,
    effects=None,
    clip=None,
    mask=None,
    animation=None,
)
```

## 매개변수 { #parameters }

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `source` | `str` | **필수** | 동영상 파일 경로입니다. |
| `position` | `tuple` | **필수** | 픽셀 또는 백분율 문자열(`"50%"`)로 표현한 `(x, y)` 위치입니다. |
| `width` | `int` | **필수** | 레이어 너비(픽셀)입니다. |
| `height` | `int` | **필수** | 레이어 높이(픽셀)입니다. |
| `fit` | `str \| FitMode` | `"contain"` | 레이어 상자 안에 맞추는 방식. `"contain"`, `"cover"`, `"fill"`입니다. [FitMode](enums.md#fitmode)를 참고하세요. |
| `trim_start` | `float` | `0.0` | 소스 파일의 재생 시작 시각(초)입니다. |
| `trim_end` | `float \| None` | `None` | 소스 파일의 재생 종료 시각. 기본값은 클립 끝입니다. |
| `start` | `float` | `0.0` | 타임라인에서 클립 재생을 시작하는 시각(초)입니다. |
| `duration` | `float \| None` | `None` | 장면에서 클립이 나타나는 길이입니다. |
| `speed` | `float` | `1.0` | 재생 속도 배수. `0.5`는 절반, `2.0`은 두 배 속도입니다. |
| `volume` | `float` | `1.0` | MP4/WebM/MOV의 클립 오디오 음량. GIF는 항상 무음입니다. |
| `captions` | `list \| None` | `[]` | 프레임에 직접 그리는 시간 지정 자막 오버레이입니다. |
| `border_radius` | `int` | `0` | 모서리 반경(픽셀)입니다. |
| `opacity` | `float` | `1.0` | `0.0`부터 `1.0`까지의 레이어 불투명도입니다. |
| `rotation` | `float` | `0.0` | 회전 각도(도)입니다. |
| `align` | `str \| Align \| tuple \| None` | `None` | `position`의 기준점입니다. [Align](enums.md#align)을 참고하세요. |
| `blend_mode` | `str \| BlendMode \| None` | `None` | 합성 혼합 모드입니다. |
| `effects` | `list \| None` | `[]` | 시각 필터인 `Filter`, `Duotone`, `Grain`, `Glow`, `Shadow`, `Stroke`, `InnerShadow`입니다. |
| `clip` | `LayerClip \| None` | `None` | 레이어를 기하학적 경계 상자로 자릅니다. |
| `mask` | `LayerMask \| None` | `None` | 도형이나 경로로 레이어를 마스킹합니다. |
| `animation` | `Animation \| AnimationSpec \| list \| None` | `None` | 등장·퇴장 프리셋 또는 사용자 정의 키프레임 모션입니다. |

## 예제 { #examples }

### 자르기와 색보정 { #trimming-and-color-grading }

클립을 6초 구간으로 자르고 흑백으로 바꾸며 모서리를 둥글게 만듭니다.

```python
from quickthumb import Canvas
from quickthumb.models import Filter

canvas = Canvas(1280, 720).video(
    "clip.mp4",
    position=(64, 64),
    width=1152,
    height=592,
    fit="cover",
    trim_start=1.0,
    trim_end=7.0,
    duration=6.0,
    border_radius=16,
    effects=[Filter(saturation=0.0, contrast=1.15)],
)
```

### 위치 애니메이션 { #animating-position }

재생 중인 동영상을 장면의 가로 방향으로 이동시킵니다.

```python
from quickthumb import AnimationSpec, Canvas, KeyframeSpec, PositionTrack, TimingSpec

canvas = Canvas(1280, 720).video(
    "clip.mp4",
    position=(0, 200),
    width=480,
    height=270,
    fit="cover",
    duration=4.0,
    animation=AnimationSpec.timeline(
        PositionTrack(
            keyframes=[
                KeyframeSpec(time=0.0, value=(0, 0)),
                KeyframeSpec(time=4.0, value=(800, 0)),
            ]
        ),
        timing=TimingSpec(start=0.0, duration=4.0),
        easing="ease_in_out",
    ),
)
```

### 스프링 이징 { #spring-easing }

`SpringEasing`으로 자연스러운 물리 기반 바운스를 추가합니다.

```python
from quickthumb import AnimationSpec, KeyframeSpec, PositionTrack, SpringEasing

motion = AnimationSpec.timeline(
    PositionTrack(keyframes=[
        KeyframeSpec(time=0, value=(0, 0)),
        KeyframeSpec(time=1, value=(180, 0)),
    ]),
    easing=SpringEasing(stiffness=100, damping=10, mass=1),
)
```

### Wiggle 트랙 수정자 { #wiggle-track-modifiers }

어떤 트랙에든 `Wiggle(frequency=2, amplitude=12, seed=42)`를 연결해 유기적이면서 결정적인 흔들림을 추가할 수 있습니다.

```python
from quickthumb import AnimationSpec, KeyframeSpec, PositionTrack, TimingSpec, Wiggle

motion = AnimationSpec.timeline(
    PositionTrack(
        keyframes=[KeyframeSpec(time=0, value=(0, 0))],
        wiggle=Wiggle(frequency=2, amplitude=12, seed=42),
    ),
    timing=TimingSpec(duration=2),
)
```

## 투명 동영상 오버레이 { #transparent-video-overlays }

투명 배경의 동영상을 내보냅니다. 하단 자막 그래픽, 애니메이션 스티커, 게임 오버레이에 적합합니다.

- **WebM(알파 포함 VP9)**: `VideoOptions(transparent=True)`
- **ProRes 4444 MOV**: `canvas.export("overlay.mov", animation=VideoOptions(transparent=True))`

```python
from quickthumb import Canvas, VideoOptions

canvas = Canvas(1280, 720).shape("pill", (100, 600), 400, 80, "#42CEB7")
canvas.export("lower_third.webm", animation=VideoOptions(transparent=True))
```

자세한 내용은 [투명 동영상](../reference/export-transparency.md)을 참고하세요.

## 참고 { #notes }

- **소스 길이**: 장면이 원본 클립보다 길면 `speed`를 `1.0` 미만으로 설정해 재생을 부드럽게 늘립니다.
- **자막**: 가독성을 보장하기 위해 구성의 모든 레이어 위에 자막을 그립니다.
- **진단**: `canvas.diagnose()`는 자막 위치, 여백, 읽기 속도를 자동으로 검사합니다.

---

# 고급 모션과 합성 { #advanced-motion-compositing }

아래 절은 텍스트, 도형, 이미지, 경로, 동영상 등 모든 시각적 레이어가 공유하는 고급 애니메이션과 합성 기능을 설명합니다.

## 곡선 모션 경로 { #curved-motion-paths }

접선 핸들이 있는 `PositionKeyframeSpec`으로 직선 대신 부드러운 베지에 모션 곡선을 만듭니다.

```python
from quickthumb import AnimationSpec, Canvas, PositionKeyframeSpec, PositionTrack, TimingSpec

canvas = Canvas(640, 360).shape(
    "pill", (60, 230), 48, 24, "#42CEB7",
    animation=AnimationSpec.timeline(
        PositionTrack(
            keyframes=[
                PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(120, -200)),
                PositionKeyframeSpec(time=4, value=(480, 0), in_tangent=(-120, -200)),
            ],
            auto_orient=True,  # Rotate layer to follow the path tangent
        ),
        timing=TimingSpec(start=0, duration=4),
        easing="linear",
    ),
)
```

### 핸들과 속도 { #handles-and-speed }

- `out_tangent=(dx, dy)`는 키프레임에서 나가는 곡선 모양을 정합니다.
- `in_tangent=(dx, dy)`는 키프레임으로 들어오는 곡선 모양을 정합니다.
- `easing="linear"`이면 레이어가 곡선을 따라 일정한 속도로 이동합니다.

### 접선 따르기 { #following-the-tangent }

`auto_orient=True`이면 레이어가 이동 방향에 맞춰 자동으로 회전합니다.
오른쪽 방향은 `0°`이며 시계 방향이 양수입니다.

### 내보내기 지원 { #export-support }

곡선 모션 경로는 래스터 애니메이션(GIF, MP4, WebM)과 HTML에서 지원됩니다.
문서 대상(PPTX, PDF)은 초기 프레임을 표시합니다.

## 변환 기준점과 독립적인 크기 조절 { #transform-anchors-and-independent-scale }

기본적으로 레이어는 중앙인 `anchor=(0.5, 0.5)`를 기준으로 크기를 조절하고 회전합니다.
다른 피벗을 사용하려면 `anchor=(x, y)`를 지정하세요.

- `(0, 0)`: 왼쪽 위
- `(0.5, 0.5)`: 중앙(기본값)
- `(1, 1)`: 오른쪽 아래

```python
from quickthumb import (
    AnimationSpec, Canvas, KeyframeSpec, RotationTrack, ScaleXTrack, ScaleYTrack, TimingSpec,
)

canvas = Canvas(320, 240).shape(
    "rectangle", (100, 100), 80, 40, "#42CEB7",
    anchor=(0, 1),  # Pivot around bottom-left corner
    animation=AnimationSpec.timeline(
        ScaleXTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=1.5)]),
        ScaleYTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=2, value=0.6)]),
        RotationTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=2, value=30)]),
        timing=TimingSpec(duration=2),
    ),
)
```

### 내보내기 지원 { #export-support_1 }

사용자 정의 기준점과 축별 크기 조절(`ScaleXTrack`, `ScaleYTrack`)은 래스터 프레임, GIF, MP4, WebM, 최신 HTML 프레젠테이션에서 동작합니다.

## 텍스트와 도형 색상 애니메이션 { #animated-text-and-shape-colors }

`ColorTrack`으로 시간에 따라 채우기와 텍스트 색상을 부드럽게 바꿉니다.

```python
from quickthumb import AnimationSpec, Canvas, ColorTrack, KeyframeSpec, TimingSpec

canvas = Canvas(640, 360).text(
    "Color in motion", position=(40, 40), size=48, color="#FF0000",
    animation=AnimationSpec.timeline(
        ColorTrack(keyframes=[
            KeyframeSpec(time=0, value="#FF0000"),
            KeyframeSpec(time=2, value="#0055FF"),
        ]),
        timing=TimingSpec(start=0, duration=2),
    ),
)
```

색상은 지각적으로 균일한 Oklab 색 공간에서 부드럽게 보간되므로 탁한 중간 색상을 피합니다.

## 실시간 타임라인 미리보기 { #live-timeline-preview }

동영상 파일을 인코딩하지 않고 브라우저에서 애니메이션을 대화형으로 탐색합니다.

```bash
quickthumb serve scene.py --timeline
```

`http://localhost:3030/timeline`에 실시간 탐색기가 열리며 프레임 이동과 저장 시 즉시 새로고침을 지원합니다.

## 부모 연결과 null 컨트롤러 { #parent-links-and-null-controllers }

`parent="parent-layer-id"`로 레이어를 계층적으로 연결합니다.
부모가 이동·회전하거나 크기가 바뀌면 자식도 따릅니다.

```python
from quickthumb import Canvas

scene = (
    Canvas(320, 240)
    .null(position=(100, 50), id="controller")  # Invisible point controller
    .shape("rectangle", (10, 20), 40, 20, "#42CEB7", parent="controller")
)
```

### 기하 구조 계약 { #geometry-contract }

- 자식 위치는 부모 좌표 공간을 기준으로 합니다.
- 자식은 부모의 모션 변환(위치, 회전, 크기)을 상속합니다.
- 부모의 스타일(불투명도, 효과, 마스크)은 상속하지 **않으므로** 자식 스타일은 독립적으로 유지됩니다.

### 현재 어댑터와 경계 { #current-adapters-and-boundaries }

부모 연결은 래스터, GIF, MP4, WebM에서 완전히 지원됩니다.
문서 형식(PPTX, PDF, SVG)에서 부모가 있는 그룹은 정적으로 렌더링된 조각으로 내보냅니다.

## 텍스트 범위 선택기 { #text-range-selectors }

`RangeSelector`를 사용하면 텍스트를 단어별, 줄별, 문자별로 나누어 움직일 수 있습니다.

```python
from quickthumb import AnimationSpec, Canvas, KeyframeSpec, PositionTrack, RangeSelector, TimingSpec

canvas = Canvas(800, 400).text(
    "Words appear one by one",
    size=48,
    color="#FFFFFF",
    position=(50, 150),
    animation=AnimationSpec.timeline(
        PositionTrack(keyframes=[
            KeyframeSpec(time=0, value=(0, 20)),
            KeyframeSpec(time=0.4, value=(0, 0)),
        ]),
        selector=RangeSelector(
            target="words",  # "words", "lines", or "characters"
            offset=[KeyframeSpec(time=0, value=-100), KeyframeSpec(time=2, value=100)],
        ),
        timing=TimingSpec(duration=2),
    ),
)
```

### 문자별 소유권 { #character-ownership }

`target="characters"`이면 각 글리프가 자체 애니메이션 단계를 받습니다.
공백과 문장 부호도 정확한 글꼴 측정값으로 보존합니다.

## 트랙 매트 { #track-mattes }

`mask=TrackMatte(layer="source-id")`로 다른 레이어를 알파 또는 루마 마스크로 사용합니다.

```python
from quickthumb import Canvas, TrackMatte

canvas = (
    Canvas(640, 360)
    .shape("ellipse", (120, 80), 200, 200, color="#FFFFFF", id="hole")
    .image("photo.jpg", position=(0, 0), width=640, height=360, mask=TrackMatte(layer="hole"))
)
```

- `mode="alpha"`: 소스 레이어의 투명도로 마스킹합니다.
- `mode="luma"`: 소스 레이어의 밝기로 마스킹합니다.
- `invert=True`: 잘라낸 영역을 반전합니다.

### 도형 마스크 기하 구조 애니메이션 { #animated-shape-mask-geometry }

`MaskPositionTrack`, `MaskSizeTrack`, `MaskFeatherTrack`으로 마스크 위치, 크기, 페더를 동적으로 바꿉니다.

### 네이티브 HTML 도형 마스크 { #native-html-shape-masks }

사각형, 캡슐, 타원 마스크는 HTML 슬라이드쇼에서 깔끔한 CSS 클리핑으로 내보냅니다.

### 소유 레이어에 연결한 경로 마스크 { #owner-attached-path-masks }

`LayerMask(shape="path", d="M0 0 H40 V40 H0 Z")`로 사용자 정의 SVG 경로 마스크를 레이어에 직접 연결합니다.

### 경로 모양 매트 { #path-shaped-mattes }

`Canvas.path()` 레이어를 동적으로 움직이는 트랙 매트로 참조해 사용자 정의 애니메이션 컷아웃을 만듭니다.
