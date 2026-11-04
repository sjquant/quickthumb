---
description: quickthumb 이미지 시퀀스, 렌더링 품질과 병렬 애니메이션 렌더링을 설명합니다.
---

# 이미지 시퀀스와 렌더링 품질 { #image-sequences-and-render-quality }

[내보내기 레퍼런스](../exports.md) · [출력 형식 선택](../output-guide.md)

## 이미지 시퀀스 { #image-sequences }

`Canvas.export_image_sequence()`와 같은 Deck 메서드는 실제 애니메이션 타임라인을 독립된 PNG, JPEG, WebP 파일과 매니페스트 하나로 기록합니다.
목적지는 새 경로여야 하며 부모 디렉터리는 존재해야 합니다. 기본 형식은 PNG입니다.

```python
from quickthumb import ImageSequenceOptions

options = ImageSequenceOptions(fps=24, hold=2, render_quality="high", workers=2)
result = canvas.export_image_sequence("overlay_frames", options=options)
canvas.export_image_sequence("review_frames", format="jpeg", quality=85, matte="white", options=options)
canvas.export_image_sequence("web_frames", format="webp", lossless=True, options=options)
print(result.frame_count, result.duration, result.manifest_path)
```

인코딩 제어는 메서드의 키워드 인수이며 `ImageSequenceOptions(fps=30, hold=3, workers=1, render_quality="standard")`의 타이밍·합성과 별개입니다.

| 제어 | PNG | JPEG | WebP |
| --- | --- | --- | --- |
| `format`(대소문자 구분 없음) | 기본 `"png"` | `"jpeg"` | `"webp"` |
| `quality` | 거부 | 정수 1–95, 기본 90 | 손실 출력 정수 1–95, 기본 80 |
| `matte` | 거부 | 불투명 색상 문자열, 기본 흰색 | 거부 |
| `lossless` | 거부 | 거부 | 불리언, 기본 `False` |

`lossless=True`와 `quality`를 함께 쓸 수 없습니다.
품질은 무손실 WebP 인코더의 노력 수준이 아닌 손실 압축 품질입니다.
잘못된 자료형이나 호환되지 않는 옵션은 출력·임시 저장소를 만들기 전에 실패합니다.
옵션 모델에는 `fps`(유한하며 0 초과, 120 이하), `hold`(유한한 0 이상의 초), `workers`(엄격한 정수 1–8), `render_quality`(`"standard"` 또는 `"high"`)만 있습니다.

PNG는 숨겨진 RGB를 포함해 렌더러의 정확한 **8비트 straight-alpha RGBA 바이트**를 유지합니다.
무손실 WebP도 숨겨진 RGB를 포함한 픽셀을 보존합니다.
JPEG는 해석된 매트에 알파를 평탄화해 RGB로 인코딩합니다.
JPEG와 손실 WebP는 색상이 바뀔 수 있으므로 정규 픽셀과 정확히 같다고 보장하지 않습니다.
WebP는 알파를 유지하지만 완전히 불투명한 파일은 중복 알파 평면을 생략하고 이미지 리더에서 RGB로 열릴 수 있습니다.
매니페스트의 논리적 `mode: "RGBA"`를 사용할 때는 RGBA로 변환하세요.
제작한 배경은 모든 형식에서 계속 보입니다.
홀수 크기와 1픽셀 크기도 모든 행과 열을 유지합니다.
크기가 다른 슬라이드는 첫 Canvas의 전체 크기에 맞추며 인코딩 전에 투명 여백(JPEG는 매트 색상)을 넣습니다.
가져온 이미지는 ICC 정규화를 하지 않습니다. 출력은 상속된 프로필·메타데이터를 제거하며 sRGB나 색상 프로필을 보장하지 않습니다.

디렉터리에는 `000000.png`, `.jpg`, `.webp`부터 이어지는 파일과 간결한 `manifest.json` 하나가 있습니다.
`version: "1"`, `format: "image_sequence"`, 문서 `kind`, `encoding: "png"|"jpeg"|"webp"`, 상대 `filename_pattern`(`%06d.png`, `%06d.jpg`, `%06d.webp`), `start_index: 0`을 기록합니다.
실제 `frame_count`, `fps`, `duration`, `width`, `height`는 기록한 파일을 설명합니다.
픽셀 필드는 논리적 디코딩을 설명합니다. PNG/WebP는 `mode: "RGBA"`, `alpha: "straight"`, JPEG는 `"RGB"`, `"none"`이며 `bit_depth`는 8입니다.
`lossless`는 선택한 인코딩을 보고합니다. 해석된 `quality`, `matte`는 해당하는 경우에만 기록하고 나머지는 `null`입니다.

`ImageSequenceResult`는 `ImageSequenceManifest`에 절대 `output_directory`, `manifest_path`, `capability_report` 진단을 더합니다.
두 모델과 `ImageSequenceOptions`는 JSON 왕복과 `model_json_schema()`를 지원합니다.
Canvas/Deck 문서 필드나 래스터 형식 열거형 값을 추가하지 않습니다.
프레임 경로나 타임스탬프의 증가하는 목록도 없습니다.
반복 프레임은 정규 샷마다 한 번 인코딩하고 하드링크가 아닌 독립적인 편집 가능 파일로 씁니다.
프레임 메모리는 제한되지만 기존 장면 준비와 워커 버퍼도 메모리를 사용합니다.

타이밍은 명시적 슬라이드 길이, `advance_after`, 내레이션 기반 시각 타이밍, 전환, Morph를 포함해 애니메이션 내보내기를 따릅니다.
누적 프레임 할당으로 소수 유지 시간의 드리프트를 방지하며 짧거나 유지 시간이 0인 정지 슬라이드에도 최소 한 프레임을 할당합니다.
보고된 길이는 실제 기록 파일 기준의 정확한 `frame_count / fps`입니다.
독립적인 타임라인 샘플러의 길이나 표본 수와 다를 수 있습니다.
`validate_export("image_sequence")`, `inspect_motion(target="image_sequence")`는 동영상 모션 기능을 사용합니다.
기존 엄격·모션 줄이기 정책과 부모, Morph, 자막, 워커 제한이 적용됩니다.

시퀀스는 무음이며 오디오 인코딩, 멀티플렉싱, 사운드트랙, 오디오 사이드카가 없습니다.
내레이션은 기존 파일 검증과 길이 추론을 유지하되 인코더의 오디오 입력 64개 제한은 없습니다.
이미지만 있는 장면에는 FFmpeg가 필요하지 않습니다.
내레이션 길이 추론에는 여전히 ffprobe가 필요하고 동영상 레이어는 일반적인 검사·디코딩 요구 사항을 유지합니다.

모든 프레임과 `manifest.json`은 게시 전에 원자적 임시 디렉터리에 렌더링됩니다.
목적지 디렉터리는 존재하면 안 됩니다. 이미 있으면 안전하게 실패해 실수로 덮어쓰는 일을 막습니다.

`examples/image_sequence_overlay.py`는 FFmpeg 없이 PNG, 흰 매트 JPEG, 무손실 WebP 하단 그래픽 시퀀스를 만듭니다.
실행할 때마다 출력 디렉터리 세 개 모두 새 경로여야 합니다.

## 고품질 애니메이션 합성 { #high-quality-animated-compositing }

`GifOptions(render_quality="high")`, `VideoOptions(render_quality="high")`는 2배 크기 레이어 합성 표면에서 작업한 뒤 LANCZOS로 한 번 축소합니다.
기본 `render_quality="standard"`는 기존 출력을 보존합니다.
이 이름 공간이 있는 옵션은 JPEG/WebP용 `render(..., quality=...)`와 별개입니다.
애니메이션 바이트 메서드도 키워드 전용 `render_quality="high"`를 받습니다.

```python
canvas.render("smooth.mp4", animation=VideoOptions(fps=30, render_quality="high"))
deck.render("smooth.gif", animation=GifOptions(fps=12, colors=64, render_quality="high"))
```

고품질 모드는 각 소스 이미지의 확대 복사본을 보관하지 않고 준비한 레이어와 stagger 대상을 큰 표면에 직접 필터링합니다.
회전·축소된 가장자리의 결합을 개선합니다. 크기, 타이밍, 오디오, GIF 팔레트·크기 제어, `workers`의 의미는 그대로입니다.
프레임과 캐시 배경판의 픽셀이 네 배이므로 렌더링 시간과 메모리가 더 필요합니다.
워커마다 버퍼가 추가되므로 전체 메모리는 워커 수에 따라 늘어날 수 있습니다.

이는 슈퍼샘플링한 **레이어 합성**이며 고해상도 소스 레이아웃이 아닙니다.
글꼴·에셋과 배경 의존 소스 표면은 여전히 원래 크기로 준비합니다.
제작한 정적 회전도 이미 소스에 반영되어 있습니다.
축소 후 자막은 원래 해상도로 그리며 슬라이드 전환과 키가 있는 Morph도 기존 원래 해상도 경로를 유지합니다.
준비한 소스에 없는 세부를 복원할 수 없고 아주 작은 글자를 흐리게 할 수 있습니다.
동일 조건의 비용 측정과 텍스트 전후 비교는 [벤치마크 안내](https://github.com/sjquant/quickthumb/tree/main/benchmarks)를 참고하세요.

## 병렬 애니메이션 렌더링 { #parallel-animated-rendering }

`GifOptions(workers=2)`, `VideoOptions(workers=2)`는 프로세스 기반 프레임 렌더링을 사용합니다.
애니메이션 바이트 메서드에도 같은 키워드 전용 `workers`가 있습니다.
엄격한 1–8 정수이며 기본값은 여전히 1이고 CPU 수에 맞춰 자동 확장하지 않습니다.
프로세스 시작, 슬라이드 준비, 프레임 복사에 시간이 들므로 작거나 정적인 내보내기는 워커 하나가 더 빠를 수 있습니다.
인코딩과 오디오 혼합은 여전히 부모 내보내기 경로에서 실행합니다.

가져올 수 있는 스크립트와 Python의 main 가드를 사용하세요.
워커는 Linux에서도 항상 `spawn`을 사용하며 애플리케이션 전역 시작 방식은 바꾸지 않습니다.
main 모듈을 가져올 수 없는 대화형 환경에서는 `workers=1`을 사용하세요.

```python
from quickthumb import Canvas, Fade, VideoOptions

def main():
    canvas = Canvas(640, 360).background(color="#123456")
    canvas.shape("rectangle", (40, 40), 200, 160, "#FF3355",
                 animation=Fade(duration=2))
    canvas.render("parallel.mp4", animation=VideoOptions(fps=30, workers=2))

if __name__ == "__main__":
    main()
```

워커는 별도의 글꼴과 동영상 디코더로 내장 캔버스를 다시 구성합니다.
제한되고 순서가 있는 프레임 작업 창만 대기시키므로 기존 샷 길이, 접힌 유지 구간, 자막 경계, 전환 순서를 보존합니다.
로컬 동영상, 자막, 시드가 있는 입자, 내장 모션은 병렬로 동작합니다.
사용자 정의·플러그인 레이어, Canvas 하위 클래스, 원격 동영상, 시드가 없고 0이 아닌 입자는 `workers=1`이 필요합니다.
슬라이드 준비에서 해석한 원격 이미지·글꼴은 워커용으로 고정합니다.
내보내기 중에는 로컬 에셋과 글꼴 캐시 파일을 변경하지 마세요.
소스나 워커가 실패하면 내보내기가 실패하고 기존 목적지 파일을 보존합니다.

워커가 많으면 메모리가 더 필요합니다.
각 워커는 진행 중인 RGB 프레임 외에도 Python 런타임, 글꼴, 준비된 슬라이드 이미지, 디코더 캐시를 가집니다.
정상 종료와 오류 모두 실행 중인 작업이 끝날 때까지 기다린 뒤 디코더를 닫습니다.
실패하면 대기 작업을 취소하고 갑자기 종료된 워커는 렌더링 오류로 보고합니다.
운영체제가 강제 종료하면 일반적인 정리를 수행할 수 없습니다.
