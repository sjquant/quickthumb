---
description: quickthumb에서 Google Fonts나 URL의 글꼴을 불러오고 remove_background로 사진의 피사체를 분리합니다.
---

# 웹 글꼴과 배경 제거 { #webfonts-background-removal }

## 글꼴 { #fonts }

텍스트 레이어의 `font`는 글꼴 모음 이름이나 URL일 수 있습니다.
컴퓨터에 설치되지 않은 글꼴도 다음 세 가지 방법으로 사용할 수 있습니다.

### 이름으로 Google Font 선택 { #a-google-font-by-name }

`font_source="google"`로 설정하세요.
quickthumb는 처음에 글꼴 모음을 내려받아 캐시하고 `weight`, `italic`에 맞는 파일을 선택합니다.

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720).background(color="#0A1730").text(
    content="Hello from Inter",
    font="Inter",
    font_source="google",
    weight=800,
    size=96,
    color="#FFFFFF",
    position=("50%", "50%"),
    align="center",
)
canvas.render("inter.png")
```

Google Fonts 글꼴 모음을 이름으로 선택할 때 이 옵션을 사용하세요.

### URL로 글꼴 파일 선택 { #a-font-file-by-url }

`.ttf`, `.otf`, `.woff`, `.woff2` 파일 URL을 전달합니다. 한 번 내려받아 캐시합니다.

```python
SHOW_FONT_URL = "https://fonts.gstatic.com/s/dmserifdisplay/v17/-nFnOHM81r4j6k0gjAW3mujVU2B2K_c.ttf"

canvas.text(content="Signal to Noise", font=SHOW_FONT_URL, size=50, color="#F5F5F7")
```

URL은 특정 파일 하나를 가리키므로 `weight`, `bold`, `italic`은 무시됩니다.
일반·굵은 스타일을 쓰려면 두 URL을 사용하세요. 예를 들어 `TextPart`마다 하나씩 지정할 수 있습니다.
[팟캐스트 홍보](podcast-promo.md) 레시피는 이 방식으로 방송 제목을 불러옵니다.

### 로컬 글꼴 폴더 { #a-local-font-folder }

`QUICKTHUMB_FONT_DIR`에 글꼴 파일 폴더를 지정하고 글꼴 모음 이름을 사용합니다.
`QUICKTHUMB_DEFAULT_FONT`는 레이어에 `font`가 없을 때의 글꼴을 정합니다.

```python
import os

os.environ["QUICKTHUMB_FONT_DIR"] = "assets/fonts"
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

canvas.text(content="Hello", font="NotoSerif", weight=700, size=64, color="#FFFFFF")
```

모든 레시피 예제는 저장소의 `assets/fonts` 폴더에 포함된 글꼴을 이 방식으로 사용합니다.

## 배경 제거 { #background-removal }

이미지 레이어의 `remove_background=True`는 사진에서 피사체를 분리하고 나머지를 제거합니다.

```python
from quickthumb import Canvas, Shadow

canvas = (
    Canvas(1280, 720)
    .background(color="#1C1C1E")
    .image(
        path="portrait.jpg",
        position=(1280, 720),
        width=620,
        height=710,
        fit="cover",
        align=("right", "bottom"),
        remove_background=True,
        effects=[Shadow(offset_x=-12, offset_y=12, color="#00000099", blur_radius=26)],
    )
)
```

`path`에는 `http(s)` URL도 사용할 수 있습니다.

Python 3.11 이상이 필요한 `rembg` 추가 기능을 설치해야 합니다.

```bash
pip install "quickthumb[rembg]"
```

첫 호출은 분할 모델(약 170 MB)을 내려받아 캐시합니다.

알아 둘 사항은 다음과 같습니다.

- **배경 제거가 먼저입니다.** 배경을 제거한 뒤 이미지 크기를 조절하고 마지막으로 `effects`를 적용합니다. 따라서 `Shadow`는 원래 사진의 사각 테두리가 아니라 인물의 윤곽을 따릅니다. `Filter`는 잘라낸 이미지의 색상만 바꾸며, 배경을 제거하는 방식에는 영향을 주지 않습니다.
- **인물에 가장 적합합니다.** 모델은 주로 인물 사진으로 학습했습니다. 배경과 뚜렷이 구분되는 피사체가 가장 깔끔한 가장자리를 만듭니다.
- **피사체를 가장자리에 고정하세요.** [발표자 사진](youtube-thumbnail.md#talking-head)과 [반응](youtube-thumbnail.md#reaction) 썸네일처럼 `position=(1280, 720)`과 `align=("right", "bottom")`을 사용하면 크기와 관계없이 인물을 모서리에 유지합니다.
