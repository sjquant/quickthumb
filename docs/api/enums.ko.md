---
description: 정렬, 크기 맞춤, 도형, 필터와 색상 전환에 사용하는 quickthumb 열거형과 그라디언트 모델을 설명합니다.
---

# 열거형과 그라디언트 { #enums-gradients }

## Align { #align }

레이어의 어느 점을 `position`에 맞출지 정하고, 텍스트의 가로 정렬도 제어합니다.

```python
from quickthumb import Align
```

### 값 { #values }

| 열거형 | 문자열 별칭 | 가로 | 세로 |
| --- | --- | --- | --- |
| `Align.CENTER` | `"center"` | 가운데 | 가운데 |
| `Align.LEFT` | `"left"` | 왼쪽 | 가운데 |
| `Align.RIGHT` | `"right"` | 오른쪽 | 가운데 |
| `Align.TOP_LEFT` | `"top-left"` | 왼쪽 | 위 |
| `Align.TOP_CENTER` | `"top-center"` | 가운데 | 위 |
| `Align.TOP_RIGHT` | `"top-right"` | 오른쪽 | 위 |
| `Align.BOTTOM_LEFT` | `"bottom-left"` | 왼쪽 | 아래 |
| `Align.BOTTOM_CENTER` | `"bottom-center"` | 가운데 | 아래 |
| `Align.BOTTOM_RIGHT` | `"bottom-right"` | 오른쪽 | 아래 |

### 사용법 { #usage }

```python
# Enum value
canvas.image(..., align=Align.TOP_LEFT)

# String alias
canvas.image(..., align="center")

# (horizontal, vertical) tuple
canvas.image(..., align=("center", "middle"))
```

튜플의 가로 값은 `"left"`, `"center"`, `"right"`이며 세로 값은 `"top"`, `"middle"`, `"bottom"`입니다.

---

## BlendMode { #blendmode }

앞서 그려진 레이어 위에 합성하는 방식을 제어합니다.

```python
from quickthumb import BlendMode
```

### 값 { #values_1 }

| 열거형 | 문자열 별칭 | 효과 |
| --- | --- | --- |
| `BlendMode.NORMAL` | `"normal"` | 별도 혼합 없이 레이어를 위에 그립니다. |
| `BlendMode.MULTIPLY` | `"multiply"` | 색상 값을 곱해 어둡게 합니다. |
| `BlendMode.OVERLAY` | `"overlay"` | 곱하기와 스크린을 조합합니다. |
| `BlendMode.SCREEN` | `"screen"` | 반전, 곱하기, 재반전으로 밝게 합니다. |
| `BlendMode.DARKEN` | `"darken"` | 픽셀마다 더 어두운 값을 선택합니다. |
| `BlendMode.LIGHTEN` | `"lighten"` | 픽셀마다 더 밝은 값을 선택합니다. |

### 사용법 { #usage_1 }

```python
# Enum value
canvas.background(image="texture.jpg", blend_mode=BlendMode.MULTIPLY)

# String alias
canvas.background(image="texture.jpg", blend_mode="multiply")
```

`.background()`와 `.image()`에서 사용할 수 있습니다.

---

## FitMode { #fitmode }

이미지를 지정한 크기의 상자에 어떤 방식으로 맞출지 정합니다.

```python
from quickthumb import FitMode
```

### 값 { #values_2 }

| 열거형 | 문자열 별칭 | 동작 |
| --- | --- | --- |
| `FitMode.COVER` | `"cover"` | 상자를 채우고 넘치는 부분을 자릅니다. |
| `FitMode.CONTAIN` | `"contain"` | 이미지 전체를 상자 안에 맞추고 나머지는 여백으로 둡니다. |
| `FitMode.FILL` | `"fill"` | 종횡비를 무시하고 상자를 정확히 채우도록 늘립니다. |

### 사용법 { #usage_2 }

```python
# Enum value
canvas.image(path="portrait.png", position=("75%", "55%"), width=420, height=520, fit=FitMode.COVER)

# String alias
canvas.image(path="portrait.png", position=("75%", "55%"), width=420, height=520, fit="cover")
```

`.background(image=...)`와 `.image()`에서 사용할 수 있습니다.
`width`와 `height`를 모두 지정해 목표 상자가 정해진 경우에만 적용됩니다. 배경 레이어는 캔버스 전체가 목표입니다.

---

## LinearGradient { #lineargradient }

각도와 색상 정지점으로 정의하는 선형 그라디언트입니다.

```python
from quickthumb import LinearGradient

LinearGradient(
    angle=135,
    stops=[("#FF5733", 0.0), ("#3333FF", 1.0)],
)
```

| 매개변수 | 자료형 | 설명 |
| --- | --- | --- |
| `angle` | `float` | 그라디언트 방향(도). `0`은 위에서 아래, `90`은 왼쪽에서 오른쪽입니다. |
| `stops` | `list[tuple[str, float]]` | `(color, position)` 튜플 목록입니다. 위치는 `0.0`부터 `1.0`까지의 실수입니다. |

### 예제 { #examples }

```python
# Top-to-bottom dark fade
LinearGradient(angle=0, stops=[("#000000", 0.0), ("#00000000", 1.0)])

# Diagonal blue-to-purple
LinearGradient(angle=135, stops=[("#3B82F6", 0.0), ("#8B5CF6", 1.0)])

# Three-stop gradient
LinearGradient(
    angle=90,
    stops=[("#FF0000", 0.0), ("#00FF00", 0.5), ("#0000FF", 1.0)],
)
```

`.background(gradient=...)`에 전달합니다.

```python
canvas.background(
    gradient=LinearGradient(angle=120, stops=[("#0F172A", 0.0), ("#0F172A00", 1.0)]),
    opacity=0.8,
)
```

---

## RadialGradient { #radialgradient }

중심점에서 퍼지는 방사형 그라디언트입니다.

```python
from quickthumb import RadialGradient

RadialGradient(
    stops=[("#FF5733", 0.0), ("#3333FF", 1.0)],
    center=(0.5, 0.5),
)
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `stops` | `list[tuple[str, float]]` | **필수** | `(color, position)` 튜플 목록입니다. 위치는 `0.0`부터 `1.0`까지의 실수입니다. |
| `center` | `tuple[float, float]` | `(0.5, 0.5)` | 캔버스 크기에 대한 `(x, y)` 비율로 지정하는 중심점입니다. |

### 예제 { #examples_1 }

```python
# Vignette (dark edges, bright center)
RadialGradient(
    stops=[("#00000000", 0.0), ("#000000CC", 1.0)],
    center=(0.5, 0.5),
)

# Off-center spotlight
RadialGradient(
    stops=[("#FFFFFF33", 0.0), ("#FFFFFF00", 1.0)],
    center=(0.25, 0.3),
)
```

`.background(gradient=...)`에 전달합니다.

```python
canvas.background(
    gradient=RadialGradient(
        stops=[("#22d3ee33", 0.0), ("#22d3ee00", 1.0)],
        center=(0.5, 0.5),
    ),
)
```

---

## TextFillImage { #textfillimage }

텍스트 글리프를 채우는 이미지입니다. 텍스트 경계 상자에 맞춰 크기를 조절하고 글리프 모양으로 마스킹합니다.

```python
from quickthumb import TextFillImage

TextFillImage(
    path="fire_texture.jpg",
    fit="cover",
)
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `path` | `str` | **필수** | 채울 이미지의 로컬 파일 경로나 원격 URL입니다. |
| `fit` | `str \| FitMode` | `"cover"` | 텍스트 경계 상자에 맞추는 방식. `"cover"`, `"contain"`, `"fill"` 중 하나입니다. |

### 예제 { #examples_2 }

```python
from quickthumb import Canvas, TextFillImage

# Local file
canvas.text(
    content="FIRE",
    size=140,
    fill=TextFillImage(path="assets/fire_texture.jpg", fit="cover"),
    position=("50%", "50%"),
    align="center",
)

# Remote URL
canvas.text(
    content="MARBLE",
    size=140,
    fill=TextFillImage(
        path="https://example.com/textures/marble.jpg",
        fit="cover",
    ),
    position=("50%", "50%"),
    align="center",
)
```

`.text()`나 `TextPart`의 `fill`에 `TextFillImage`를 전달합니다.
실제 사용법은 [그라디언트와 이미지 채우기](text.md#gradient-and-image-fills)를 참고하세요.
