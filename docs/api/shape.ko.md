---
description: 사각형, 타원, 캡슐, 삼각형, 별, 다각형을 그리는 quickthumb 도형 레이어의 선, 그림자와 위치를 설명합니다.
---

# 도형 { #shape }

`.shape()`는 위치를 지정한 기본 도형인 사각형, 타원, 캡슐, 삼각형, 별, 다각형을 추가합니다.

## 시그니처 { #signature }

```python
canvas.shape(
    shape,
    position,
    width,
    height,
    color,
    fill=None,
    border_radius=0,
    opacity=1.0,
    rotation=0.0,
    align=None,
    points=None,
    star_points=5,
    inner_radius=0.5,
    effects=None,
)
```

## 매개변수 { #parameters }

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `shape` | `str` | **필수** | 도형 종류. `"rectangle"`, `"ellipse"`, `"pill"`, `"triangle"`, `"star"`, `"polygon"` 중 하나입니다. |
| `position` | `tuple` | **필수** | `(x, y)` 위치. 정수(픽셀)나 백분율 문자열(`"50%"`)을 사용할 수 있습니다. |
| `width` | `int` | **필수** | 도형 너비(픽셀). 양의 정수입니다. |
| `height` | `int` | **필수** | 도형 높이(픽셀). 양의 정수입니다. |
| `color` | `str` | **필수** | 채우기 색상. 16진수 문자열(`"#RRGGBB"` 또는 `"#RRGGBBAA"`)입니다. |
| `fill` | `LinearGradient \| RadialGradient \| None` | `None` | 도형 내부에 칠하고 도형과 함께 회전하는 그라디언트입니다. 그라디언트를 그리지 못하는 대상(PPTX, PDF, SVG, HTML)에는 `color`가 단색 대체 표현으로 남습니다. |
| `border_radius` | `int` | `0` | 모서리 반경(픽셀). `"rectangle"`에만 적용되며 0 이상의 정수입니다. |
| `opacity` | `float` | `1.0` | `0.0`부터 `1.0`까지의 레이어 불투명도입니다. |
| `rotation` | `float` | `0.0` | 회전 각도(도)입니다. |
| `align` | `str \| Align \| tuple \| None` | `None` | `position`이 가리키는 도형의 기준점입니다. [Align](enums.md#align)을 참고하세요. |
| `points` | `list[tuple[float, float]] \| None` | `None` | `"polygon"`의 정점. 도형 상자 안의 `0.0`–`1.0`으로 정규화하며 최소 3개입니다. |
| `star_points` | `int` | `5` | 별의 꼭짓점 수. `"star"`에만 적용되며 최소 3개입니다. |
| `inner_radius` | `float` | `0.5` | `"star"`의 바깥 반경에 대한 안쪽 반경 비율. `0.0`보다 크고 `1.0`보다 작아야 합니다. |
| `effects` | `list \| None` | `[]` | `Stroke`, `Shadow`, `Glow` 효과 목록입니다. |

## 예제 { #examples }

### 라벨 사각형 { #label-rectangle }

```python
from quickthumb import Shadow, Stroke

canvas.shape(
    shape="rectangle",
    position=(64, 64),
    width=320,
    height=96,
    color="#CC0000",
    border_radius=14,
    effects=[
        Stroke(width=3, color="#FFFFFF"),
        Shadow(offset_x=0, offset_y=10, color="#000000", blur_radius=18),
    ],
)
```

### 회전한 배지 { #rotated-badge }

```python
canvas.shape(
    shape="rectangle",
    position=(64, 64),
    width=360,
    height=120,
    color="#CC0000",
    border_radius=16,
    opacity=0.95,
    rotation=-4,
    align=("left", "top"),
)
```

### 타원과 원 { #ellipse-circle }

```python
# Circle: set width == height
canvas.shape(
    shape="ellipse",
    position=("50%", "50%"),
    width=200,
    height=200,
    color="#22d3ee",
    align=("center", "middle"),
)
```

### 캡슐 { #pill }

양 끝이 완전히 둥근 사각형입니다. `border_radius`가 필요하지 않습니다.

```python
canvas.shape(
    shape="pill",
    position=(64, 60),
    width=220,
    height=56,
    color="#B8FF00",
)
```

### 삼각형 { #triangle }

`width` × `height` 상자 안에 들어가는 위쪽 방향의 이등변삼각형입니다.
다른 방향으로 향하게 하려면 `rotation`을 사용하세요.

```python
canvas.shape(
    shape="triangle",
    position=("50%", "20%"),
    width=140,
    height=120,
    color="#F59E0B",
    align=("center", "middle"),
    rotation=180,   # point down
)
```

### 별 { #star }

`star_points`는 꼭짓점 수를, `inner_radius`는 뾰족한 정도를 조절합니다. 값이 작을수록 더 뾰족합니다.

```python
from quickthumb import Glow

canvas.shape(
    shape="star",
    position=("80%", "50%"),
    width=280,
    height=280,
    color="#7C5CFF",
    align=("center", "middle"),
    rotation=12,
    star_points=5,
    inner_radius=0.45,
    effects=[Glow(color="#7C5CFF", radius=40, opacity=0.5)],
)
```

### 다각형 { #polygon }

임의 정점을 도형 상자 기준으로 정규화합니다. `(0.0, 0.0)`은 왼쪽 위, `(1.0, 1.0)`은 오른쪽 아래 모서리입니다.

```python
# A right-pointing arrow
canvas.shape(
    shape="polygon",
    position=(600, 60),
    width=160,
    height=100,
    color="#53BF9D",
    points=[
        (0.0, 0.25), (0.6, 0.25), (0.6, 0.0),
        (1.0, 0.5),
        (0.6, 1.0), (0.6, 0.75), (0.0, 0.75),
    ],
)
```

### 발광 효과가 있는 중앙 도형 { #centered-shape-with-glow }

```python
from quickthumb import Glow

canvas.shape(
    shape="rectangle",
    position=("50%", "80%"),
    width=480,
    height=72,
    color="#111827",
    border_radius=36,
    align=("center", "middle"),
    effects=[Glow(color="#22d3ee", radius=24, opacity=0.4)],
)
```

## 검증 규칙 { #validation-rules }

- `shape`, `position`, `width`, `height`, `color`는 필수입니다.
- `position`은 항목 두 개의 튜플이어야 합니다. 백분율 문자열은 `-?N%` 형식이어야 합니다.
- `border_radius`는 음수일 수 없습니다.
- `opacity`는 `0.0`과 `1.0` 사이여야 합니다.
- `points`는 `"polygon"`에서 필수이며 다른 도형에서는 거부됩니다. 각 값이 `0.0`과 `1.0` 사이로 정규화된 항목이 최소 3개 있어야 합니다.
- `star_points`는 최소 3이어야 하며 `inner_radius`는 `0.0`보다 크고 `1.0`보다 작아야 합니다.
