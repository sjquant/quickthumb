---
description: 간격, 안쪽 여백, 항목 정렬과 중첩을 지원하는 quickthumb 그룹 레이어의 행·열 자동 레이아웃을 설명합니다.
---

# 그룹(자동 레이아웃) { #group-auto-layout }

`.group()`은 자식의 크기를 측정해 행이나 열로 쌓는 자동 레이아웃 컨테이너를 추가합니다.
각 자식을 직접 배치할 필요가 없습니다. 그룹은 자식의 원래 크기로 위치를 다시 계산하므로 제목이 길어지거나 배지가 추가되어도 같은 명세를 계속 사용할 수 있습니다.
이 때문에 LLM이 생성한 레이아웃에도 그룹이 적합합니다.

## 시그니처 { #signature }

```python
canvas.group(
    children,
    direction="column",
    gap=0,
    padding=0,
    position=None,
    align=None,
    item_align="start",
)
```

## 매개변수 { #parameters }

| 매개변수 | 자료형 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `children` | `list` | **필수** | 쌓을 순서의 자식 레이어. dict 또는 `text`, `image`, `shape`, `svg`, `chart`, `qr_code`, 중첩된 `group` 레이어 모델입니다. |
| `direction` | `str` | `"column"` | 주축 방향입니다. `"column"`은 위에서 아래로, `"row"`는 왼쪽에서 오른쪽으로 쌓습니다. |
| `gap` | `int` | `0` | 주축에서 인접한 자식 사이의 간격(픽셀). 0 이상이어야 합니다. |
| `padding` | `int \| tuple` | `0` | 안쪽 여백. 정수 하나, `(vertical, horizontal)` 또는 `(top, right, bottom, left)`입니다. |
| `position` | `tuple \| None` | `None` | 그룹 상자의 기준점. 픽셀이나 백분율 문자열로 지정합니다. |
| `align` | `str \| Align \| tuple \| None` | `None` | 이미지 레이어처럼 `position`이 가리키는 그룹 상자의 기준점입니다. [Align](enums.md#align)을 참고하세요. |
| `item_align` | `str` | `"start"` | 각 자식의 교차축 배치. `"start"`, `"center"`, `"end"` 중 하나입니다. |

!!! warning "자식에 `position`을 설정하지 마세요"
    그룹이 위치를 지정합니다. 자식에 `position`을 설정하면 `ValidationError`가 발생하며 자식의 `align`은 무시됩니다. 대신 그룹의 `item_align`을 사용하세요.

## 예제 { #examples }

### 세로로 쌓은 제목 블록 { #stacked-headline-block }

```python
canvas = Canvas(1280, 720).background(color="#16213E").group(
    children=[
        {"type": "shape", "shape": "pill", "width": 120, "height": 36, "color": "#E94560"},
        {"type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900},
        {"type": "text", "content": "No coordinates were harmed", "size": 40, "color": "#A2A8D3"},
    ],
    direction="column",
    gap=24,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

### 가로 배지 행 { #horizontal-badge-row }

```python
def chip(label):
    return {
        "type": "text",
        "content": label,
        "size": 24,
        "color": "#22D3EE",
        "weight": 700,
        "effects": [
            {"type": "background", "color": "#1D2547", "padding": [8, 14], "border_radius": 18},
        ],
    }

canvas.group(
    children=[chip("GROUPS"), chip("TOKENS"), chip("LINT")],
    direction="row",
    gap=14,
    position=("50%", "88%"),
    align=("center", "middle"),
)
```

### 중첩된 그룹 { #nested-groups }

그룹은 중첩할 수 있으므로 열 안에 행을 넣거나 그 반대로 구성할 수 있습니다.

```python
canvas.group(
    children=[
        {"type": "text", "content": "RELEASE 0.5", "size": 96, "color": "#FFFFFF", "weight": 900},
        {
            "type": "group",
            "direction": "row",
            "gap": 14,
            "children": [chip("GROUPS"), chip("TOKENS"), chip("LINT")],
        },
    ],
    direction="column",
    gap=28,
    position=("7%", "50%"),
    align=("left", "middle"),
)
```

### 교차축 정렬 { #cross-axis-alignment }

```python
canvas.group(
    children=[
        {"type": "text", "content": "CENTERED", "size": 80, "color": "#FFFFFF", "weight": 900},
        {"type": "text", "content": "Both children share a center line", "size": 36, "color": "#A2A8D3"},
    ],
    direction="column",
    gap=18,
    item_align="center",            # cross-axis: center each child horizontally
    position=("50%", "50%"),
    align=("center", "middle"),
)
```

## 크기 결정 방식 { #how-sizing-works }

1. 각 자식의 원래 크기(텍스트 경계, 이미지 크기, 도형의 `width`/`height`)를 측정합니다.
2. 주축을 따라 `gap`만큼 간격을 두고 자식을 차례로 배치합니다.
3. 자식들의 합집합에 `padding`을 더해 그룹 상자를 정합니다.
4. `align`에 따라 상자 전체의 기준점을 `position`에 맞춥니다.

## JSON 표현 { #json-form }

그룹도 다른 레이어와 같은 방식으로 직렬화합니다. 전체 스키마는 [JSON Schema 문서](../json-schema.md#group-layer)를 참고하세요.

```json
{
  "type": "group",
  "direction": "column",
  "gap": 24,
  "position": ["8%", "50%"],
  "align": ["left", "middle"],
  "item_align": "start",
  "children": [
    { "type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900 }
  ]
}
```

## 검증 규칙 { #validation-rules }

- `children`은 비어 있지 않은 목록이어야 합니다.
- 자식은 `position`을 설정하면 안 됩니다. 그룹이 위치를 지정합니다.
- 유효한 자식 종류는 `text`, `image`, `shape`, `svg`, `group`입니다.
- `gap`과 `padding` 값은 음수일 수 없습니다. 여백 튜플은 항목이 2개 또는 4개여야 합니다.
