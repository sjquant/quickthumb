---
description: quickthumb를 설치하고 SVG, PDF, PPTX, 동영상, 배경 제거와 CLI용 선택 의존성을 추가한 뒤 실행 환경을 확인합니다.
---

# 설치 { #installation }

quickthumb에는 Python 3.11 이상이 필요합니다.

## 독립된 가상 환경 { #isolated-environment }

quickthumb 소스 체크아웃 밖에 가상 환경을 만들고 quickthumb 0.8.0을 설치합니다.

```bash
mkdir -p quickthumb-first-export
cd quickthumb-first-export
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "quickthumb==0.8.0"
```

Windows에서는 대신 `.venv\Scripts\activate`로 활성화합니다.
위 셸 명령은 Bash/Zsh용입니다. 의존성을 설치하려면 패키지 인덱스에 접근할 수 있거나 로컬 캐시가 채워져 있어야 합니다.
체크아웃 밖에서 실행하면 Python이 소스 디렉터리 대신 설치된 wheel을 가져옵니다.

### 기존 uv 프로젝트 { #existing-uv-project }

```bash
uv add "quickthumb[cli]>=0.8.0"
```

기본 패키지만으로 PNG, JPEG, WebP, GIF, SVG 출력과 HTML을 사용할 수 있습니다.
선택 렌더러를 추가하기 전에 [첫 에피소드 카드 렌더링](getting-started.md)을 시도해 보세요.
이 예제는 설치 후 글꼴이나 이미지를 내려받지 않습니다.

## 선택 의존성 { #optional-extras }

일부 기능에는 추가 패키지가 필요합니다. 예를 들어 `pip install "quickthumb[svg,pdf]"`처럼 이름으로 설치합니다.

| 추가 기능 | 용도 |
| --- | --- |
| `svg` | SVG 파일을 레이어로 그립니다. SVG로 *내보내기*에는 이 추가 기능이 필요하지 않습니다. |
| `pdf` | PDF 내보내기와 선택적인 PDF 충실도 검사에 사용합니다. |
| `pptx` | PowerPoint로 내보냅니다. |
| `lottie` | Canvas Lottie 내보내기에서 지원되는 텍스트 외곽선에 사용합니다. 도형만 있는 Lottie에는 필요하지 않습니다. |
| `rembg` | 이미지 배경을 제거합니다. 처음 사용할 때 약 170 MB의 모델을 내려받습니다. |
| `cli` | `render`, `lint`, `watch`, `doctor`를 포함한 `quickthumb` 명령을 제공합니다. |

MP4, WebM, MOV 내보내기에는 Python 패키지가 아닌 시스템 프로그램인 [ffmpeg](https://ffmpeg.org/)도 필요합니다.

```bash
brew install ffmpeg      # macOS
sudo apt install ffmpeg  # Debian / Ubuntu
```

MOV에는 `prores_ks` 인코더가 포함된 FFmpeg 빌드가 필요합니다.

SVG 레이어에는 네이티브 Cairo 라이브러리도 필요합니다. Python 추가 패키지는 시스템 라이브러리를 설치하지 않습니다.
플랫폼별 요구 사항은 [CairoSVG 설치 문서](https://cairosvg.org/documentation/)를 확인하세요.

## 실행 환경 확인 { #check-your-environment }

`cli` 추가 기능의 `quickthumb doctor`는 내보내기에 필요한 환경을 확인합니다.

```bash
quickthumb doctor            # PNG, the default
quickthumb doctor mp4        # discover ffmpeg/ffprobe
quickthumb doctor pdf --spec card.json -o out/card.pdf
```

필수 검사에 실패하면 종료 상태 1을 반환하므로 CI 단계로도 사용할 수 있습니다.
이 명령은 테스트 파일을 렌더링하거나 네이티브 라이브러리, 코덱 지원, 시각적 충실도를 보증하지 않습니다.
실제로 사용할 내보내기도 실행하세요. 자세한 내용은 [진단과 CLI](diagnostics.md#quickthumb-doctor)를 참고하세요.

## 개발용 체크아웃 { #development-checkout }

아직 출시되지 않은 변경 사항을 시험하려면 저장소에서 `uv build`를 실행한 뒤 생성된 wheel의 절대 경로로 독립된 가상 환경에 설치합니다.
예를 들어 `python -m pip install "/path/to/dist/quickthumb-0.8.0-py3-none-any.whl[cli]"`를 사용합니다.
이 방법은 공개된 릴리스를 내려받는 대신 체크아웃의 코드를 설치합니다.
0.7.0에서 업그레이드할 때는 [0.8.0 마이그레이션 안내](releases/0.8.0.md#migration-from-v070)를 확인하세요.

## 환경 변수 { #environment-variables }

모두 선택 사항입니다.

| 변수 | 역할 |
| --- | --- |
| `QUICKTHUMB_FONT_DIR` | `font`가 글꼴 모음 이름일 때 글꼴 파일을 찾을 폴더 |
| `QUICKTHUMB_DEFAULT_FONT` | 텍스트 레이어에 `font`가 없을 때 사용할 글꼴 |
| `QUICKTHUMB_FONT_CACHE_DIR` | 내려받은 글꼴의 캐시 위치. 기본값은 시스템 임시 폴더입니다. |
| `QUICKTHUMB_ASSET_CACHE_DIR` | 내려받은 이미지의 캐시 위치. 기본값은 시스템 임시 폴더입니다. |
| `QUICKTHUMB_ASSET_MAX_AGE` | 캐시된 다운로드를 갱신하기까지의 초 수. 설정하지 않으면 갱신하지 않습니다. |
| `QUICKTHUMB_ASSET_OFFLINE` | `1`로 설정하면 다운로드하지 않고 캐시된 파일만 사용합니다. |
| `QUICKTHUMB_FFMPEG`, `QUICKTHUMB_FFPROBE` | `PATH`에 없는 경우 `ffmpeg`와 `ffprobe`의 경로 |

캐시에 대한 자세한 설명은 [원격 에셋과 캐시](reference/export-assets.md#remote-assets-and-caching)를 참고하세요.
