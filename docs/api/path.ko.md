---
description: 로컬 viewBox, 그라디언트, 점선과 경로 애니메이션을 사용해 채움 또는 선이 있는 SVG 경로를 그립니다.
---

# 경로 { #path }

`Canvas.path()`는 외부 SVG 파일이나 추가 의존성 없이 표준 SVG 경로 데이터(`d`)로 채움 또는 선이 있는 벡터 경로를 그립니다.

```python
from quickthumb import Canvas

canvas = Canvas(160, 120).path(
    "M 0 0 H 100 V 100 H 0 Z M 25 25 H 75 V 75 H 25 Z",
    position=(20, 10),
    width=120,
    height=100,
    view_box=(0, 0, 100, 100),
    color="#42CEB7",
)
canvas.export("path.png")
```

## 매개변수 { #parameters }

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `d` | `str` | **필수** | SVG 경로 명령(`M`, `L`, `H`, `V`, `C`, `S`, `Q`, `T`, `A`, `Z`)입니다. |
| `position` | `tuple` | **필수** | 픽셀이나 백분율 문자열(`"50%"`)로 표현한 `(x, y)` 위치입니다. |
| `width` | `int` | **필수** | 프레임 너비(픽셀)입니다. |
| `height` | `int` | **필수** | 프레임 높이(픽셀)입니다. |
| `view_box` | `tuple \| None` | `None` | 로컬 좌표 영역 `(x, y, width, height)`. 기본값은 `(0, 0, width, height)`입니다. |
| `color` | `str \| None` | `"#000000"` | 단색 채우기 색상입니다. 선만 있는 경로는 `None`으로 설정합니다. |
| `fill` | `LinearGradient \| RadialGradient \| None` | `None` | 그라디언트 채우기. 지정하면 `color`를 대체합니다. |
| `stroke` | `str \| None` | `None` | 선 색상(16진수 문자열)입니다. |
| `stroke_width` | `int \| float` | `1` | 로컬 단위의 선 두께입니다. |
| `line_cap` | `str` | `"butt"` | 끝점 모양. `"butt"`, `"round"`, `"square"` 중 하나입니다. |
| `line_join` | `str` | `"miter"` | 모서리 연결 모양. `"miter"`, `"bevel"`, `"round"` 중 하나입니다. |
| `miter_limit` | `float` | `4` | 베벨로 바뀌기 전까지 허용하는 최대 마이터 비율입니다. |
| `dash_array` | `tuple \| None` | `None` | 길이로 표현한 점선 패턴 `(dash, gap, ...)`입니다. |
| `dash_offset` | `float` | `0` | 점선 패턴의 시작 위상 오프셋입니다. |
| `rotation` | `float` | `0.0` | 회전 각도(도)입니다. |
| `opacity` | `float` | `1.0` | `0.0`부터 `1.0`까지의 레이어 불투명도입니다. |
| `anchor` | `tuple` | `(0.5, 0.5)` | 회전과 크기 조절에 사용하는 정규화된 피벗입니다. |
| `animation` | `AnimationSpec \| None` | `None` | 이동, 트림, 점선 위상, 모핑을 위한 타임라인 애니메이션입니다. |

## 예제 { #examples }

### 점선 외곽선이 있는 곡선 { #stroked-curves-with-dashed-outline }

```python
canvas.path(
    "M10 50 C30 0 70 100 90 50",
    position=(20, 10),
    width=120,
    height=100,
    color=None,
    stroke="#42CEB7",
    stroke_width=6,
    line_cap="round",
    view_box=(0, 0, 100, 100),
    dash_array=(12, 6),
    dash_offset=3,
)
```

### 내부가 뚫린 그라디언트 채우기 { #gradient-fill-with-cutouts }

경로는 **짝홀 채우기 규칙**을 사용하므로 겹치는 내부 윤곽이 자연스럽게 빈 공간이나 구멍을 만듭니다.

```python
from quickthumb import LinearGradient

canvas.path(
    "M10 10 H90 V90 H10 Z M30 30 H70 V70 H30 Z",
    position=(20, 10),
    width=120,
    height=100,
    color=None,
    fill=LinearGradient(angle=45, stops=[("#42CEB7", 0), ("#315D8E", 1)]),
    view_box=(0, 0, 100, 100),
)
```

## 경로 애니메이션 { #path-animations }

### 점선 위상 애니메이션(움직이는 점선) { #animated-dash-phase-marching-ants }

`DashOffsetTrack`을 애니메이션으로 바꾸면 점선이 기어가는 효과를 만들 수 있습니다.

```python
from quickthumb import AnimationSpec, DashOffsetTrack, KeyframeSpec, TimingSpec

phase_animation = AnimationSpec.timeline(
    DashOffsetTrack(keyframes=[
        KeyframeSpec(time=0, value=0),
        KeyframeSpec(time=1, value=20),
    ]),
    timing=TimingSpec(duration=1),
    easing="linear",
)

canvas.path(
    "M0 10 H100",
    position=(10, 10),
    width=200,
    height=20,
    color=None,
    stroke="#42CEB7",
    dash_array=(6, 4),
    animation=phase_animation,
)
```

### 선 트림(스스로 그려지는 선) { #stroke-trim-self-drawing-line }

`TrimEndTrack`을 사용하면 시작부터 끝까지 선이나 외곽선을 점진적으로 그릴 수 있습니다.

```python
from quickthumb import AnimationSpec, KeyframeSpec, TimingSpec, TrimEndTrack

draw_outline = AnimationSpec.timeline(
    TrimEndTrack(keyframes=[
        KeyframeSpec(time=0, value=0.0),
        KeyframeSpec(time=1.5, value=1.0),
    ]),
    timing=TimingSpec(duration=1.5),
    easing="ease_in_out",
)

canvas.path(
    "M0 20 Q50 -10 100 20",
    position=(20, 20),
    width=200,
    height=60,
    view_box=(0, -10, 100, 30),
    color=None,
    stroke="#42CEB7",
    stroke_width=4,
    animation=draw_outline,
)
```

- `TrimStartTrack`과 `TrimEndTrack`: 전체 경로 길이에 대한 정규화된 끝점(`0.0`부터 `1.0`)입니다.
- `TrimOffsetTrack`: 트림된 구간을 경로를 따라 이동시킵니다.

### 경로 모핑 { #path-morphing }

`PathMorphTrack`으로 한 벡터 도형을 다른 도형으로 부드럽게 변형할 수 있습니다.

```python
from quickthumb import AnimationSpec, KeyframeSpec, PathMorphTrack, TimingSpec

morph = AnimationSpec.timeline(
    PathMorphTrack(keyframes=[
        KeyframeSpec(time=0, value="M10 10 H50 V50 H10 Z"),
        KeyframeSpec(time=1, value="M20 20 H60 V60 H20 Z"),
    ]),
    timing=TimingSpec(duration=1),
    easing="ease_in_out",
)

canvas.path(
    "M10 10 H50 V50 H10 Z",
    position=(10, 10),
    width=100,
    height=100,
    color="#42CEB7",
    animation=morph,
)
```

각 키에는 퇴화하지 않은 윤곽이 1–16개 있어야 합니다.
윤곽의 개수, 순서, 열림/닫힘 상태, 감기는 방향, 중첩 구조가 서로 같아야 합니다.
전환 도중을 포함해 윤곽끼리 교차하거나 닿으면 안 됩니다.
호환되지 않는 키는 `path_morph_topology` 오류를 발생시키며, 중간 도형이 올바르지 않으면 위상 구조를 바꾸는 대신 렌더링 중 실패합니다.

복잡한 외곽선은 윤곽당 세분화 정점 256개, 대응점 4096개, 변 쌍 검사 100만 회 제한을 초과할 수 있습니다.
재표본화는 원래 정점에서 로컬 SVG 단위 ¼ 이내를 유지해야 하며 확대하면 근사 오차가 보일 수 있습니다.
모핑 준비 단계에서 거부되면 경로를 단순화하세요.

## 내보내기 지원 { #export-support }

- **래스터와 동영상(PNG, GIF, MP4, WebM)**: 경로, 점선, 트림, 모핑 애니메이션을 렌더링합니다.
- **Lottie**: 지원되는 [경로 모핑 애니메이션](../reference/export-lottie.md#lottie-path-morph)을 벡터로 내보냅니다.
- **HTML**: 지원되는 열린 경로에 네이티브 SVG 렌더링과 CSS 선 애니메이션을 사용합니다. 모핑 애니메이션은 제작된 정지 이미지를 사용합니다.
- **PDF와 PPTX**: 지원되는 경로를 벡터로 내보냅니다. 모핑 애니메이션은 제작된 정지 이미지를 사용합니다.
