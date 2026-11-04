---
description: quickthumb 이미지 레이어의 로컬·원격 이미지, 크기 맞춤, 위치, 마스킹, 효과와 배경 제거를 설명합니다.
---

# 이미지 { #image }

`.image()`로 원하는 위치에 이미지를 겹쳐 그립니다. 로컬 파일과 원격 URL을 사용할 수 있으며, 배경 제거와 크기 맞춤, 혼합 모드, 각종 효과를 적용할 수 있습니다.

## 시그니처 { #signature }

```python
canvas.image(
    path,
    position,
    width=None,
    height=None,
    fit=None,
    opacity=1.0,
    rotation=0.0,
    align=Align.TOP_LEFT,
    remove_background=False,
    border_radius=0,
    blend_mode=None,
    effects=None,
)
```

## 매개변수 { #parameters }

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `path` | `str` | **필수** | 로컬 파일 경로나 원격 `http(s)://` URL입니다. |
| `position` | `tuple` | **필수** | `(x, y)` 위치. 정수(픽셀)나 백분율 문자열(`"50%"`)을 사용할 수 있습니다. |
| `width` | `int \| None` | `None` | 목표 너비(픽셀). 한쪽 크기만 지정하면 종횡비를 유지합니다. |
| `height` | `int \| None` | `None` | 목표 높이(픽셀). 한쪽 크기만 지정하면 종횡비를 유지합니다. |
| `fit` | `str \| FitMode \| None` | `None` | `width`와 `height`를 모두 설정했을 때 이미지 크기를 맞추는 방식입니다. [FitMode](enums.md#fitmode)를 참고하세요. |
| `opacity` | `float` | `1.0` | `0.0`부터 `1.0`까지의 레이어 불투명도입니다. |
| `rotation` | `float` | `0.0` | 회전 각도(도)입니다. |
| `align` | `str \| Align \| tuple` | `Align.TOP_LEFT` | `position`이 가리키는 이미지의 기준점입니다. [Align](enums.md#align)을 참고하세요. |
| `remove_background` | `bool` | `False` | AI로 이미지 배경을 제거합니다. `quickthumb[rembg]`가 필요합니다. |
| `border_radius` | `int` | `0` | 둥근 모서리의 반경(픽셀). 0 이상의 정수입니다. |
| `blend_mode` | `str \| BlendMode \| None` | `None` | 합성 혼합 모드입니다. [BlendMode](enums.md#blendmode)를 참고하세요. |
| `effects` | `list \| None` | `[]` | `Stroke`, `Shadow`, `Glow`, `Filter`, `Grain` 효과 목록입니다. |

## 예제 { #examples }

### 기본 오버레이 { #basic-overlay }

```python
canvas.image(
    path="portrait.png",
    position=("74%", "54%"),
    width=420,
    height=520,
    fit="cover",
    align=("center", "middle"),
)
```

### 효과 적용 { #with-effects }

```python
from quickthumb import Filter, Shadow

canvas.image(
    path="portrait.png",
    position=("74%", "54%"),
    width=420,
    height=520,
    fit="cover",
    align=("center", "middle"),
    border_radius=28,
    effects=[
        Filter(contrast=1.1, saturation=1.05),
        Shadow(offset_x=0, offset_y=12, color="#000000", blur_radius=24),
    ],
)
```

### 배경 제거 { #background-removal }

```python
canvas.image(
    path="portrait.jpg",
    position=("75%", "55%"),
    width=430,
    height=540,
    align=("center", "middle"),
    remove_background=True,
)
```

!!! note
    `remove_background=True`에는 Python 3.11 이상과 `uv pip install "quickthumb[rembg]"`가 필요합니다. 처음 사용할 때 ONNX 모델(약 170 MB)을 내려받아 캐시합니다.

### 원격 이미지 { #remote-image }

```python
canvas.image(
    path="https://example.com/avatar.png",
    position=("50%", "50%"),
    width=300,
    height=300,
    align=("center", "middle"),
    border_radius=150,  # circle
)
```

### 종횡비 유지 { #preserve-aspect-ratio }

```python
# Only width: height keeps the image's proportions
canvas.image(path="logo.png", position=(40, 40), width=200)

# Only height: width keeps the image's proportions
canvas.image(path="logo.png", position=(40, 40), height=80)
```

## 크기 맞춤 모드 { #fit-modes }

`fit`은 `width`와 `height`를 모두 설정했을 때 적용됩니다.

| 값 | 동작 |
| --- | --- |
| `"cover"` | 상자를 채우고 필요하면 넘치는 부분을 자릅니다. |
| `"contain"` | 이미지 전체를 상자 안에 맞추고 가장자리에 빈 공간을 남깁니다. |
| `"fill"` | 종횡비를 무시하고 상자를 정확히 채우도록 늘립니다. |

## 검증 규칙 { #validation-rules }

- `path`와 `position`은 필수입니다.
- `position`은 항목 두 개의 튜플이어야 합니다. 백분율 문자열은 `-?N%` 형식이어야 합니다.
- `border_radius`는 음수일 수 없습니다.
- `opacity`는 `0.0`과 `1.0` 사이여야 합니다.
- 올바르지 않은 `path`나 원격 다운로드 실패는 렌더링 시 `RenderingError`를 발생시킵니다.
