---
description: 아이콘과 로고를 렌더링할 때 래스터화하는 quickthumb SVG 레이어의 크기, 정렬, 혼합 모드와 효과를 설명합니다.
---

# SVG { #svg }

`.svg()`로 캔버스 위에 SVG 이미지를 겹쳐 그립니다. 렌더링할 때 필요한 크기로 래스터화하므로, 출력 크기가 달라져도 선명해야 하는 아이콘이나 로고, 벡터 장식에 적합합니다.

!!! note "선택 의존성"
    SVG 레이어에는 `svg` 추가 기능([cairosvg](https://cairosvg.org/))이 필요합니다.

    ```bash
    pip install "quickthumb[svg]"
    ```

    이를 설치하지 않고 `svg` 레이어가 있는 캔버스를 렌더링하면 `RenderingError`가 발생합니다.

## 시그니처 { #signature }

```python
canvas.svg(
    path,
    position,
    width=None,
    height=None,
    opacity=1.0,
    rotation=0.0,
    align=Align.TOP_LEFT,
    effects=None,
    blend_mode=None,
)
```

## 매개변수 { #parameters }

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `path` | `str` | **필수** | SVG 문서의 로컬 파일 경로나 URL입니다. |
| `position` | `tuple` | **필수** | `(x, y)` 위치. 정수(픽셀)나 백분율 문자열(`"50%"`)을 사용할 수 있습니다. |
| `width` | `int \| None` | `None` | 출력 래스터 너비(픽셀). `height`를 생략하면 종횡비를 유지합니다. |
| `height` | `int \| None` | `None` | 출력 래스터 높이(픽셀). `width`를 생략하면 종횡비를 유지합니다. |
| `opacity` | `float` | `1.0` | `0.0`부터 `1.0`까지의 레이어 불투명도입니다. |
| `rotation` | `float` | `0.0` | 회전 각도(도)입니다. |
| `align` | `str \| Align \| tuple` | `Align.TOP_LEFT` | `position`이 가리키는 레이어의 기준점입니다. [Align](enums.md#align)을 참고하세요. |
| `effects` | `list \| None` | `[]` | 이미지 레이어와 같은 효과인 `Stroke`, `Shadow`, `Glow`, `Filter`를 사용합니다. |
| `blend_mode` | `str \| BlendMode \| None` | `None` | 이전 레이어 위에 합성할 때의 혼합 모드입니다. |

고정 크기 비트맵을 확대하는 대신 요청한 크기로 SVG를 래스터화하므로 크게 렌더링해도 로고가 선명합니다.

## 예제 { #examples }

### 모서리의 로고 { #logo-in-a-corner }

```python
canvas.svg(
    path="logo.svg",
    position=("95%", "6%"),
    width=120,
    align=("right", "top"),
)
```

### 회전과 불투명도를 적용한 장식 요소 { #decorative-element-with-rotation-and-opacity }

```python
canvas.svg(
    path="assets/images/spark.svg",
    position=("70%", "20%"),
    width=44,
    align=("center", "middle"),
    rotation=20,
    opacity=0.8,
)
```

### 그림자가 있는 원격 SVG { #remote-svg-with-a-shadow }

```python
from quickthumb import Shadow

canvas.svg(
    path="https://example.com/badge.svg",
    position=("50%", "85%"),
    width=200,
    align=("center", "middle"),
    effects=[Shadow(offset_x=0, offset_y=8, color="#000000", blur_radius=16)],
)
```

## 검증 규칙 { #validation-rules }

- `path`와 `position`은 필수입니다.
- `position`은 항목 두 개의 튜플이어야 합니다. 백분율 문자열은 `-?N%` 형식이어야 합니다.
- `opacity`는 `0.0`과 `1.0` 사이여야 합니다.
- `quickthumb[svg]`를 설치하지 않고 렌더링하면 `RenderingError`가 발생합니다.
