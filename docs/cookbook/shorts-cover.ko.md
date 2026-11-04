---
description: quickthumb로 JSON 명세에서 렌더링한 1080×1920 Shorts 커버와 실제 생성에 사용한 명세를 확인합니다.
---

# Shorts / 세로형 커버 { #shorts-vertical-cover }

![잘린 사진을 보여 주는 기울어진 휴대전화와 "Turn long videos into Shorts"라는 문구가 있는 세로형 커버](../assets/examples/shorts_cover_agent.png)

디자인 전체가 JSON 파일인 1080×1920 커버입니다.
Python은 파일을 불러와 렌더링만 합니다. LLM이나 템플릿 시스템이 레이아웃을 작성할 때 quickthumb를 사용하는 방식입니다.

예제를 실행하려면 [uv](https://docs.astral.sh/uv/)를 설치하고 저장소를 복제하세요.

```bash
git clone https://github.com/sjquant/quickthumb
cd quickthumb
uv run python examples/shorts_cover_agent.py
```

스크립트는 `examples/shorts_cover_agent.png`를 기록하며 같은 이름의 기존 파일을 덮어씁니다.

## 구성 방식 { #how-its-built }

- **사진 하나를 두 번 사용합니다.** 같은 사진을 가로 16:9로 잘라 표시하고 휴대전화 안에도 표시합니다. `"fit": "cover"`가 각 프레임의 모양에 맞춰 자릅니다.
- **휴대전화는 두 레이어입니다.** 어둡고 둥근 사각형이 본체이고 위의 사진이 화면입니다. 두 레이어와 화면의 라벨 세 개가 모두 `"rotation": 3`을 사용하므로 함께 기울어집니다.
- **경로는 저장소 루트를 기준으로 합니다.** 예를 들어 `assets/images/denise-jans-WIRvXd1PYlg-unsplash.jpg`입니다. 렌더링 전에 스크립트가 저장소 루트로 이동하므로 어느 디렉터리에서도 실행할 수 있습니다.
- **배경에 약간의 입자를 더했습니다.** 고정 `seed`가 있는 `grain` 효과로 렌더링할 때마다 같은 질감을 만듭니다.

## 명세 { #the-spec }

```json
--8<-- "examples/shorts_cover_agent.json"
```

## 스크립트 { #the-script }

```python
--8<-- "examples/shorts_cover_agent.py"
```

`Canvas.from_json()`은 그리기 전에 명세를 검증하므로 형식이 잘못되면 해당 필드를 가리키는 `ValidationError`가 발생합니다.
사용 가능한 전체 필드는 [JSON Schema와 AI 작업 흐름](../json-schema.md)을 참고하세요.
