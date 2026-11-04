---
description: quickthumb로 만든 1280×720 YouTube 썸네일 다섯 가지와 각 이미지를 실제로 렌더링한 스크립트를 확인합니다.
---

# YouTube 썸네일 { #youtube-thumbnails }

1280×720 YouTube 썸네일 레이아웃 다섯 가지를 소개합니다. 각 이미지 바로 아래에 실제 렌더링에 사용한 스크립트가 있으며, 저장소의 `examples/` 폴더에서도 찾을 수 있습니다.

실행하려면 [uv](https://docs.astral.sh/uv/)를 설치하고 저장소를 복제한 뒤 루트에서 스크립트를 실행하세요.
스크립트는 `assets/`에서 에셋을 불러와 `examples/`에 PNG를 기록하며 같은 이름의 기존 파일을 덮어씁니다.

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/youtube_thumbnail_01.py
```

## 전후 비교 카드 { #before-after }

!["Better thumbnails. Faster."라는 제목과 기울어진 전후 비교 카드 두 장이 있는 썸네일](../assets/examples/youtube_thumbnail_01.png)

사진을 배경으로 깔고 왼쪽에 제목, 오른쪽에 기울어진 카드 두 장을 배치했습니다. 전후 비교를 통해 어떤 변화를 얻을 수 있는지 바로 보여 줍니다.

- 가로 `LinearGradient`가 거의 검정인 색에서 투명으로 이어집니다. 왼쪽은 텍스트를 읽기 충분히 어둡게 유지하고 오른쪽은 사진을 보여 줍니다.
- 세 줄 제목은 각자 크기와 색상이 있는 `TextPart`로 구성한 `.text()` 레이어 하나입니다.
- 카드는 `Stroke`가 있는 회전한 `rectangle` 도형이며 앞쪽 카드에는 `Shadow`도 있습니다. 카드의 텍스트도 같은 `rotation`을 사용합니다.

??? example "examples/youtube_thumbnail_01.py"

    ```python
    --8<-- "examples/youtube_thumbnail_01.py"
    ```

## 강렬한 질문 { #burnout }

![채도를 낮춘 사진 위에 "Are you burning out?"라고 적힌 썸네일](../assets/examples/youtube_thumbnail_02.png)

대부분의 색상을 제거한 사진 위에 질문 하나를 아주 크게 배치합니다.

- `Filter(saturation=0.32)`로 사진의 색을 낮춰 주황색 강조만 강하게 남깁니다.
- 제목의 각 줄은 고정 픽셀 위치의 개별 텍스트 레이어이므로 줄 사이 간격을 정확히 제어할 수 있습니다.
- 문구 위의 가는 선은 `#FFFFFF33`, 즉 불투명도 20%인 흰색의 1px 사각형입니다.

??? example "examples/youtube_thumbnail_02.py"

    ```python
    --8<-- "examples/youtube_thumbnail_02.py"
    ```

## 발표자 인물 사진 { #talking-head }

![파란 패널의 배경을 제거한 인물 사진 옆에 "AI tools. What actually works."라고 적힌 썸네일](../assets/examples/youtube_talking_head.png)

왼쪽에는 제목, 오른쪽에는 발표자를 배치합니다.

- URL에서 인물 사진을 가져와 `remove_background=True`로 배경을 제거합니다. Python 3.11 이상의 `rembg` 추가 기능과 네트워크 연결이 필요합니다. `uv run --extra rembg python examples/youtube_talking_head.py`로 실행하세요.
- `position=(1280, 720)`과 `align=("right", "bottom")`은 사진 크기와 무관하게 인물을 오른쪽 아래에 고정합니다.
- `max_width="55%"`는 제목이 인물에 닿기 전에 줄바꿈합니다.

??? example "examples/youtube_talking_head.py"

    ```python
    --8<-- "examples/youtube_talking_head.py"
    ```

## 반응 { #reaction }

![놀란 표정의 배경을 제거한 인물과 "Viral, 12.4M views"라는 문구가 있는 썸네일](../assets/examples/youtube_reaction.png)

큰 단어, 큰 숫자, 반응하는 얼굴로 구성합니다.

- 인물 뒤에 중심을 둔 `RadialGradient`가 은은한 빨간 발광을 더합니다. 위에 놓은 `LinearGradient`는 텍스트 쪽을 어둡게 유지합니다.
- 전체 뒤의 `#1`은 불투명도 13%의 470px 텍스트 레이어입니다.
- 인물은 `rembg` 추가 기능이 필요한 `remove_background=True`와 `Filter(saturation=0.08)`을 사용해 거의 흑백으로 보입니다.

??? example "examples/youtube_reaction.py"

    ```python
    --8<-- "examples/youtube_reaction.py"
    ```

## 튜토리얼 { #tutorial }

![짧은 코드가 있는 파란 패널 옆에 "Master Python."이라고 적힌 썸네일](../assets/examples/youtube_tutorial_explainer.png)

사진 없이 제목, 파란 패널, 몇 줄의 "코드"로 구성합니다.

- 패널의 코드는 텍스트 레이어 하나입니다. 각 `TextPart`에 색상과 굵기를 지정하는 것만으로 문법 강조처럼 보이게 합니다.
- 색상은 모듈 수준 상수(`BLUE`, `WHITE`, `GRAY`)이므로 세 줄만 고치면 썸네일 스타일을 바꿀 수 있습니다.

??? example "examples/youtube_tutorial_explainer.py"

    ```python
    --8<-- "examples/youtube_tutorial_explainer.py"
    ```
