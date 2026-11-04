---
description: 너비, 색상, 불투명도, 모서리 반경을 지정해 캔버스 테두리를 그리는 quickthumb 테두리 레이어를 설명합니다.
---

# 테두리 { #outline }

`.outline()`은 캔버스 전체 가장자리에 테두리를 그립니다. 보통 모든 콘텐츠 위에 표시되도록 마지막 레이어로 추가합니다.

## 시그니처 { #signature }

```python
canvas.outline(
    width,
    color,
    offset=0,
    opacity=1.0,
)
```

## 매개변수 { #parameters }

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `width` | `int` | **필수** | 테두리 두께(픽셀). 양의 정수입니다. |
| `color` | `str` | **필수** | 테두리 색상. 16진수 문자열(`"#RRGGBB"` 또는 `"#RRGGBBAA"`)입니다. |
| `offset` | `int` | `0` | 캔버스 가장자리에서 안쪽으로 들어오는 거리(픽셀). 0 이상의 정수입니다. |
| `opacity` | `float` | `1.0` | `0.0`부터 `1.0`까지의 레이어 불투명도입니다. |

## 예제 { #examples }

### 기본 테두리 { #basic-outline }

```python
canvas.outline(width=12, color="#B8FF00")
```

### 안쪽 테두리 { #inset-outline }

```python
# Drawn 8px inside the canvas edge
canvas.outline(width=4, color="#FFFFFF", offset=8)
```

### 반투명 테두리 { #semi-transparent-outline }

```python
canvas.outline(width=8, color="#FFFFFF", opacity=0.5)
```

### 전체 구성에서의 일반적인 사용법 { #typical-usage-in-a-full-composition }

```python
canvas = (
    Canvas(1280, 720)
    .background(color="#0F172A")
    .text(content="TITLE", size=96, color="#FFFFFF", align="center")
    .outline(width=12, color="#22d3ee")  # always last
)
```

## 참고 { #notes }

- 기본값인 `offset=0`에서는 캔버스 가장자리에서 안쪽으로 테두리를 그립니다.
- 큰 `offset`과 얇은 `width`를 조합하면 떠 있는 액자 같은 효과를 만들 수 있습니다.
- `opacity`는 `0.0`과 `1.0` 사이여야 합니다.
