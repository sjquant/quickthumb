---
description: 사용할 출력 형식을 선택하고 quickthumb로 첫 이미지, 프레젠테이션 또는 애니메이션을 내보냅니다.
---

# 출력 형식 선택 { #choose-an-output-format }

Canvas나 Deck 하나로 이미지, 프레젠테이션, 애니메이션을 모두 만들 수 있습니다. 결과물을 어디에 사용할지에 따라 출력 형식을 고르세요.

| 원하는 작업 | 선택할 형식 | 필요한 도구 |
| --- | --- | --- |
| 이미지 게시 | PNG, JPEG 또는 WebP | 기본 패키지 |
| 브라우저에서 프레젠테이션 공유 | HTML | 기본 패키지 |
| PowerPoint나 Keynote에서 슬라이드 편집 | [PPTX](reference/export-documents.md#pptx) | `pptx` 추가 기능 |
| 문서 공유 | PDF | `pdf` 추가 기능 |
| 짧은 애니메이션 공유 | GIF | 기본 패키지 |
| 동영상 게시 | MP4, WebM 또는 MOV | FFmpeg. MOV에는 `prores_ks` 인코더도 필요합니다. |
| 벡터 아트워크 사용 | SVG 또는 Lottie | SVG는 기본 패키지를 사용합니다. Lottie는 Canvas 전용의 제한된 기능만 지원합니다. |

## 이미지 내보내기 { #export-an-image }

파일 확장자로 형식이 결정됩니다. 이 예제에는 Python 3.11 이상과 `pip install quickthumb`가 필요합니다.

```python
from quickthumb import Canvas

canvas = Canvas(1280, 720).background(color="#155BD7").text(
    "Make an idea visible.", size=72, color="#FFFFFF", position=(80, 300)
)
result = canvas.export("image.png")
print(result.written_paths)
```

작업 디렉터리에서 `image.png`를 여세요. 다시 내보내면 파일을 덮어씁니다.
JPEG와 WebP는 각각 `.jpg`, `.webp`를 사용합니다. Deck을 이미지 형식으로 내보내면 번호가 붙은 슬라이드 파일이 생성됩니다.
파일 이름은 `written_paths`로 확인할 수 있습니다.

## 슬라이드 또는 애니메이션 만들기 { #make-slides-or-animation }

[프레젠테이션과 동영상 예제](cookbook/decks-and-video.md)에서 실행 가능한 이미지, 두 장짜리 HTML 프레젠테이션, GIF 예제를 확인하세요.
PowerPoint나 PDF를 사용하려면 먼저 해당 [선택 의존성](installation.md#optional-extras)을 설치합니다.
MP4와 WebM에는 별도로 설치한 FFmpeg가 필요합니다.

형식에 따라 효과와 애니메이션이 다르게 표현됩니다. PowerPoint와 PDF에서는 일부 콘텐츠가 이미지로 바뀔 수 있고, HTML 프레젠테이션에서는 Deck 내레이션이 재생되지 않습니다. 실제로 사용할 앱에서 결과를 확인하세요.

지원 형식, 내보내기 결과, 고급 옵션과 대체 표현은 [내보내기 레퍼런스](exports.md)를 참고하세요.
