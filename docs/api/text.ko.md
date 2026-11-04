---
description: quickthumb 텍스트 레이어의 부분별 서식, 글꼴, 정렬, 줄바꿈, 외곽선, 그림자와 크기 조절을 설명합니다.
---

# 텍스트 { #text }

`.text()`는 텍스트 레이어를 추가합니다.
일반 문자열을 넣거나, 부분마다 서식을 다르게 지정할 수 있도록 `TextPart` 목록을 전달할 수 있습니다.

## 시그니처 { #signature }

```python
canvas.text(
    content,
    font=None,
    font_source="auto",
    font_variations=None,
    emoji_style="monochrome",
    size=None,
    color=None,
    fill=None,
    position=None,
    align=None,
    bold=False,
    italic=False,
    weight=None,
    max_width=None,
    max_height=None,
    min_size=1,
    balance_lines=False,
    effects=None,
    line_height=None,
    letter_spacing=None,
    auto_scale=False,
    rotation=0.0,
    opacity=1.0,
)
```

## 매개변수 { #parameters }

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `content` | `str \| list[TextPart]` | **필수** | 텍스트 내용. 일반 문자열이나 서식 있는 텍스트용 `TextPart` 목록입니다. |
| `font` | `str \| None` | `None` | 글꼴 모음 이름, 로컬 파일 경로 또는 원격 웹 글꼴 URL입니다. |
| `font_source` | `"auto" \| "system" \| "google"` | `"auto"` | 글꼴 검색 소스. `"google"`은 해당 이름의 Google Font를 불러와 캐시합니다. |
| `font_variations` | `dict[str, float] \| None` | `None` | `{"wght": 650}` 같은 OpenType 가변 축 값입니다. |
| `emoji_style` | `"monochrome" \| "color"` | `"monochrome"` | 이모지 표시 방식입니다. |
| `size` | `int \| None` | `None` | 글꼴 크기(픽셀). 양의 정수여야 합니다. |
| `color` | `str \| None` | `None` | 기본 텍스트 색상. 16진수 문자열(`"#RRGGBB"` 또는 `"#RRGGBBAA"`)입니다. |
| `fill` | `LinearGradient \| RadialGradient \| TextFillImage \| None` | `None` | 글리프에 적용하는 그라디언트 또는 이미지 채우기입니다. 설정하면 `color`보다 시각적으로 우선합니다. [그라디언트와 이미지 채우기](#gradient-and-image-fills)를 참고하세요. |
| `position` | `tuple \| None` | `None` | `(x, y)` 위치. 정수(픽셀)나 백분율 문자열(`"50%"`)을 사용할 수 있습니다. |
| `align` | `str \| Align \| tuple \| None` | `None` | 텍스트 블록 정렬. [Align 값](#align-values)을 참고하세요. |
| `bold` | `bool` | `False` | 굵게 표시하는 설정. `weight`와 함께 사용할 수 없습니다. |
| `italic` | `bool` | `False` | 기울임꼴 설정입니다. |
| `weight` | `int \| str \| None` | `None` | CSS 방식의 글꼴 굵기(예: `700`, `900`, `"bold"`). `bold`와 함께 사용할 수 없습니다. |
| `max_width` | `int \| str \| None` | `None` | 줄바꿈 너비. 픽셀이나 백분율 문자열(예: `"60%"`)입니다. |
| `max_height` | `int \| str \| None` | `None` | 텍스트 블록 최대 높이. 픽셀이나 백분율 문자열입니다. |
| `min_size` | `int` | `1` | 자동 맞춤에서 허용하는 가장 작은 글꼴 크기입니다. |
| `balance_lines` | `bool` | `False` | `max_width`가 설정되면 줄 길이의 균형을 맞춥니다. |
| `effects` | `list \| None` | `[]` | `Stroke`, `Shadow`, `Glow`, `Background` 효과 목록입니다. |
| `line_height` | `float \| None` | `None` | 줄 높이 배수. 양의 실수입니다. |
| `letter_spacing` | `int \| None` | `None` | 가로 자간 조절값(픽셀)입니다. |
| `auto_scale` | `bool` | `False` | 텍스트가 `max_width` 및/또는 `max_height` 안에 들어올 때까지 글꼴을 줄입니다. |
| `rotation` | `float` | `0.0` | 회전 각도(도)입니다. |
| `opacity` | `float` | `1.0` | `0.0`부터 `1.0`까지의 레이어 불투명도입니다. |

## Align 값 { #align-values }

`align`은 다음 형식 중 하나를 받습니다.

```python
align="center"              # shorthand
align="top-left"            # compound string
align=("left", "middle")    # (horizontal, vertical) tuple
align=Align.BOTTOM_RIGHT    # enum
```

| 문자열 | 열거형 | 위치 |
| --- | --- | --- |
| `"center"` | `Align.CENTER` | 가로·세로 가운데 |
| `"left"` | `Align.LEFT` | 왼쪽 정렬, 세로 가운데 |
| `"right"` | `Align.RIGHT` | 오른쪽 정렬, 세로 가운데 |
| `"top-left"` | `Align.TOP_LEFT` | 왼쪽 위 모서리 |
| `"top-center"` | `Align.TOP_CENTER` | 위쪽 가장자리의 가로 중앙 |
| `"top-right"` | `Align.TOP_RIGHT` | 오른쪽 위 모서리 |
| `"bottom-left"` | `Align.BOTTOM_LEFT` | 왼쪽 아래 모서리 |
| `"bottom-center"` | `Align.BOTTOM_CENTER` | 아래쪽 가장자리의 가로 중앙 |
| `"bottom-right"` | `Align.BOTTOM_RIGHT` | 오른쪽 아래 모서리 |

튜플을 사용할 때 가로 값은 `left`, `center`, `right`, 세로 값은 `top`, `middle`, `bottom`입니다.

## 예제 { #examples }

### 일반 텍스트 { #plain-text }

```python
canvas.text(
    content="Hello World",
    size=64,
    color="#FFFFFF",
    align="center",
)
```

### `TextPart`로 서식 지정 { #rich-text-with-textpart }

```python
from quickthumb import Stroke, TextPart

canvas.text(
    content=[
        TextPart(text="5 ", color="#FBBF24", weight=900),
        TextPart(text="WARNING SIGNS", color="#FFFFFF", weight=900),
    ],
    size=72,
    position=("8%", "55%"),
    align=("left", "middle"),
)
```

### 효과 적용 { #with-effects }

```python
from quickthumb import Background, Glow, Shadow, Stroke

canvas.text(
    content="BREAKING",
    size=96,
    color="#FFFFFF",
    position=("8%", "50%"),
    align=("left", "middle"),
    weight=900,
    max_width="65%",
    effects=[
        Stroke(width=4, color="#000000"),
        Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
        Glow(color="#B8FF00", radius=16, opacity=0.25),
        Background(color="#111827CC", padding=(16, 24), border_radius=14),
    ],
)
```

### 크기에 맞춰 자동 축소 { #auto-scale-to-fit }

```python
canvas.text(
    content="This is a very long title that should fit",
    size=80,
    color="#FFFFFF",
    max_width="70%",
    auto_scale=True,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

### 웹 글꼴 사용 { #using-a-webfont }

```python
canvas.text(
    content="Custom Font",
    font="https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hiA.woff2",
    size=72,
    color="#FFFFFF",
    align="center",
)
```

!!! note "웹 글꼴 URL"
    `font`가 URL이면 이미 특정 파일을 가리키므로 `bold`, `italic`, `weight`는 무시됩니다. 스타일별로 다른 URL을 사용하거나 글꼴 모음 이름과 `font_source="google"`을 지정해 `weight`와 `italic`에 따라 파일을 선택하게 하세요.

### 그라디언트와 이미지 채우기 { #gradient-and-image-fills }

단색 대신 그라디언트나 이미지로 글리프를 채웁니다.
`fill`에 `LinearGradient`, `RadialGradient`, `TextFillImage`를 전달하세요.

```python
from quickthumb import Canvas, LinearGradient, RadialGradient, TextFillImage, TextPart

# Linear gradient headline
canvas.text(
    content="GRADIENT",
    size=120,
    fill=LinearGradient(angle=90, stops=[("#FF6B6B", 0.0), ("#4ECDC4", 1.0)]),
    position=("50%", "50%"),
    align="center",
)

# Image-filled text
canvas.text(
    content="TEXTURE",
    size=140,
    fill=TextFillImage(path="fire_texture.jpg", fit="cover"),
    position=("50%", "50%"),
    align="center",
)

# Per-segment fills using TextPart
canvas.text(
    content=[
        TextPart(
            text="HOT ",
            fill=LinearGradient(angle=45, stops=[("#FF4500", 0.0), ("#FFD700", 1.0)]),
            weight=900,
        ),
        TextPart(
            text="COLD",
            fill=LinearGradient(angle=45, stops=[("#00BFFF", 0.0), ("#8A2BE2", 1.0)]),
            weight=900,
        ),
    ],
    size=110,
    position=("50%", "50%"),
    align="center",
)
```

`TextPart`에 `fill`을 지정하면 해당 부분에만 적용되며, 레이어 전체의 `fill`보다 우선합니다. `fill`과 `color`는 따로 설정할 수 있지만, 둘 다 있으면 실제로 보이는 색은 `fill`이 결정합니다.
이미지 채우기 옵션은 [TextFillImage](enums.md#textfillimage)를 참고하세요.

## TextPart { #textpart }

`TextPart`는 텍스트 레이어 안에서 구간별 서식을 지정합니다.

```python
from quickthumb import Stroke, TextPart

TextPart(
    text="HOT",
    color="#FF3B30",
    fill=None,
    size=56,
    font="Impact",
    font_source=None,
    font_variations=None,
    emoji_style=None,
    weight=900,
    italic=False,
    line_height=None,
    letter_spacing=0,
    effects=[Stroke(width=3, color="#000000")],
)
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `text` | `str` | **필수** | 텍스트 구간. 빈 문자열일 수 없습니다. |
| `color` | `str \| None` | `None` | 이 구간에 덮어쓸 16진수 색상입니다. |
| `fill` | `LinearGradient \| RadialGradient \| TextFillImage \| None` | `None` | 이 구간의 그라디언트·이미지 채우기. 해당 구간에서만 레이어의 `fill`을 덮어씁니다. |
| `size` | `int \| None` | `None` | 이 구간의 글꼴 크기를 덮어씁니다. |
| `font` | `str \| None` | `None` | 이 구간의 글꼴을 덮어씁니다. |
| `font_source` | `"auto" \| "system" \| "google" \| None` | `None` | 글꼴 소스 재정의. `None`은 레이어에서 상속하고 명시한 값은 덮어씁니다. |
| `font_variations` | `dict[str, float] \| None` | `None` | 가변 축 재정의. `None`은 상속하며 `{}`는 상속된 축을 명시적으로 지웁니다. |
| `emoji_style` | `"monochrome" \| "color" \| None` | `None` | 이모지 스타일 재정의. `None`은 상속하며 `"monochrome"`은 명시적으로 덮어씁니다. |
| `bold` | `bool \| None` | `None` | 굵게 표시를 덮어씁니다. `weight`와 함께 사용할 수 없습니다. |
| `italic` | `bool \| None` | `None` | 기울임꼴을 덮어씁니다. |
| `weight` | `int \| str \| None` | `None` | 글꼴 굵기를 덮어씁니다. `bold`와 함께 사용할 수 없습니다. |
| `line_height` | `float \| None` | `None` | 줄 높이 배수를 덮어씁니다. |
| `letter_spacing` | `int \| None` | `None` | 자간을 덮어씁니다. |
| `effects` | `list[TextEffect]` | `[]` | 구간별 효과인 `Stroke`, `Shadow`, `Glow`, `Background`를 지정합니다. |

## 텍스트 애니메이션 { #text-animations }

`RangeSelector`로 단어별 또는 문자별로 텍스트를 애니메이션화할 수 있습니다.

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

선택기 모양, 타이밍, 색상 전환은 [텍스트 범위 선택기](video.md#text-range-selectors)를 참고하세요.

## 검증 규칙 { #validation-rules }

- `content`는 필수이며 빈 목록일 수 없습니다.
- `TextPart.text`는 빈 문자열일 수 없습니다.
- `TextLayer`와 `TextPart` 모두 `weight`와 `bold=True`를 함께 사용할 수 없습니다.
- `auto_scale=True`에는 `max_width` 또는 `max_height`가 필요합니다.
- `max_width`는 양의 정수이거나 `"60%"` 같은 양의 백분율 문자열이어야 합니다.
- `position`의 백분율 문자열은 `-?N%` 형식이어야 합니다. 음수 백분율도 유효합니다.
- `fill`과 `color`는 독립 필드이며 함께 설정되면 `fill`이 시각적으로 우선합니다.
- `TextFillImage.path`는 로컬 파일 경로와 원격 URL을 지원합니다. 로컬 파일이 없으면 렌더링 시 `FileNotFoundError`가 발생합니다.
