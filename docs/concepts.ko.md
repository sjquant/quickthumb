---
description: 순서가 있는 레이어, 위치와 정렬, 효과, 부분별 서식, 자동 레이아웃, JSON 명세와 검증으로 quickthumb의 동작 원리를 설명합니다.
---

# 핵심 개념 { #core-concepts }

## 캔버스는 레이어 목록입니다 { #a-canvas-is-a-list-of-layers }

`Canvas`에는 크기와 순서가 있는 레이어 목록이 있습니다.
각 레이어 메서드는 레이어 하나를 추가하고 캔버스를 반환하므로 이어서 호출할 수 있습니다.

```python
from quickthumb import Canvas

canvas = (
    Canvas(1280, 720)
    .background(color="#0F172A")
    .text(content="Hello", size=64, color="#FFFFFF", align="center")
    .outline(width=8, color="#22D3EE")
)
canvas.render("hello.png")
```

레이어는 추가한 순서대로 그려집니다. 첫 레이어는 맨 뒤, 마지막 레이어는 맨 위에 놓입니다.
따라서 그림을 그리듯 배경을 먼저, 세부 요소를 마지막에 설명하면 됩니다.

## 레이어 종류 { #layer-types }

| 메서드 | 추가하는 내용 | 레퍼런스 |
| --- | --- | --- |
| `.background()` | 캔버스 전체의 색상, 그라디언트 또는 이미지 | [배경](api/background.md) |
| `.text()` | 일반 텍스트 또는 서식을 지정한 `TextPart` | [텍스트](api/text.md) |
| `.image()` | 위치를 지정한 이미지와 선택적인 배경 제거 | [이미지](api/image.md) |
| `.shape()` | 사각형, 타원, 캡슐, 삼각형, 별, 다각형 | [도형](api/shape.md) |
| `.svg()` | 아이콘이나 로고 같은 SVG 파일. `svg` 추가 기능이 필요합니다. | [SVG](api/svg.md) |
| `.video()` | 애니메이션 내보내기용 동영상 클립 | [동영상](api/video.md) |
| `.chart()`, `.qr_code()` | 막대·선 차트 또는 QR 코드 | [데이터 시각화](api/data-visualizations.md) |
| `.counter()` | 한 값에서 다른 값으로 세는 숫자 | [Canvas](api/canvas.md#animated-counters) |
| `.group()` | 자식을 자동으로 배치하는 행이나 열 | [그룹](api/group.md) |
| `.outline()` | 캔버스 가장자리의 테두리 | [테두리](api/outline.md) |
| `.custom(fn)` | Pillow 이미지에 직접 그리는 함수 | [Canvas](api/canvas.md) |

## 위치와 정렬 { #position-and-alignment }

`position`은 `(x, y)` 쌍입니다. 각 값은 픽셀이나 캔버스의 백분율이며 섞어 쓸 수 있습니다.

```python
canvas.shape(shape="rectangle", position=(64, 64), width=200, height=80, color="#CC0000")
canvas.text(content="Hello", size=72, color="#FFFFFF", position=("8%", 360))
```

`align`은 해당 위치에 놓을 레이어의 기준점을 정합니다. 기본값은 왼쪽 위입니다.
`align=("center", "middle")`은 레이어 중앙을 그 위치에 놓습니다.
1280×720 캔버스에서 `align=("right", "bottom")`과 `position=(1280, 720)`을 쓰면 레이어 크기와 무관하게 오른쪽 아래에 고정합니다.

`align`은 같은 의미의 여러 표기법을 받습니다.

```python
align=("center", "middle")      # (horizontal, vertical)
align="center"                  # same as ("center", "middle")
align="bottom-right"
align=Align.BOTTOM_RIGHT
```

가로 값은 `left`, `center`, `right`, 세로 값은 `top`, `middle`, `bottom`입니다.
텍스트 레이어에 `position` 없이 `align`만 있으면 캔버스에서 해당 정렬로 배치하므로 `align="center"`는 중앙에 놓습니다.

## 효과 { #effects }

효과는 레이어 하나를 그리는 방식을 바꿉니다. 목록으로 전달하세요.

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

모든 효과가 모든 레이어에 적합한 것은 아닙니다.

| 레이어 | 효과 |
| --- | --- |
| 배경 | `Filter`, `Grain` |
| 텍스트 | `Stroke`, `Shadow`, `Glow`, `Background`(텍스트 뒤의 상자) |
| 도형 | `Stroke`, `Shadow`, `Glow`, `InnerShadow`, `BackdropBlur` |
| 이미지, SVG, 동영상 | `Stroke`, `Shadow`, `Glow`, `Filter`, `Grain`, `Duotone`, `InnerShadow`, `BackdropBlur` |

레이어가 지원하지 않는 효과를 전달하면 `ValidationError`가 발생합니다.
전체 매개변수는 [효과 레퍼런스](api/effects.md)에 있습니다.

## 부분별 텍스트 서식 { #rich-text }

텍스트의 모양이 모두 같으면 일반 문자열이면 충분합니다.
일부 구간을 다르게 꾸미려면 `TextPart` 목록을 전달하세요.

```python
from quickthumb import TextPart

canvas.text(
    content=[
        TextPart(text="5 ", color="#FBBF24"),
        TextPart(text="WAYS TO WIN", color="#FFFFFF"),
    ],
    size=80,
    weight=900,
    position=("8%", "55%"),
    align=("left", "middle"),
)
```

레이어의 설정(여기서는 `size`, `weight`)은 각 구간이 자체 값을 지정하지 않는 한 전체에 적용됩니다.
구간은 `color`, `size`, `font`, `weight`, `bold`, `italic`, `letter_spacing`, `line_height`, `effects`를 덮어쓸 수 있습니다.

## 그라디언트, 혼합 모드와 크기 맞춤 { #gradients-blend-modes-and-fit }

배경에는 색상이나 이미지뿐 아니라 `gradient`도 전달할 수 있습니다.

```python
from quickthumb import LinearGradient, RadialGradient

canvas.background(gradient=LinearGradient(angle=135, stops=[("#FF5733", 0.0), ("#3333FF", 1.0)]))
canvas.background(gradient=RadialGradient(center=(0.5, 0.5), stops=[("#FF5733", 0.0), ("#3333FF", 1.0)]))
```

정지점의 색상에 알파(`"#00000080"`)를 포함하면 텍스트 뒤 사진의 일부를 어둡게 할 수 있습니다.

배경이나 이미지 레이어의 `blend_mode`는 아래 내용과 합치는 방식을 정합니다.
`normal`, `multiply`, `screen`, `overlay`, `darken`, `lighten`을 사용할 수 있습니다.

`fit`은 이미지로 상자를 채우는 방식을 정합니다.
배경 기본값인 `cover`는 채우고 넘치는 부분을 자르며, `contain`은 전체 이미지를 안에 맞추고, `fill`은 늘립니다.

## 자동 레이아웃 { #auto-layout }

직접 위치를 정한 텍스트는 문구가 길어지면 깨질 수 있습니다.
`group`은 자식을 측정하고 행이나 열로 쌓습니다. 그룹만 한 번 배치하면 자식은 그룹이 배치합니다.

```python
canvas.group(
    children=[
        {"type": "shape", "shape": "pill", "width": 120, "height": 36, "color": "#E94560"},
        {"type": "text", "content": "AUTO LAYOUT", "size": 96, "color": "#FFFFFF", "weight": 900},
        {"type": "text", "content": "Longer copy pushes the rest down", "size": 40, "color": "#A2A8D3"},
    ],
    direction="column",
    gap=24,
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

자식은 `position`을 설정하지 않으며 그룹 안에 그룹을 넣을 수도 있습니다.
[그룹](api/group.md)을 참고하세요.

## JSON 명세 { #json-specs }

위의 모든 내용은 Python 대신 JSON으로 쓸 수 있고 캔버스를 양방향으로 변환할 수 있습니다.

```python
spec = canvas.to_json()
same_canvas = Canvas.from_json(spec)
```

Python 함수는 JSON에 저장할 수 없으므로 `.custom(fn)`만 예외입니다.

JSON 명세는 `theme` 블록에 색상과 크기를 한 번 정의하고 `$theme.<path>`로 참조할 수도 있습니다.

```json
{
  "kind": "canvas",
  "width": 1280,
  "height": 720,
  "theme": { "colors": { "primary": "#B8FF00" }, "sizes": { "title": 96 } },
  "layers": [
    { "type": "text", "content": "Hello", "size": "$theme.sizes.title", "color": "$theme.colors.primary" }
  ]
}
```

[JSON Schema와 AI 작업 흐름](json-schema.md)을 참고하세요.

## 경로 모션 { #path-motion }

`Canvas.path()`는 SVG 경로 데이터, 그라디언트를 포함한 채우기, 점선을 지원합니다.
고정된 `width`/`height` 뷰포트는 로컬 그림을 자르고 회전·크기 조절 중에도 정규화된 `anchor`를 정의합니다.

```python
from quickthumb import AnimationSpec, Canvas, KeyframeSpec, ScaleTrack, TimingSpec

canvas = Canvas(320, 240).path(
    "M2 20C2 2 38 2 38 20C38 38 2 38 2 20Z", (100, 80), 40, 40,
    "#38B6A080", anchor=(0.5, 0.5),
    animation=AnimationSpec.timeline(
        ScaleTrack(keyframes=[KeyframeSpec(time=0, value=1), KeyframeSpec(time=1, value=4)]),
        timing=TimingSpec(duration=1), easing="linear",
    ),
)
frame = canvas.render_frame(0.75)
```

경로 애니메이션에는 트랙 타임라인을 사용하세요.
지원 범위는 출력 형식에 따라 다르며 경로에는 프리셋, stagger, Group 자식, 부모 변환을 지원하지 않습니다.
애니메이션과 내보내기 상세는 [Path API](api/path.md)를 참고하세요.

## 오류와 검사 { #errors-and-checks }

아무것도 그리기 전에 레이어를 추가할 때 인수를 검증합니다.

```python
from quickthumb import ValidationError

try:
    canvas.text(content="Hello", size=64, color="#FFF")
except ValidationError as error:
    print(error)  # /color: invalid hex color: #FFF
```

다운로드 실패처럼 그리는 중에만 드러나는 문제는 `RenderingError`, 존재하지 않는 로컬 파일은 `MissingAssetError`를 발생시킵니다.
모든 오류는 구조화된 `details`를 포함합니다. [구조화된 오류](errors.md)를 참고하세요.

캔버스가 유효해도 시각적으로 잘못 보일 수 있습니다.
`canvas.diagnose()`는 파일을 렌더링하지 않고 너무 작거나 캔버스를 벗어난 텍스트, 낮은 대비, 다른 레이어에 가린 레이어 같은 문제를 찾습니다.
[진단과 CLI](diagnostics.md)를 참고하세요.
