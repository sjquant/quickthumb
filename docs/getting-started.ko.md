---
description: 재사용 가능한 Python 레이아웃 하나로 에피소드 카드 세 장을 렌더링하고 내용을 바꿔 나만의 카드를 만듭니다.
---

# 첫 카드 렌더링 { #render-your-first-cards }

에피소드 카드 레이아웃을 하나 만들고 세 가지 콘텐츠로 렌더링합니다.
그런 다음 제목을 바꿔 나만의 버전을 만들어 보세요.

<div class="qt-gallery" markdown>
![주황색 띠 위에 큰 숫자 12와 "Ship your first release" 제목이 있는 에피소드 12 카드](assets/home/episode-12.png)

![노란색 띠 위에 큰 숫자 13과 "Make room for better work" 제목이 있는 에피소드 13 카드](assets/home/episode-13.png)

![파란색 띠 위에 큰 숫자 14와 "Build less. Finish more." 제목이 있는 에피소드 14 카드](assets/home/episode-14.png)
</div>

## 1. quickthumb 설치 { #1-install-quickthumb }

**Python 3.11 이상**이 필요합니다. Python 환경에서 다음 명령을 실행합니다.

```bash
python -m pip install quickthumb
```

먼저 환경을 만들어야 한다면 [설치 안내](installation.md#isolated-environment)를 따른 뒤 여기로 돌아오세요.
이 예제는 기본 패키지와 내장 글꼴만 사용합니다. 설치 후 글꼴이나 사진을 내려받거나 선택 렌더러를 설치할 필요가 없습니다.

## 2. 레이아웃 저장 및 실행 { #2-save-and-run-the-layout }

quickthumb 체크아웃 밖의 작업 디렉터리에 다음 코드를 `episode_cards.py`로 저장합니다.

```python
--8<-- "examples/episode_cards.py"
```

같은 디렉터리에서 실행합니다.

```bash
python episode_cards.py
```

같은 디렉터리의 `episode-12.png`, `episode-13.png`, `episode-14.png`를 여세요.
각 이미지는 1280 × 720 크기입니다. 스크립트는 실행할 때마다 같은 파일 이름으로 기록하며, 이미 존재하는 파일을 덮어씁니다.

## 3. 다음 카드 만들기 { #3-make-the-next-card }

함수는 그대로 두고 `episodes`에 행을 하나 추가합니다.

```python
(15, "Your next big idea", "#FF4B1F"),
```

스크립트를 다시 실행하고 `episode-15.png`를 여세요.
같은 레이아웃을 재사용하면서 에피소드 번호, 제목, 색상만 바꾼 것입니다.

제목은 `max_width` 안에서 줄바꿈됩니다. `auto_scale=True`를 사용하면 지정한 너비와 높이에 맞도록 글자가 작아집니다.
여러 카드를 일괄 제작하기 전에 실제로 사용할 가장 긴 제목으로 확인하세요.

## 디자인 조정 { #adapt-the-design }

`episode_card()` 안에서 색상, 숫자나 제목 크기, 위치를 한 번 바꾸면 모든 카드에 적용됩니다.
레이어는 추가한 순서대로 그려집니다. 원하는 서체를 쓰려면 각 `.text()` 호출에 `font="/path/to/your-font.ttf"`와 같은 로컬 글꼴 경로를 추가하세요.
글꼴 자체가 충분히 굵다면 `Stroke` 효과를 제거하세요.

레이아웃을 확장할 때는 `canvas.diagnose()`로 캔버스를 벗어난 레이어나 낮은 대비 같은 일반적인 문제를 확인하세요.
이 레이아웃은 숫자를 의도적으로 잘랐으므로 `off-canvas` 항목을 하나 보고합니다.
검사 항목과 한계는 [진단](diagnostics.md)을 참고하세요. 문제가 없는 진단 결과가 디자인의 시각적 완성도를 보증하지는 않습니다.

## 다음 단계 선택 { #choose-your-next-step }

- [레시피 모음](cookbook/index.md): 썸네일, 소셜 카드, 팟캐스트 레이아웃을 응용합니다.
- [핵심 개념](concepts.md): 레이어, 효과, 배치를 이해합니다.
- [자동 레이아웃](api/group.md): 내용이 달라지는 요소를 행과 열로 배치합니다.
- [JSON과 AI 작업 흐름](json-schema.md): 레이아웃을 JSON으로 불러오고 검증합니다.
- [출력 형식 선택](output-guide.md): 이미지, 프레젠테이션, 애니메이션을 만듭니다.
- [API 레퍼런스](api/index.md): 클래스나 매개변수를 찾아봅니다.
