---
description: 화면을 채우는 인물 사진과 URL에서 불러온 웹 글꼴로 quickthumb 1280×720 팟캐스트 에피소드 홍보물을 만듭니다.
---

# 팟캐스트 홍보 { #podcast-promo }

![오른쪽에 게스트 인물 사진이 있는 "Signal to Noise" 에피소드 06 팟캐스트 홍보 카드](../assets/examples/podcast_interview_promo.png)

방송 이름과 에피소드 제목, 게스트 정보를 담은 카드입니다. 오른쪽은 게스트 사진으로 채웠습니다.

예제를 실행하려면 [uv](https://docs.astral.sh/uv/)를 설치하고 저장소를 복제하세요.

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/podcast_interview_promo.py
```

스크립트는 `examples/podcast_interview_promo.png`를 기록하며 같은 이름의 기존 파일을 덮어씁니다.

처음 실행할 때는 방송 제목의 웹 글꼴을 내려받기 위한 네트워크 연결이 필요합니다. 이후에는 캐시를 사용합니다.

## 구성 방식 { #how-its-built }

- **인물 사진이 배경입니다.** `.background(image=..., fit=FitMode.COVER)`는 캔버스 전체를 사진으로 채웁니다. 배경 제거를 하지 않으므로 다듬어야 할 잘린 가장자리도 없습니다.
- **그라디언트로 글자가 잘 보이게 합니다.** 정지점 네 개를 둔 `LinearGradient`로 텍스트 뒤는 불투명한 검정으로, 얼굴 위는 완전히 투명하게 만듭니다. 중간 정지점을 옮기면 검정색이 사라지는 위치를 조절할 수 있습니다.
- **방송 제목은 웹 글꼴을 사용합니다.** `font=SHOW_FONT_URL`은 Google Fonts의 `.ttf` 파일을 가리킵니다. URL은 이미 특정 스타일 파일이므로 `weight`, `bold`, `italic`은 적용되지 않습니다.
- **강조색은 하나입니다.** 방송 제목 아래의 짧은 빨간 선만 유채색이고 나머지는 흰색이나 회색입니다.

## 코드 { #code }

```python
--8<-- "examples/podcast_interview_promo.py"
```

같은 레이아웃에서 화면을 채우는 사진 대신 배경을 제거한 인물 사진을 쓰려면 [웹 글꼴과 배경 제거](webfonts-rembg.md)를 참고하세요.
