---
description: quickthumb의 형식 충실도와 검증에 관한 레퍼런스입니다.
---

# 형식 충실도와 검증 { #format-fidelity-and-validation }

[내보내기 레퍼런스](../exports.md) · [출력 형식 선택](../output-guide.md)

## 선택적 정적 SVG 충실도 보고서 { #optional-static-svg-fidelity-report }

현재 작업에서 허용할 오차를 정했다면 `ExportPolicy`로 CairoSVG 비교를 요청할 수 있습니다. 세 가지 한계를 모두 명시해야 하며, 형식별로 미리 정해진 기본 허용치는 없습니다. 다음 예제는 가장자리나 글꼴 차이에 대한 애플리케이션별 허용치 대신 보이는 RGBA의 정확한 일치를 요청합니다.

```python
from quickthumb import Canvas, ExportPolicy

policy = ExportPolicy(fidelity={"svg": {
    "pixel_tolerance": 0,
    "max_different_pixel_ratio": 0,
    "min_hash_similarity": 1,
}})
canvas = Canvas(160, 90).background(color="#123456")
result = canvas.export("checked.svg", policy=policy)
comparison = result.pixel_metrics.fidelity
print(comparison.verdict, comparison.pixel_diff_ratio, comparison.hash_similarity)
```

선택한 SVG 내보내기에서 이 검사를 요청할 때만 선택 의존성인 `quickthumb[svg]`와 시스템 Cairo가 필요합니다. 보고서에는 CairoSVG/Cairo 버전, 기준 렌더링 환경, 적용된 한계, 실제 래스터화 크기가 기록됩니다. 크기를 바꾸지 않고 작성된 정적 상태의 `sample()` 정지 화면과 비교합니다. `exact`는 보이는 모든 RGBA 채널이 일치한다는 뜻입니다. `tolerated`는 지정한 픽셀 비율과 평균 해시 한계를 만족하며, `out_of_policy`는 한계나 크기가 맞지 않는다는 뜻입니다. 평균 절대 오차는 네 채널에 걸쳐 정규화되며 최대 채널 차이도 보고됩니다. 완전히 투명한 픽셀에서는 숨겨진 RGB를 무시하므로, 여기서 말하는 정확한 일치는 기준 원시 픽셀의 SHA-256 일치와 다릅니다. 8×8 평균 해시는 흰색 위에 합성합니다. 해시가 같아도 RGBA 측정은 알파 손실을 별도로 감지합니다.

이 검사는 결과를 보고하는 용도입니다. 판정이 `out_of_policy`여도 원래 SVG를 그대로 저장합니다. 충실도 진단은 비교 결과만 알려 주며, 다른 래스터 출력으로 자동 전환하지 않습니다. 기준 렌더링이 없거나 실패하면 대상을 열기 전에 오류가 발생해 기존 파일을 보존합니다. 기본 내보내기와 SVG 이외의 대상은 이 비교를 수행하지 않습니다.

이 관찰은 기록된 환경의 정적 Cairo 렌더링에 적용됩니다. Cairo는 설치된 글꼴을 사용하며 삽입된 CSS `@font-face`를 따르지 않으므로, 같은 글꼴 환경을 별도로 제공해야 합니다. [CairoSVG 문서](https://cairosvg.org/documentation/)를 참고하세요. 브라우저, HTML, 애니메이션 충실도를 보장하지는 않습니다. SVG는 기존의 작성된 정적 모션 동작을 유지합니다.

## 선택적 정적 PDF 충실도 보고서 { #optional-static-pdf-fidelity-report }

Canvas PDF 내보내기는 `"pdf"` 키 아래에서 같은 세 가지 명시적 한계를 받습니다.

```python
policy = ExportPolicy(fidelity={"pdf": {
    "pixel_tolerance": 0,
    "max_different_pixel_ratio": 0,
    "min_hash_similarity": 1,
}})
result = Canvas(160, 90).background(color="#123456").export("checked.pdf", policy=policy)
print(result.pixel_metrics.fidelity.verdict)
```

ReportLab과 선택적 PDFium 관찰 도구를 사용하려면 `quickthumb[pdf]`를 설치하세요. 기본 PDF 내보내기는 PDFium을 임포트하지 않습니다. 비교를 요청하면 실제 PDF 바이트를 배율 1의 투명 RGBA로 렌더링합니다. 이 내보내기는 기준 픽셀당 PDF 포인트 하나를 사용하며, 96-DPI 인쇄 크기로 변환하지 않습니다. 보고서에는 PDFium과 바인딩 버전, 실제 페이지 크기(포인트), 페이지 수, 렌더링 크기, 기준 환경이 기록됩니다. 네이티브 PDFium 문서/렌더링/정리 호출은 스레드 간에 직렬화하며, 기준 렌더링과 픽셀 비교는 해당 잠금 밖에서 수행합니다. 예상 포인트 크기의 페이지가 정확히 한 장이어야 합니다. 픽셀 한계가 느슨해도 불일치는 정책을 벗어납니다. 크기를 바꾸거나 흰 배경으로 평탄화해 알파나 기하 손실을 숨기지 않습니다.

위에서 설명한 보이는 RGBA/해시 기준과 보고 전용 동작이 똑같이 적용됩니다. 예상과 달리 Canvas 결과가 여러 페이지이면 첫 페이지를 측정하고, 보고된 페이지 수 때문에 정책을 벗어났다고 판정합니다. PDF 생성과 요청한 비교는 대상을 열기 전에 끝납니다. 관찰 도구가 없거나 실패하면 기존 파일을 보존합니다. 충실도 판정과 관계없이 네이티브 텍스트/벡터와 이유가 설명된 래스터 조각을 유지합니다. 네이티브 PDF 텍스트는 검색 가능한 벡터 콘텐츠이지만 PowerPoint 같은 편집을 보장하지 않습니다. Deck PDF 비교는 명시적으로 거부합니다. Canvas 슬라이드를 각각 내보내세요. 이 관찰은 PPTX나 애니메이션 충실도를 입증하지 않습니다.

## PPTX 호환성 { #pptx-compatibility }

PPTX는 지원하는 텍스트와 도형을 편집 가능한 상태로 유지합니다. 글로우는 고정 이미지로 편집 가능한 콘텐츠와 함께 포함될 수 있습니다. 편집 후 글로우를 갱신하려면 다시 내보내세요. 외곽선이 있는 콘텐츠도 여러 개체를 함께 편집하거나 다시 내보내야 할 수 있습니다.

다음 효과 조합은 해당 레이어를 그림으로 내보냅니다.

- 선/글로우 효과가 있는 반투명 텍스트, 도형, 외곽선.
- 선/글로우 효과가 있는 그라디언트 채우기 도형.
- 글로우가 있는 리치 텍스트 또는 글로우와 그림자를 함께 쓰는 콘텐츠.
- 원본이 슬라이드 밖으로 뻗는 도형 글로우.

불투명 선형 그라디언트 텍스트는 편집 가능한 채우기와 외곽선을 유지할 수 있습니다. 각 텍스트 부분이 실제 사용하는 페인트만 반투명 여부를 결정합니다. 사용하지 않거나 덮어쓴 색상 때문에 편집 가능성이 사라지지는 않습니다.

내보내기 전에는 `canvas.validate_export("pptx")`, 이후에는 결과의 `capability_report`에서 호환성 결정을 확인하세요. 편집 가능한 전경과 고정 효과가 혼합되면 `support="partial"`, 전체 레이어가 이미지이면 `support="fallback"`입니다. 확인서 필드는 [문서 레이어 라우팅](export-methods.md#document-layer-routing)을 참고하세요.

`ExportPolicy(pptx={"title": "native"})`는 ID가 `title`인 레이어에 이런 효과 이미지나 혼합 표현을 허용하지 않습니다. `ExportPolicy(unsupported_motion="error")`도 이런 효과 대체 출력을 거부합니다. Canvas와 Deck의 `to_pptx(policy=...)`는 파일 내보내기와 같은 정책 검사를 적용합니다. 기본값은 이유가 설명된 대체 출력을 허용합니다.

## HTML 브라우저 검증 도구 { #html-browser-validation-harness }

개발자용 도구는 명시적으로 선택한 Chrome과 Node 내장 WebSocket을 사용해 실제로 내보낸 Canvas 및 두 슬라이드 Deck 스테이지를 캡처합니다. 브라우저를 설치하거나 `ExportPolicy`를 변경하지 않습니다.

```bash
PYTHONPATH=. python scripts/check_html_fidelity.py \
  --chrome "/path/to/chrome" --output /tmp/quickthumb-html-observations
```

출력 디렉터리는 새 디렉터리여야 합니다. Chrome은 임시 프로필과 루프백 CDP로 헤드리스 실행하며, 기존 브라우저 세션에 연결하지 않습니다. 글꼴, 이미지, 슬라이드 전환을 기다리고 DPR 1에서 원래 크기의 스테이지만 캡처합니다. 실제 클릭으로 시작한 CSS 페이드를 0초, 5초, 10초로 탐색합니다. 보고서에는 브라우저/Node 버전, 기준 환경, 입력 에셋 해시, 실행된 라우트 진단, 크기, 탐색 시점, 명시적 픽스처 한계, 픽셀/해시 측정값, 판정이 기록됩니다. 기준/브라우저 PNG도 함께 남깁니다.

텍스트/도형/이미지/마스크 혼합 픽스처는 채널 허용 오차 16, 다른 픽셀 최대 8%, 평균 해시 유사도 최소 0.94를 허용합니다. 각 구성 요소도 기록된 영역 기준을 만족해야 합니다. 텍스트는 다른 픽셀 20%를 허용하고 해시 유사도 0.95를 요구하며, 네이티브 타원은 2%와 0.98을 요구합니다. 삽입 이미지는 정확히 일치해야 하고, 마스크 조각은 채널 한 단계의 반올림만 허용합니다. 텍스트/타원 채널 허용 오차는 16입니다. 이 지역별 기준은 작은 요소가 사라져도 전체 스테이지 평균으로 통과하는 일을 막습니다. 부정 대조군은 가로형 Canvas와 세로형 Deck 양쪽에서 텍스트/이미지/마스크/타원 요소를 각각 제거하며, 다른 측정값만이 아니라 해당 영역에서 실패해야 합니다. 모든 허용치는 이 픽스처에만 해당하며 일반 문서의 허용치가 아닙니다. 단순 페이드는 채널 한 단계의 반올림만 허용합니다. 의도적으로 잘못된 문서는 비교에서 실패해야 합니다. 예상하지 못한 판정이 나오면 명령은 실패하고 보고서는 보존합니다. 자동 래스터 대체 출력이나 브라우저/CI 설치는 수행하지 않습니다.

이는 하나의 Chrome/글꼴/플랫폼 환경과 제한된 CSS 애니메이션 하나를 관찰합니다. 모든 브라우저, 애니메이션, 큐, Deck 전환을 검증하지는 않습니다. CairoSVG는 이 브라우저 관찰을 대신할 수 없습니다. 기존 Node 런타임 테스트는 브라우저 픽셀과 별도로 스케줄링과 상태 동작을 검사합니다.

## 정적 형식 간 내보내기 검사 { #static-cross-export-checks }

`tests/test_static_export_matrix.py`는 같은 작성 콘텐츠를 공개 Canvas 및 Deck 파일 내보내기 경계를 통해 전달합니다. 첫 160×120 슬라이드에는 저장소 글꼴 텍스트, 네이티브 사각형, 생성 이미지, 타원 마스크를 조합합니다. 두 번째 Deck 슬라이드에는 투명 캔버스 위의 반투명 사각형이 있습니다. 검사는 측정한 외관과 구조적 근거를 구분합니다.

| 형식 | Canvas | Deck | 지원 기능 및 대체 출력 근거 |
| --- | --- | --- | --- |
| PNG | 디코딩한 RGBA가 기준 샘플과 일치 | 번호가 붙은 각 슬라이드가 기준 샘플과 일치 | 래스터 출력이며 네이티브 개체나 문서 뷰어에 관한 주장은 하지 않음 |
| SVG | 실제 CairoSVG 관찰 및 네이티브 텍스트/벡터와 PNG 검사 | 단일 파일 Deck SVG는 거부하고 각 Canvas 슬라이드를 별도로 측정 | 실행된 소스 ID, 네이티브 라우트, 이유가 설명된 이미지/마스크 PNG 라우트 |
| HTML | 스테이지 마크업, 네이티브 텍스트/CSS, 정확한 마스크 PNG | 스테이지 수와 슬라이드별 라우트 | 구조만 검사하며 이 매트릭스에서 브라우저 픽셀은 측정하지 않음 |
| PDF | 실제 PDFium 관찰, 검색 가능한 텍스트, 벡터 경로, 이미지 개체 | 페이지 수/기하, 네이티브 개체, 렌더링한 구성 요소 영역 | Canvas 라우트는 보고하지만 Deck 실행 라우트와 확인서 충실도는 아직 수집하지 않음 |
| PPTX | 편집 가능한 OOXML 텍스트/도형과 정확한 위치의 마스크 PNG | 슬라이드 수 및 슬라이드별 네이티브/래스터 개체 | 실행된 라우트는 보고하지만 PowerPoint/Keynote 외관은 아직 측정하지 않음 |

혼합 SVG/PDF 픽스처에는 명시적 전체 이미지 한계를 적용합니다. 채널 허용 오차 0, 다른 픽셀 최대 8%, 해시 유사도 최소 0.94입니다. 이 수치는 픽스처별 글꼴/가장자리 허용치이며 내보내기 기본값이 아닙니다. 네이티브 텍스트는 텍스트로도 존재해야 하며, 작은 사각형, 이미지, 마스크 내부 영역은 정확히 일치해야 합니다. 그래야 누락된 구성 요소가 전체 이미지 허용치에 가려지지 않습니다. 텍스트 영역도 해시 유사도 최소 0.95를 요구하며, 글꼴 래스터화 가장자리에 채널 허용 오차 16을 적용한 뒤 다른 픽셀을 최대 30%까지 허용합니다. 흰 배경 위의 검색 가능한 흰 텍스트를 담은 실제 Deck PDF는 텍스트 개체와 다른 구성 요소 영역이 온전해도 이 영역 검사에 실패해야 합니다. 투명 사각형에 한해서는 알파가 정확히 일치해야 하지만, 렌더러의 미리 곱하기/되돌리기 반올림 때문에 보이는 RGB는 채널당 최대 두 단계까지 다를 수 있습니다. 완전히 숨겨진 RGB에는 기존 보이는 RGBA 비교 규칙을 적용합니다. PNG는 여전히 원시 RGBA를 정확히 보존합니다. 출력 크기를 바꾸거나 임의의 매트 색상으로 평탄화하지 않습니다.

`uv run --locked pytest tests/test_static_export_matrix.py --no-cov -q`를 실행하세요. 기존 품질 워크플로는 SVG/PDF/PPTX 선택 의존성과 네이티브 Cairo를 설치한 뒤 `pytest tests/`로 이 파일을 실행합니다. 로컬 환경에 선택적 관찰 도구가 없으면 의존성 이유와 함께 해당 사례를 건너뜁니다. Pytest 사례 ID는 형식과 문서 종류를 식별합니다. 각 사례는 임시 디렉터리에 소스 JSON, 기준 PNG, 실제 내보내기, JSON 확인서를 보관합니다. 측정된 확인서에는 렌더러 버전, 기준 환경, 한계, 측정값이 포함됩니다. 플랫폼별 스크린샷 기준 대신 공유 픽스처와 이름이 붙은 형식 검사로 실패를 재현할 수 있습니다.

이는 범위가 제한된 정적 매트릭스입니다. 브라우저를 실행하거나 PPTX 뷰어의 픽셀/글꼴/타이밍을 인증하거나 Deck PDF 충실도 정책을 추가하지 않습니다. 별도의 HTML 브라우저 도구와 네이티브 프레젠테이션 뷰어 관찰에는 각각 실행과 환경 근거가 필요합니다. 구조 검사의 성공을 렌더링 픽셀 충실도 판정으로 보고해서는 안 됩니다.

## Lottie 기준 플레이어 { #lottie-reference-player }

기준 검사는 **lottie-web 5.13.0 SVG**와 공식 **Lottie Android 6.7.1**을 사용합니다.
Android는 Robolectric 4.17 NATIVE graphics, Android 15/API 35, mdpi의 software Drawable을
Linux/JVM에서 실행합니다. 9개 파일을 schema 1.0.1로 검증하며 각 플레이어는 정상 프레임 37개와
빈 출력·멈춘 모션 대조 15개를 검사합니다. 기존 31+13에 다중 윤곽 트림·길이 변화·반투명 공통
stroke를 확인하는 6+2를 더했습니다. 전체 프레임과 작품 영역 모두 채널 허용차 32, 차이 픽셀
8% 이하, 해시 0.93 이상을 요구합니다. 공통 stroke 내부 픽셀은 채널 차이 2 이하도 검사합니다.

기존 웹 CI artifact에 Android의 `report.json`, `execution.json`, `maven.log`도 실패 시를
포함해 보존합니다. Native PNG는 작업 로컬에 남으므로 아래 명령으로 같은 manifest를 재실행해
얻을 수 있습니다. 실제 Android 라이브러리·native graphics 검사이며 실기기·에뮬레이터·ARM/GPU·
iOS·앱 성능 검사는 아닙니다. 사용 설정은 [가이드](export-lottie.md#play-it-on-the-web)에 있습니다.

### 반투명 fill/stroke 조사

960×640 다중 윤곽 morph의 frame 0 탐색 사례는 Android ROI `(500,320)-(860,560)`의
해시가 **0.921875**로 기준 **0.93**에 못 미칩니다. 차이 픽셀은 **3.2928%**로 8% 안이며,
전체 해시는 1.0, 차이는 1.5653%입니다. 같은 입력을 다시 내보내 동일 수치를 재현했습니다.
다른 레이어나 morph 애니메이션을 제거해도 결과가 같으며, fill만·stroke만인 대조는 통과합니다.
Android의 결합 출력은 분리한 fill 위에 stroke를 합성한 결과와 정확히 같습니다.

채널 허용차 32를 넘는 2,845픽셀은 모두 알파 경계 주변에 있습니다. 양 렌더러의 분리된
fill/stroke 알파가 7×7 이웃에서 두 단계 이내로 일정한 65,459픽셀의 최대 채널 차이는 2입니다.
이는 morph 길이 샘플링보다 페인트 경계의 래스터화·합성을 가리키지만, exporter 결함이나 이전
버전 대비 회귀를 입증하지는 않습니다. 기존 52건의 기준은 유지하며 불투명 fill morph와 공통
반투명 stroke를 각각 검사합니다.

재현하려면 `examples.lottie_trim_multi.build_canvas()`의 `id="morph"` 레이어만
`color="#159A8C40"`으로 바꾸고 `LottieOptions(fps=24, hold=0.5)`로 내보내세요.
`render_frame(0)`과 Android frame 0을 위 ROI·기준으로 비교합니다. 해당 레이어만 남기기,
`animation` 제거, `stroke` 또는 `color`만 제거하기로 대조할 수 있습니다.

문자 컴파일의 레이어별 상한은 1,024문자, 외곽선 정점 65,536개, 글꼴 소스 64 MiB입니다.
RAQM 여러 글자에는 명시적 0 아닌 자간이 필요하고, 자간 없는 BASIC은 전진 폭이 가산적이어야
합니다. 정밀도·자원 검사는 중간 샘플의 컴파일까지 포함해 쓰기 전에 끝납니다.

```bash
uv sync --locked --extra lottie --dev
npm ci --prefix tests/fixtures/lottie/player --ignore-scripts --no-audit --no-fund
PYTHONPATH=. uv run --locked python scripts/check_lottie_fidelity.py \
  --chrome /path/to/chrome \
  --player tests/fixtures/lottie/player/node_modules/lottie-web/build/player/lottie.min.js \
  --output /tmp/quickthumb-lottie-observations
```

### Android native graphics 재실행

웹 검사의 manifest와 기존 JDK 21·Maven 3.9+를 사용합니다. Maven이 test 전용 의존성을 가져옵니다.

```bash
PYTHONPATH=. uv run --locked python scripts/check_lottie_android.py \
  --maven /path/to/mvn --java-home /path/to/jdk-21 \
  --cases /tmp/quickthumb-lottie-observations/cases.json \
  --output /tmp/quickthumb-android-observations
```
