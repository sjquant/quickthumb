---
description: quickthumb 설치, 텍스트, 글꼴, 이미지, 출력 형식, JSON 명세와 오류에 관해 자주 묻는 질문에 답합니다.
---

# 자주 묻는 질문 { #faq }

## 설치 { #installation }

### 어떤 Python 버전을 지원하나요? { #which-python-versions-are-supported }

Python 3.11 이상을 지원합니다. 패키지는 3.11과 3.12용으로 분류되어 있으며 CI는 3.11에서 실행됩니다.
배경 제거 기능인 `rembg` 추가 기능에도 동일하게 적용됩니다.

### `quickthumb` 명령을 찾을 수 없어요 { #the-quickthumb-command-isnt-found }

명령줄 도구는 선택 기능입니다. `pip install "quickthumb[cli]"`로 설치하세요.
전체 추가 기능 목록은 [설치 안내](installation.md)에 있습니다.

### SVG 레이어에서 왜 `RenderingError`가 발생하나요? { #why-does-my-svg-layer-raise-renderingerror }

SVG 파일을 그리려면 `svg` 추가 기능이 필요합니다. `pip install "quickthumb[svg]"`로 설치하세요.
캔버스를 SVG로 *내보낼 때*는 필요하지 않습니다.

## 캔버스와 레이어 { #canvas-and-layers }

### 레이어가 없는 캔버스를 렌더링하면 어떻게 되나요? { #what-happens-if-i-render-a-canvas-with-no-layers }

캔버스 크기의 완전히 투명한 이미지가 만들어집니다. 오류가 아닙니다.

### 그룹 자식에서 왜 "group children must not set position" 오류가 발생하나요? { #why-does-a-group-child-raise-group-children-must-not-set-position }

그룹이 자식의 위치를 직접 정하기 때문입니다. 자식의 `position`을 제거하고 대신 그룹을 배치하세요.

```python
canvas.group(
    children=[{"type": "text", "content": "TITLE", "size": 96, "color": "#FFFFFF"}],
    position=("8%", "50%"),
    align=("left", "middle"),
)
```

자식의 `align`도 무시됩니다. 그룹의 교차축 방향으로 자식을 정렬하려면 그룹의 `item_align`을 사용하세요.

### 렌더링 전에 디자인의 문제를 확인하려면 어떻게 하나요? { #how-do-i-check-a-design-for-problems-before-rendering }

`canvas.diagnose()`를 호출하거나 JSON 명세에 `quickthumb lint spec.json`을 실행하세요.
너무 작거나 캔버스를 벗어난 텍스트, 낮은 대비, 숨겨진 레이어 등의 문제를 보고합니다.
[진단과 CLI](diagnostics.md)를 참고하세요.

## 텍스트와 글꼴 { #text-and-fonts }

### 텍스트가 캔버스를 벗어나요 { #my-text-runs-off-the-canvas }

줄바꿈되도록 `max_width`를 설정하세요.

```python
canvas.text(content="A longer title that needs two lines", size=72, color="#FFFFFF", max_width="60%")
```

텍스트가 들어갈 때까지 크기를 줄이려면 `max_width`, `max_height` 또는 둘 다와 함께 `auto_scale=True`를 추가하세요.

### `bold=True`와 `weight=900`을 설정했더니 오류가 나요 { #i-set-boldtrue-and-weight900-and-got-an-error }

둘은 같은 속성을 설정하므로 하나만 사용하세요. `weight`로 더 정확하게 지정할 수 있습니다.
`TextPart(text="STRONG", weight=900)`처럼 사용합니다.

### Google Font를 사용하려면 어떻게 하나요? { #how-do-i-use-a-google-font }

글꼴 이름을 지정하고 `font_source="google"`로 설정하세요.
한 번 내려받아 캐시하며, `weight`에 맞는 파일을 선택합니다.

```python
canvas.text(content="Hello", font="Inter", font_source="google", weight=800, size=72, color="#FFFFFF")
```

글꼴 파일의 URL을 전달하거나 `QUICKTHUMB_FONT_DIR`에 글꼴 폴더를 지정할 수도 있습니다.
[웹 글꼴과 배경 제거](cookbook/webfonts-rembg.md)를 참고하세요.

## 이미지 { #images }

### URL의 이미지를 사용할 수 있나요? { #can-i-use-images-from-a-url }

네. `background(image=...)`와 `image(path=...)`는 `http(s)` URL을 받습니다.
렌더링 중에 내려받고 캐시합니다. 캐시 설정은 [원격 에셋과 캐시](reference/export-assets.md#remote-assets-and-caching)를 참고하세요.

### 인물 뒤의 배경을 제거하려면 어떻게 하나요? { #how-do-i-remove-the-background-behind-a-person }

이미지 레이어에 `remove_background=True`를 설정하세요. `rembg` 추가 기능이 필요합니다.

```python
canvas.image(path="portrait.jpg", position=("75%", "55%"), width=420, height=520, remove_background=True)
```

### `cover`, `contain`, `fill`의 차이는 무엇인가요? { #whats-the-difference-between-cover-contain-and-fill }

`cover`는 상자를 채우고 넘치는 부분을 자릅니다.
`contain`은 이미지 전체가 상자 안에 들어오도록 맞추고 남는 공간을 비웁니다.
`fill`은 비율을 무시하고 이미지를 상자 크기로 늘립니다.

## 출력 { #output }

### 어떤 형식으로 내보낼 수 있나요? { #which-formats-can-i-export }

`render()`에 전달한 파일 확장자로 형식이 결정됩니다.

| 종류 | 형식 | 필요한 도구 |
| --- | --- | --- |
| 이미지 | PNG, JPEG, WebP | |
| 벡터와 문서 | SVG, PDF, PPTX | PDF와 PPTX에는 각각 `pdf`, `pptx` 추가 기능 |
| 웹 | HTML | |
| 애니메이션 | GIF, MP4, WebM | MP4와 WebM에는 `ffmpeg` |

첫 내보내기는 [출력 형식 선택](output-guide.md)을, 각 형식이 보존하거나 잃는 내용은 [내보내기 레퍼런스](exports.md)를 참고하세요.

### PNG에 `quality`를 설정할 수 있나요? { #can-i-set-quality-for-a-png }

아니요. `quality`는 JPEG와 WebP에만 적용됩니다. PNG에 전달하면 `RenderingError`가 발생합니다.

### 파일을 쓰지 않고 이미지를 얻으려면 어떻게 하나요? { #how-do-i-get-the-image-without-writing-a-file }

```python
png_base64 = canvas.to_base64(format="PNG")
jpeg_data_url = canvas.to_data_url(format="JPEG", quality=90)
```

## JSON { #json }

### `Canvas.from_json()`에 dict를 전달할 수 있나요? { #can-i-pass-a-dict-to-canvasfrom_json }

아니요. JSON 문자열을 받습니다. 먼저 `json.dumps(data)`로 변환하세요.

### `to_json()`에서 왜 `ValidationError`가 발생하나요? { #why-does-to_json-raise-validationerror }

캔버스에 `.custom(fn)` 레이어가 있기 때문입니다. Python 함수는 JSON으로 기록할 수 없으므로 해당 레이어를 먼저 제거하세요.

### `to_json()` 후 `theme` 블록이 사라졌어요 { #my-theme-block-disappeared-after-to_json }

명세를 불러올 때 테마 토큰을 실제 값으로 치환하므로 `to_json()`은 그 값만 기록하고 `theme` 블록은 기록하지 않습니다.
토큰을 계속 편집하려면 원본 명세 파일을 보관하세요.

## 오류 { #errors }

### 각 오류는 무엇을 뜻하나요? { #what-do-the-different-errors-mean }

- `ValidationError`: 인수나 명세 필드가 올바르지 않습니다. 레이어를 추가하거나 명세를 불러오는 즉시 발생합니다.
- `RenderingError`: 다운로드 등 그리기 과정의 작업이 실패했습니다.
- `MissingAssetError`: 명세에서 참조한 로컬 파일이 없습니다.

모든 오류의 `details`에는 안정적인 코드, 해당 필드의 JSON Pointer, 레이어 ID가 포함됩니다.
[구조화된 오류](errors.md)를 참고하세요.
