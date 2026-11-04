---
description: quickthumb 효과인 외곽선, 그림자, 발광, 필터, 텍스트 배경, 입자, 듀오톤, 내부 그림자, 배경 흐림과 각 레이어의 지원 범위를 설명합니다.
---

# 효과 { #effects }

효과는 개별 레이어를 그리는 방식을 바꿉니다.
각 레이어 종류마다 허용하는 효과가 다르며 지원하지 않는 효과를 전달하면 `ValidationError`가 발생합니다.

| 효과 | 텍스트 | 이미지, SVG, 동영상 | 도형 | 배경 |
| --- | :---: | :---: | :---: | :---: |
| `Stroke` | ✓ | ✓ | ✓ | — |
| `Shadow` | ✓ | ✓ | ✓ | — |
| `Glow` | ✓ | ✓ | ✓ | — |
| `Filter` | — | ✓ | — | ✓ |
| `Background` | ✓ | — | — | — |
| `Grain` | — | ✓ | — | ✓ |
| `Duotone` | — | ✓ | — | — |
| `InnerShadow` | — | ✓ | ✓ | — |
| `BackdropBlur` | — | ✓ | ✓ | — |

레이어의 `effects` 매개변수에 효과 목록을 전달합니다.

```python
from quickthumb import Shadow, Stroke

canvas.text(
    content="CLICK NOW",
    size=96,
    color="#FFFFFF",
    effects=[
        Stroke(width=4, color="#000000"),
        Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
    ],
)
```

---

## Stroke { #stroke }

텍스트 글리프, 이미지 가장자리, 도형 가장자리에 외곽선을 그립니다.

```python
from quickthumb import Stroke

Stroke(width=4, color="#000000")
```

| 매개변수 | 자료형 | 설명 |
| --- | --- | --- |
| `width` | `int` | 외곽선 두께(픽셀). 양의 정수입니다. |
| `color` | `str` | 외곽선 색상. 16진수 문자열(`"#RRGGBB"` 또는 `"#RRGGBBAA"`)입니다. |

### 예제 { #example }

```python
from quickthumb import Stroke, TextPart

canvas.text(
    content=[
        TextPart(text="BIG TEXT", color="#FFFFFF", effects=[Stroke(width=6, color="#000000")]),
    ],
    size=108,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

---

## Shadow { #shadow }

레이어에서 떨어진 위치에 그림자를 추가합니다.

```python
from quickthumb import Shadow

Shadow(offset_x=4, offset_y=8, color="#000000", blur_radius=12)
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `offset_x` | `int` | **필수** | 가로 그림자 오프셋(픽셀). 음수도 가능합니다. |
| `offset_y` | `int` | **필수** | 세로 그림자 오프셋(픽셀). 음수도 가능합니다. |
| `color` | `str` | **필수** | 그림자 색상. 16진수 문자열입니다. |
| `blur_radius` | `int` | `0` | 흐림 확산 반경(픽셀). 0 이상의 정수입니다. |

### 예제 { #example_1 }

```python
from quickthumb import Shadow

canvas.image(
    path="portrait.png",
    position=("74%", "54%"),
    width=420,
    height=520,
    effects=[Shadow(offset_x=0, offset_y=14, color="#000000", blur_radius=24)],
)
```

---

## Glow { #glow }

레이어 주위에 부드러운 색상의 후광을 추가합니다.

```python
from quickthumb import Glow

Glow(color="#B8FF00", radius=16, opacity=0.35)
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `color` | `str` | **필수** | 발광 색상. 16진수 문자열입니다. |
| `radius` | `int` | **필수** | 발광 확산 반경(픽셀). 양의 정수입니다. |
| `opacity` | `float` | `1.0` | `0.0`부터 `1.0`까지의 발광 강도입니다. |

### 예제 { #example_2 }

```python
from quickthumb import Glow

canvas.text(
    content="ELECTRIC",
    size=96,
    color="#FFFFFF",
    effects=[Glow(color="#22d3ee", radius=24, opacity=0.5)],
)
```

---

## Filter { #filter }

이미지 처리 조정을 적용합니다. 배경 레이어와 이미지 레이어에 사용합니다.

```python
from quickthumb import Filter

Filter(blur=4, brightness=0.75, contrast=1.1, saturation=0.9)
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `blur` | `int` | `0` | 가우시안 흐림 반경. 0 이상의 정수입니다. |
| `brightness` | `float` | `1.0` | 밝기 배수. 양의 실수입니다. `1.0`은 변화 없음, `0.5`는 절반 밝기입니다. |
| `contrast` | `float` | `1.0` | 대비 배수. 양의 실수입니다. `1.0`은 변화가 없습니다. |
| `saturation` | `float` | `1.0` | 채도 배수. 0 이상의 실수입니다. `0.0`은 회색조, `1.0`은 변화가 없습니다. |

모든 매개변수의 기본값은 중립값이므로 바꿀 항목만 설정하면 됩니다.

### 예제 { #example_3 }

```python
from quickthumb import Filter

canvas.background(
    image="hero.jpg",
    fit="cover",
    effects=[Filter(blur=6, brightness=0.6, saturation=0.8)],
)
```

---

## Background(텍스트 채우기) { #background-text-fill }

텍스트 블록 뒤에 채워진 둥근 사각형을 그립니다. 텍스트 레이어에서만 사용할 수 있습니다.

```python
from quickthumb import Background

Background(color="#111827CC", padding=(16, 24), border_radius=14, opacity=1.0)
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `color` | `str` | **필수** | 채우기 색상. 16진수 문자열(`"#RRGGBB"` 또는 `"#RRGGBBAA"`)입니다. |
| `padding` | `int \| tuple` | `0` | 안쪽 여백. 균일한 `int`, `(vertical, horizontal)` 또는 `(top, right, bottom, left)`입니다. |
| `border_radius` | `int` | `0` | 모서리 반경(픽셀). 0 이상의 정수입니다. |
| `opacity` | `float` | `1.0` | `0.0`부터 `1.0`까지의 채우기 불투명도입니다. |

### 예제 { #example_4 }

```python
from quickthumb import Background

canvas.text(
    content="BREAKING NEWS",
    size=72,
    color="#FFFFFF",
    position=("8%", "50%"),
    align=("left", "middle"),
    effects=[
        Background(color="#CC0000", padding=(12, 20), border_radius=8),
    ],
)
```

!!! note
    `Background` 효과는 `.background()` 레이어 빌더와 별개입니다. 효과는 텍스트 블록 뒤에 적용되고 레이어는 캔버스 전체를 덮습니다.

---

## Grain { #grain }

배경이나 이미지 레이어에 필름 입자 노이즈를 추가합니다.

```python
from quickthumb import Grain

Grain(intensity=0.12, monochrome=True, blend_mode="overlay", opacity=1.0)
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `intensity` | `float` | **필수** | `0.0`(없음)부터 `1.0`(최대)까지의 노이즈 진폭입니다. |
| `monochrome` | `bool` | `True` | `True`는 휘도 노이즈(회색 입자), `False`는 채널별로 독립된 색상 노이즈입니다. |
| `blend_mode` | `str` | `"overlay"` | 노이즈를 레이어에 합성하는 방식. `"overlay"`, `"screen"`, `"multiply"`, `"normal"` 중 하나입니다. |
| `opacity` | `float` | `1.0` | `0.0`(보이지 않음)부터 `1.0`(전체)까지의 전반적인 입자 강도입니다. |
| `seed` | `int \| None` | `None` | 결정적인 출력에 사용할 난수 시드입니다. `None`이면 렌더링할 때마다 무작위입니다. |

`intensity=0.0`이면 노이즈를 추가하지 않습니다.

### 예제 { #example_5 }

```python
from quickthumb import Canvas, Grain

canvas = (
    Canvas(1280, 720)
    .background(
        color="#1A1A2E",
        effects=[Grain(intensity=0.12, monochrome=True)],
    )
    .image(
        path="portrait.png",
        position=("70%", "50%"),
        width=400,
        height=500,
        align=("center", "middle"),
        effects=[Grain(intensity=0.08, monochrome=False, blend_mode="overlay", opacity=0.6)],
    )
)
```

!!! note
    `Grain`은 배경, 이미지, SVG, 동영상 레이어에서 동작하며 텍스트나 도형에는 적용되지 않습니다.

---

## Duotone { #duotone }

밝기에 따라 레이어를 두 색상에 대응시킵니다.
어두운 부분은 `shadows`, 밝은 부분은 `highlights` 색상을 사용하며 그 사이를 부드럽게 혼합합니다.
사진에 브랜드 색상을 입힐 때 유용합니다.

```python
from quickthumb import Duotone

Duotone(shadows="#0A1730", highlights="#7FADFF", opacity=1.0)
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `shadows` | `str` | **필수** | 이미지의 가장 어두운 부분에 사용할 색상입니다. |
| `highlights` | `str` | **필수** | 이미지의 가장 밝은 부분에 사용할 색상입니다. |
| `opacity` | `float` | `1.0` | 원래 색상을 대체하는 강도. `0.0`부터 `1.0`까지입니다. |

---

## InnerShadow { #innershadow }

레이어 가장자리 안쪽에 그림자를 그려 눌린 듯한 모습을 만듭니다.

```python
from quickthumb import InnerShadow

InnerShadow(offset_x=0, offset_y=6, color="#00000080", blur_radius=12)
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `color` | `str` | **필수** | 그림자 색상. 색상의 알파 값을 반영합니다. |
| `offset_x` | `int` | `0` | 가로 오프셋(픽셀)입니다. |
| `offset_y` | `int` | `0` | 세로 오프셋(픽셀)입니다. |
| `blur_radius` | `int` | `0` | 흐림 반경(픽셀)입니다. |
| `opacity` | `float` | `1.0` | 전반적인 강도. `0.0`부터 `1.0`까지입니다. |

---

## BackdropBlur { #backdropblur }

불투명 유리처럼 레이어 모양 안에서 뒤에 이미 그려진 내용을 흐리게 합니다.
반투명 채우기와 조합하면 패널 형태도 드러납니다.

```python
from quickthumb import BackdropBlur, Canvas

canvas = (
    Canvas(1280, 720)
    .background(image="photo.jpg", fit="cover")
    .shape(
        shape="rectangle",
        position=(80, 440),
        width=640,
        height=200,
        color="#FFFFFF33",
        border_radius=24,
        effects=[BackdropBlur(radius=24)],
    )
)
```

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `radius` | `int` | **필수** | 흐림 반경(픽셀)입니다. |
| `opacity` | `float` | `1.0` | 흐려진 배경을 표시하는 강도. `0.0`부터 `1.0`까지입니다. |
