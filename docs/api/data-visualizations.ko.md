---
description: 결정적인 막대 차트, 선 차트와 QR 코드 레이어를 설명합니다.
---

# 데이터 시각화 { #data-visualizations }

quickthumb는 대시보드, 카드, 소셜 그래픽 생성에 쓸 수 있는 작고 결정적인 차트 레이어와 QR 코드 레이어를 제공합니다.
막대 차트와 선 차트는 `ChartData`를 공유하며 각 차트에는 용도에 맞는 스타일 모델이 있습니다.
범용 플로팅 시스템을 목적으로 하지는 않습니다.

```python
from quickthumb import (
    BarChartSpec,
    BarChartStyle,
    Canvas,
    LineChartSpec,
    LineChartStyle,
)

canvas = (
    Canvas(800, 400)
    .chart(
        spec=BarChartSpec(
            data=[-4, 8, 12, 6],
            style=BarChartStyle(color="#2563EB", negative_color="#DC2626"),
        ),
        position=(40, 40),
        width=220,
        height=120,
    )
    .chart(
        spec=LineChartSpec(
            data=[2, 5, 3, 7],
            style=LineChartStyle(color="#7C3AED", fill="#DDD6FE"),
        ),
        position=(40, 200),
        width=440,
        height=120,
    )
    .qr_code("https://example.com", position=(620, 40), size=140)
)
```

## 공통 차트 데이터와 스타일 { #shared-chart-data-and-style }

생성된 명세에 이름 있는 데이터 객체가 필요할 때 `ChartData(values=[...])`가 유용합니다.
빌더와 JSON은 일반 숫자 목록도 받습니다. 빈 계열, 상수 계열, 음수 계열도 유효합니다.
값은 유한한 숫자여야 하므로 `NaN`, 무한대, 숫자가 아닌 값을 넣으면 `ValidationError`가 발생합니다.

`BarChartStyle`은 `color`, `padding`, `opacity`, `negative_color`, `bar_gap`을 받습니다.
`LineChartStyle`은 `color`, `padding`, `opacity`, `fill`, `fill_opacity`, `stroke_width`, `point_radius`, `show_points`를 받습니다.
선택한 차트 종류에 의미가 없는 옵션을 전달하면 조용히 무시하는 대신 `ValidationError`가 발생합니다.
선택한 명세는 하나의 `.chart()` 빌더에 전달합니다.

선 차트 값은 플롯 상자에 맞게 조정됩니다. 상수 계열은 세로 중앙에 놓입니다.
막대 차트의 범위에는 항상 0이 포함되므로 양수와 음수는 기준선의 서로 반대쪽에 그려집니다.
빈 계열은 아무 픽셀도 그리지 않습니다.

## 레이어 빌더 { #layer-builders }

| 빌더 | JSON 종류 | 용도 |
| --- | --- | --- |
| `.chart(spec, position, width, height)` | `chart` / `bar` | `BarChartSpec`을 전달하면 0을 반영한 기준선의 세로 막대를 그립니다. |
| `.chart(spec, position, width, height)` | `chart` / `line` | `LineChartSpec`을 전달하면 기본적으로 점 표시가 있는 선 차트를 그립니다. |
| `.qr_code(data, position, size)` | `qr_code` | 오류 정정 수준과 여백을 명시한 정사각형 QR 코드를 그립니다. |

JSON의 차트 레이어는 `"spec"` 아래에 종류를 구분할 수 있는 차트 명세를 저장합니다.
예를 들어 `{ "type": "bar", "data": [1, -2] }`처럼 표현합니다.

차트 빌더는 픽셀 또는 백분율 위치, `align`, `opacity`, 기존 `clip`과 `mask` 합성 기본 요소를 받습니다.
그룹의 자식으로 사용할 수도 있으며 그룹이 위치를 자동으로 지정합니다.
QR 코드는 `foreground`, `background`, `error_correction`(`L`, `M`, `Q`, `H`), `quiet_zone`을 받습니다.
요청한 정사각형 크기가 생성된 QR 모듈 행렬을 보존하기에 너무 작으면 `RenderingError`가 발생합니다.
차트와 QR 레이어는 PPTX와 GIF/동영상 내보내기에 기존 레이어 수준의 `animation` 계약도 적용합니다.
생략하면 결정적인 정적 동작을 유지합니다.

차트와 QR 레이어는 `Canvas.to_json()`으로 직렬화하고 `Canvas.from_json()`으로 검증하며 `quickthumb schema`에 포함됩니다.
SVG, HTML, PDF, PPTX 내보내기는 표준 픽셀 단위 일치 래스터 대체 표현으로 이를 보존합니다.
