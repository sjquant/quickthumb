---
description: quickthumb의 SVG, HTML, PowerPoint, PDF 내보내기를 설명합니다.
---

# SVG, HTML, PowerPoint, PDF { #svg-html-powerpoint-and-pdf }

[내보내기 레퍼런스](../exports.md) · [출력 형식 선택](../output-guide.md)

## SVG { #svg }

```python
svg = canvas.to_svg()
svg = canvas.to_svg(embed_fonts=True)
```

기본 SVG는 `font-family="Roboto"`처럼 글꼴 모음 이름으로 참조합니다.
파일은 작지만 보는 컴퓨터에도 해당 글꼴이 필요합니다.
`embed_fonts=True`는 사용한 글꼴 파일을 `@font-face` 데이터 URL로 포함해 어디서든 같은 텍스트를 렌더링하게 합니다.

!!! note "뷰어 지원"
    그림자와 발광은 SVG 필터(`feGaussianBlur`)를 사용합니다. 브라우저는 충실히 렌더링하지만 간단한 SVG 래스터 변환기는 필터를 일부만 적용할 수 있습니다.

## HTML { #html }

```python
html = canvas.to_html()
canvas.render("card.html")
```

결과는 자체 포함된 HTML 파일 하나입니다.
배경, 도형, 테두리, 텍스트는 HTML과 CSS가 되고 이미지 및 CSS로 대응할 수 없는 내용은 PNG 조각으로 포함됩니다.
SVG, PDF, PPTX와 달리 레이어 `animation` 효과를 재생하며 클릭하면 진행됩니다.

디자인은 재배치되지 않는 고정 크기의 무대입니다.
기본 `responsive=True`에서는 무대 전체가 브라우저 창에 맞게 조절됩니다.
정확한 픽셀 크기를 원하면 `responsive=False`를 전달하세요.
글꼴은 기본적으로 포함되므로(`embed_fonts=True`) 다른 컴퓨터에서도 같은 모양을 유지합니다.

Deck도 같은 방식으로 발표자 화면이 있는 HTML 슬라이드쇼로 내보냅니다. [Deck](../api/deck.md)을 참고하세요.

## PPTX { #pptx }

편집 가능한 텍스트와 지원되는 도형으로 PowerPoint나 Keynote에서 다듬을 슬라이드를 만듭니다.
`pptx` 추가 기능을 설치하세요.

```bash
pip install "quickthumb[pptx]"
```

```python
from quickthumb import Canvas

canvas = Canvas(640, 360).background(color="#101826").text(
    "Ready to share", font="Arial", size=36, color="#FFFFFF", position=(60, 120)
)
canvas.export("promo.pptx")
```

슬라이드 편집기에서 `promo.pptx`를 여세요.
Canvas는 슬라이드 한 장이 되며 여러 장은 `deck.export("promo.pptx")`를 사용합니다.

!!! note "스타일이 있는 콘텐츠 편집"
    발광은 고정 이미지로 저장되고 외곽선은 별도 객체를 사용할 수 있습니다.
    스타일이 있는 텍스트나 도형을 바꾼 뒤에는 발광·테두리를 맞추기 위해 Python에서 다시 내보내세요.
    일부 효과 조합은 그림이 되므로 해당 콘텐츠를 개별 텍스트나 도형으로 편집할 수 없습니다.
    자세한 내용은 [PPTX 호환성](export-validation.md#pptx-compatibility)을 참고하세요.

!!! note "글꼴과 레이아웃"
    글꼴은 포함되지 않습니다. quickthumb와 슬라이드 편집기 양쪽에 있는 글꼴을 선택하세요.
    글꼴 대체, 크기가 섞인 서식 텍스트, 회전은 간격이나 배치를 바꿀 수 있으므로 실제 사용할 앱에서 결과를 확인하세요.

## PDF { #pdf }

PDF 내보내기에는 `pdf` 추가 기능이 필요합니다.

```bash
pip install "quickthumb[pdf]"
```

캔버스는 픽셀당 1포인트로 캔버스 크기의 PDF 한 페이지가 됩니다.
배경, 테두리, 도형, 적합한 텍스트는 래스터 렌더러와 같은 레이아웃 계산으로 네이티브 PDF 벡터 요소로 그립니다.
글꼴을 안전하게 포함할 수 있고 복잡한 문자 조형이 필요하지 않으면 부분 글꼴을 포함합니다.
지원하지 않는 텍스트는 시각적 결과를 충실히 유지하도록 픽셀이 정확히 일치하는 PNG 조각으로 포함합니다.

```python
canvas.render("promo.pdf")
# or
with open("promo.pdf", "wb") as f:
    f.write(canvas.to_pdf())
```

!!! note "충실도"
    PDF 셰이딩은 투명도를 표현할 수 없으므로 반투명 그라디언트와 반투명 정지점이 있는 그라디언트는 그림으로 포함합니다.
    흐림 효과(그림자, 발광), 도형의 외곽선, 그라디언트·이미지 글리프 채우기도 충실한 PDF 벡터 표현이 없으므로 픽셀이 정확히 일치하는 PNG 조각으로 포함합니다.
