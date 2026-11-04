---
description: quickthumb 배경 레이어의 색상, 그라디언트, 이미지, 불투명도, 효과와 렌더링 순서를 설명합니다.
---

# 배경 { #background }

`.background()`는 캔버스 전체를 덮는 배경 레이어를 추가합니다. 여러 번 호출하면 렌더링 순서대로 쌓이며 처음 호출한 배경이 가장 뒤에 놓입니다.

## 시그니처 { #signature }

```python
canvas.background(
    color=None,
    gradient=None,
    image=None,
    opacity=1.0,
    blend_mode=None,
    fit=None,
    effects=None,
)
```

## 매개변수 { #parameters }

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `color` | `str \| tuple \| None` | `None` | 단색 채우기. 16진수 문자열(`"#RRGGBB"` 또는 `"#RRGGBBAA"`)이나 RGB/RGBA 튜플입니다. |
| `gradient` | `LinearGradient \| RadialGradient \| None` | `None` | 그라디언트 채우기. [열거형과 그라디언트](enums.md)를 참고하세요. |
| `image` | `str \| None` | `None` | 로컬 파일 경로나 원격 URL입니다. |
| `opacity` | `float` | `1.0` | `0.0`(투명)부터 `1.0`(불투명)까지의 레이어 불투명도입니다. |
| `blend_mode` | `str \| BlendMode \| None` | `None` | 이전 레이어 위에 합성하는 방식입니다. [BlendMode](enums.md#blendmode)를 참고하세요. |
| `fit` | `str \| FitMode \| None` | `None` | 이미지로 캔버스를 채우는 방식입니다. [FitMode](enums.md#fitmode)를 참고하세요. |
| `effects` | `list \| None` | `[]` | 배경 효과입니다. `Filter`와 `Grain`을 받습니다. |

## 예제 { #examples }

### 단색 { #solid-color }

```python
canvas.background(color="#0F172A")
```

### 그라디언트 오버레이 { #gradient-overlay }

```python
from quickthumb import LinearGradient

canvas.background(
    gradient=LinearGradient(
        angle=120,
        stops=[("#111827", 0.0), ("#11182700", 1.0)],
    ),
    opacity=0.7,
)
```

### 효과가 있는 원격 이미지 { #remote-image-with-effects }

```python
from quickthumb import Filter

canvas.background(
    image="https://images.unsplash.com/photo-1516321318423-f06f85e504b3",
    fit="cover",
    blend_mode="multiply",
    effects=[Filter(blur=4, brightness=0.75, contrast=1.1, saturation=0.9)],
)
```

### 어두운 오버레이 { #dark-overlay }

```python
canvas.background(color="#000000", opacity=0.4)
```

## 참고 { #notes }

- 배경 레이어는 항상 캔버스 전체를 덮습니다.
- `color`, `gradient`, `image`를 각각 독립적으로 사용하거나 한 레이어에서 함께 사용할 수 있습니다.
- `blend_mode`는 이 레이어를 이전 레이어 위에 합성할 때 적용됩니다.
- `image`는 로컬 파일 경로와 원격 URL을 모두 지원합니다.
- 사용할 수 있는 효과는 [Filter](effects.md#filter)와 [Grain](effects.md#grain)을 참고하세요.
