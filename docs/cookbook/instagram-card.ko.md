---
description: quickthumb로 만든 1080×1080 Instagram 속보 카드와 실제 렌더링에 사용한 스크립트를 확인합니다.
---

# Instagram 카드 { #instagram-card }

![불꽃 사진 위에 "Wildfires Spread Across 18,000 Acres"라는 제목이 있는 정사각형 속보 카드](../assets/examples/instagram_news_card.png)

사진 위에 빨간 라벨과 세리프체 제목을 올리고 출처를 덧붙인 정사각형 뉴스 카드입니다.

예제를 실행하려면 [uv](https://docs.astral.sh/uv/)를 설치하고 저장소를 복제하세요.

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/instagram_news_card.py
```

스크립트는 `examples/instagram_news_card.png`를 기록하며 같은 이름의 기존 파일을 덮어씁니다.

## 구성 방식 { #how-its-built }

- **라벨은 `Background` 효과가 있는 텍스트입니다.** `Background(color="#CC0000", padding=(11, 22))`는 "BREAKING NEWS" 주위에 빨간 상자를 그립니다. 별도 도형의 크기를 조절할 필요 없이 텍스트와 함께 커집니다.
- **제목은 나머지와 다른 글꼴을 사용합니다.** `font="NotoSerif"`는 번들 글꼴 폴더에서 세리프 글꼴을 불러옵니다. 나머지 레이어는 기본 Roboto를 사용합니다.
- **빨간 막대는 너비 9px의 사각형입니다.** 별도 도형이므로 두 줄 제목에 맞춰 위치와 높이(176px)를 직접 정합니다.
- **출처 줄은 텍스트 레이어 하나입니다.** 두 `TextPart`가 "WORLD NEWS"와 날짜에 서로 다른 색상과 굵기를 지정합니다.
- **위치는 주로 백분율로 지정합니다.** `("8%", "92%")`처럼 쓰면 캔버스 크기에 맞춰 위치도 조절됩니다. 빨간 막대는 제목에 정확히 맞춰야 하므로 예외적으로 픽셀 좌표를 사용합니다.

## 코드 { #code }

```python
--8<-- "examples/instagram_news_card.py"
```
