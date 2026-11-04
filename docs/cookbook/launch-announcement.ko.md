---
description: 테마와 자동 레이아웃 그룹을 사용한 JSON 명세에서 1280×720 출시 카드를 렌더링하고 실제 명세를 살펴봅니다.
---

# 출시 알림(자동 레이아웃) { #launch-announcement-auto-layout }

!["Layouts that build themselves."라는 문구와 오른쪽 파란 원이 있는 출시 카드](../assets/examples/launch_announcement.png)

텍스트 좌표를 일일이 지정하지 않고 만드는 출시 카드입니다. 제목은 열 그룹으로, 기능 목록은 행 그룹으로 자동 배치합니다. 색상과 글꼴 크기는 모두 `theme`에서 가져오므로 문구나 브랜드를 바꿔도 크기와 위치를 다시 측정할 필요가 없습니다.

예제를 실행하려면 [uv](https://docs.astral.sh/uv/)를 설치하고 저장소를 복제하세요.

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run --extra svg python examples/launch_announcement.py
```

스크립트는 `examples/launch_announcement.png`를 기록하며 같은 이름의 기존 파일을 덮어씁니다.

반짝임 장식은 SVG 파일이므로 `svg` 추가 기능이 필요합니다.

## 구성 방식 { #how-its-built }

- **테마 토큰.** `theme` 아래에 색상과 크기를 한 번 정의하고 `"$theme.colors.blue"`, `"$theme.sizes.title"`로 사용합니다. 값 전체가 토큰이면 JSON 자료형을 유지하므로 `"$theme.sizes.title"`은 문자열이 아닌 숫자 `116`이 됩니다.
- **텍스트용 열 그룹.** 출시 라벨, 제목, 부제는 `"direction": "column"`, `"gap": 22`인 `group` 하나의 자식입니다. 그룹만 `["7%", "44%"]`에 한 번 배치하며 자식에는 `position`이 없습니다. 부제에 줄을 추가하면 열이 그에 맞춰 재배치됩니다.
- **기능용 행 그룹.** "01 GROUPS"부터 "04 DIAGNOSTICS"는 `"direction": "row"`인 두 번째 그룹입니다. 이름을 바꿔도 간격이 균일하게 유지됩니다.
- **기본 도형으로 만든 장식.** 원, 막대 네 개, 별은 일반 `ellipse`, `rectangle`, `star` 도형입니다. 반짝임은 `assets/images/spark.svg`에 `Filter(saturation=0, brightness=3)`을 적용해 흰색으로 만듭니다.
- **렌더링 전 검사.** 스크립트는 렌더링 전에 `canvas.diagnose()`를 호출하고 진단 항목을 출력합니다. 터미널에서도 `uv run --extra cli quickthumb lint examples/launch_announcement.json`으로 같은 검사를 실행할 수 있습니다.

## 명세 { #the-spec }

```json
--8<-- "examples/launch_announcement.json"
```

## 스크립트 { #the-script }

```python
--8<-- "examples/launch_announcement.py"
```
