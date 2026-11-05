---
description: 기준 샘플링, GIF/비디오 재생, Deck 내레이션, 대화형 HTML에서 시간을 사용하는 방식을 설명합니다.
---

# 애니메이션 타이밍 레퍼런스 { #animation-timing-reference }

간단한 안내는 [애니메이션 타이밍](../timing.md)을 참고하세요.

모션과 슬라이드의 길이, 화면 유지 시간, 비디오 배치 시점, 자막 큐는 모두 초 단위로 지정합니다. `sample()`은 작성한 기준 타임라인을 관찰하고, `export()`는 실제 영상에 인코딩된 타임라인을 보고합니다. 목적이 다른 측정값이므로 구분해서 사용하세요.

## 시간 기준 선택 { #choose-the-clock }

| 출력 또는 관찰 | 타이밍 계약 |
| --- | --- |
| 시간이나 fps 없는 `sample()` | Canvas/페이지마다 작성된 정적 프레임 하나입니다. 애니메이션 끝점으로 이동하지 않고 래스터 출력과 일치합니다. `duration=0`, 프레임 `time=None`입니다. |
| `sample(time=...)` | 명시적인 문서 시점을 관찰합니다. 슬라이드 구간은 `[start, end)`이며 정확한 경계는 새로 들어오는 슬라이드에 속합니다. 끝을 넘은 시점은 안정된 마지막 장면을 보여 줍니다. |
| `sample(fps=...)` | 타임라인 끝 이전의 균일 격자 `0, 1/fps, 2/fps, …`를 관찰합니다. 길이가 0인 타임라인도 0에서 한 번 관찰합니다. |
| GIF | 무음이며 프레임 길이는 10ms 단위로 가변적입니다. 같은 프레임은 합쳐질 수 있습니다. 기본 샘플링 속도는 20fps이며, 지원 범위는 0 초과 100fps 이하입니다. |
| MP4 / WebM / MOV | 유지 구간에 반복되는 프레임을 포함해 고정 속도로 인코딩합니다. 기본값은 30fps이며, 지원 범위는 0 초과 120fps 이하입니다. |
| HTML | 브라우저가 제어하는 대화형 큐와 슬라이드 이동입니다. 인코딩된 fps나 고정된 전체 재생 길이가 없고 Deck 내레이션을 재생하지 않습니다. |

`GifOptions.fps`와 `VideoOptions.fps`는 샘플링 밀도를 요청합니다. 움직이는 구간은 각자의 시간 경계 안에서 샘플링하고, 정적 구간은 화면을 유지합니다. 비디오는 누적 프레임 시계에 반복 프레임을 배정하고, GIF는 누적 길이를 1/100초 단위로 양자화합니다. 따라서 기준 균일 샘플 격자는 인코딩 파일의 인덱스가 아닙니다. 임의의 소수 구간, 팔레트/손실 인코딩, 중복 프레임 병합 때문에 프레임 위치나 개수가 달라질 수 있습니다.

애니메이션을 내보낸 뒤 `ExportResult.timing_metrics`를 확인하세요.

| 필드 | 의미 |
| --- | --- |
| `fps` | 선택한 샘플링 속도입니다. GIF에서는 저장된 프레임 수를 재생 길이로 나눈 값이 아닙니다. |
| `frame_count` | GIF 병합이나 비디오 유지 프레임 반복을 거쳐 실제로 인코딩한 프레임 수입니다. |
| `duration` | 인코딩된 시각적 재생 시간(초)입니다. GIF 지연의 합 또는 비디오 프레임 수를 fps로 나눈 값입니다. 오디오 컨테이너 패딩은 다를 수 있습니다. |

반면 `FrameSequence.duration`은 양자화 전의 기준 타임라인을 나타냅니다. HTML의 `timing_metrics`에는 고정 재생 타이밍이 없습니다. 길이가 0이라고 해서 대화형 애니메이션에 시간이 걸리지 않는다는 뜻은 아닙니다.

```python
from quickthumb import AnimationSpec, Canvas, GifOptions

canvas = Canvas(160, 90).background(color="#000000").shape(
    "rectangle", (40, 20), 80, 50, "#FF0000",
    animation=AnimationSpec.fade(duration=1),
)
samples = canvas.sample(fps=7, hold=0.37)
result = canvas.export("timed.gif", animation=GifOptions(fps=7, hold=0.37))
print(samples.duration, len(samples.frames))
print(result.timing_metrics.model_dump())
```

## 시간적 노출 { #temporal-exposure }

Canvas나 Deck 내보내기에서 프레임 시점을 중심으로 한 모션 블러를 선택할 수 있습니다.

```python
from quickthumb import MotionBlur, VideoOptions

canvas.export(
    "exposure.mp4",
    animation=VideoOptions(fps=30, motion_blur=MotionBlur(samples=8, shutter_angle=180)),
)
```

`GifOptions`와 `ImageSequenceOptions`도 같은 설정을 받습니다. 끄는 값은 `None`뿐입니다. `MotionBlur`는 샘플 2–64개와 0 초과 360도 이하의 셔터 각도를 받습니다. 셔터는 렌더링하는 각 프레임 주변의 `(angle / 360) / fps`초에 걸칩니다. 문서 타임라인 밖의 시점은 경계 상태를 사용합니다. 하드 컷에서는 중심 시점이 속한 슬라이드로 노출을 제한하며, 정확한 컷 시점은 새로 들어오는 슬라이드에 속합니다. 부드러운 전환은 시작 시점 양쪽의 샘플을 포함해 노출에 참여합니다. 비디오와 이미지 시퀀스의 노출 중심은 출력 격자 `index / fps`를 따르고, GIF 중심은 가변 길이의 샷 시계를 따릅니다. 인코딩된 sRGB의 미리 곱한 채널을 평균한 뒤 비연관 RGBA로 되돌려, 투명한 잔상에서 채도가 높은 색상을 보존합니다.

노출은 시간 지정 자막과 등장 효과도 적분합니다. 큐 경계에서 셔터 구간의 절반 이내에 있는 내용이 영향을 줄 수 있습니다. 작성한 큐 시점과 재생 길이는 바뀌지 않으며, GIF 지연과 비디오 프레임 수는 여전히 각 코덱의 시계를 따릅니다. 유지 시간이 0이면 마지막 프레임에도 움직이는 동안의 노출이 섞입니다. 동작이 완전히 끝난 화면을 보여 주려면 유지 시간을 추가하세요.

이 설정은 `workers`를 포함한 Canvas 및 Deck GIF/비디오 내보내기와 이미지 시퀀스를 지원합니다. 각 워커는 직렬 렌더링과 같은 샘플 시점 및 알파 누적으로 전체 노출을 계산합니다. 직접 바이트를 반환하는 헬퍼는 이 설정을 지원하지 않습니다. `sample()`과 `render_frame()`은 순간적인 기준 관찰로 유지됩니다. 내보내기 확인서는 지원 기능 보고서에 요청한 시간적 노출을 명시합니다. 소스 검사만으로는 내보내기 전용 설정을 추론할 수 없습니다.

### 지원과 확인서 { #support-and-receipts }

`capabilities_for(target)["motion_blur"]`는 시간적 노출 지원 여부를 선언합니다.

| 대상 계열 | 지원 | 의미 |
| --- | --- | --- |
| `video` | full | Canvas/Deck MP4, WebM, MOV와 이미지 시퀀스에서 노출을 적분합니다. |
| `raster` | partial, static fallback | 애니메이션 GIF는 노출을 적분하지만 정적 래스터 파일에는 노출 구간이 없습니다. |
| `html`, `pptx` | unsupported, static fallback | 노출을 무시하고 작성된 브라우저/PowerPoint 모션을 그대로 유지합니다. |

`VideoOptions`/`GifOptions`는 각각 애니메이션 출력 계열에 속합니다. HTML/PPTX에 전달하면 옵션 계열 오류가 발생합니다. 지원 기능 표가 이런 옵션을 조용히 허용한다는 뜻은 아닙니다. `inspect_motion()`은 소스에 작성된 기능을 보고하며 내보내기 전용 블러가 켜졌다고 주장하지 않습니다. 실제 내보내기 뒤 `result.capability_report`의 `motion_blur` 행에서 적용된 샘플 수와 각도를 확인하세요. `timing_metrics`는 인코딩된 재생 정보를 유지합니다. 이미지 시퀀스 결과에도 같은 적용 행과 프레임/길이 정보가 포함됩니다.

[움직이는 마커 예제](https://github.com/sjquant/quickthumb/blob/main/examples/motion_blur.py)를 실행하면 서로 대응하는 OFF/8샘플 GIF를 만듭니다. 이 장면은 제어된 [샘플 비용 벤치마크](https://github.com/sjquant/quickthumb/blob/main/benchmarks/README.md#temporal-exposure-cost)에도 사용됩니다.

## 슬라이드 길이와 전환 { #slide-duration-and-transitions }

레이어 모션과 들어오는 전환은 같은 슬라이드 시계에서 시작합니다. 비대화형 미디어에서 `on_click` 큐는 `after_previous`처럼 순서대로 실행하고 `with_previous` 큐는 겹쳐 실행합니다. 지연도 해당 시계에 포함됩니다. 전환은 이전 슬라이드의 안정된 장면 위에서 재생합니다. 명시적인 전환이 없는 슬라이드는 첫 슬라이드에서 즉시 시작하고 이후에는 0.5초 크로스페이드를 사용합니다. 즉시 바뀌는 경계에는 `Cut()`을 사용하세요.

슬라이드의 종료는 적용 가능한 경계 중 가장 늦은 시점으로 정합니다.

- 길이 재정의도 `advance_after`도 없으면 전환과 레이어 모션이 끝난 뒤 안정된 장면을 `hold`초(기본 3초) 유지합니다.
- Deck 비디오에서 `slide(duration=...)`는 전환과 모션을 포함한 전체 슬라이드 구간을 설정합니다. 명시적 길이가 없으면 내레이션이 구간을 제공합니다. 어느 쪽도 더 긴 시각적 애니메이션을 자르지 않으며, 둘 다 끝날 만큼 슬라이드를 유지합니다. 내레이션 자체는 예약된 구간에 맞춰 자르거나 패딩합니다.
- 전환의 `advance_after`는 `hold`를 대신하며, 들어오는 전환 뒤부터 경계를 셉니다. 그 경계, 완료된 모션, 내레이션/명시적 길이 중 가장 늦은 시점에 종료합니다. 예를 들어 1초 애니메이션에 `Cut(advance_after=0.1)`을 사용하면 `hold=3`이어도 1초에 끝나며, 끝에 3초를 덧붙이지 않습니다.

GIF는 Deck 내레이션과 `slide(duration=...)`를 무시하고 모션, 전환, `advance_after`, `hold`를 사용합니다. `Deck.sample()`은 내레이션을 고려한 비디오 일정을 사용하므로 내레이션이 있는 Deck의 GIF 길이가 샘플링 길이와 같을 필요는 없습니다.

인코더는 `hold=0`이어도 안정된 상태를 보여 줍니다. 항상 유지 프레임을 통째로 덧붙이는 대신 필요하면 마지막 모션 샷을 교체합니다. 정적 슬라이드나 한 프레임보다 짧은 슬라이드도 표현 가능한 프레임 하나는 필요합니다. 따라서 GIF와 비디오 길이는 수학적 타임라인과 조금 다를 수 있습니다. 현재 Deck 비디오는 내레이션도 명시적인 양수 길이도 없는 슬라이드에 양수 `hold`가 필요합니다. Canvas와 Deck GIF에는 0인 유지 시간도 유효합니다.

## 오디오, 자막, 동작 줄이기 { #audio-captions-and-reduced-motion }

MP4/WebM/MOV는 지원되는 클립 오디오, Deck 내레이션, 선택적 사운드트랙을 믹싱합니다. 내레이션은 해당 슬라이드의 절대 오프셋에서 시작합니다. 사운드트랙은 시각적 타임라인에 맞춰 자르며 반복할 수 있습니다. 코덱의 오디오 패딩은 보고하는 시각적 길이를 늘리지 않습니다. GIF와 이미지 시퀀스에는 오디오가 없습니다. 모션에 사운드트랙이나 내레이션이 함께 재생되어야 하면 비디오를 사용하세요. MP4 내보내기는 슬라이드별 내레이션을 유지하면서 레이어 애니메이션과 전환을 재생합니다. 정지 슬라이드 내레이션에는 정적 캔버스를 작성하고 `deck.transition(Cut())`를 설정하세요.

비디오 레이어의 `start`는 슬라이드 내 시점입니다. `trim_start`, `trim_end`, `speed`는 소스 미디어 시간을 선택합니다. 자막 `start`/`end`는 원본 파일이 아니라 배치된 클립을 기준으로 합니다. 자막은 `[start, end)` 동안 활성화되며 지원되는 래스터/비디오 출력의 전경에 구워 넣습니다. 동작 줄이기로 클립 그림이 멈춰도 자막 타이밍은 유지됩니다.

`ExportPolicy(reduced_motion=True)`는 작성된 레이어 모션과 슬라이드 전환을 억제합니다. 유지 시간, 내레이션, 자막 타이밍은 보존하며 슬라이드 사이에 기본 Deck 크로스페이드가 남을 수 있습니다. 결과 길이는 원래 모션 길이가 아니라 실제 내보내기 확인서에서 확인하세요.

HTML은 `on_click` 큐를 대화형으로, `after_previous` 큐를 자동으로 유지합니다. `advance_after`는 들어오는 전환 뒤 조건부 자동 이동을 켭니다. 프레젠테이션을 고정 길이 비디오로 바꾸지는 않습니다. HTML의 비디오 레이어는 정적 대체 출력을 사용하므로 재생/자막 타이밍을 재현하지 않습니다. 대상의 `validate_export()`와 반환된 대체 출력 진단을 확인하세요. GIF/비디오 옵션 계열, 지원하지 않는 투명도, 코덱 속도 한계는 다른 형식을 조용히 선택하는 대신 해결 방법이 있는 오류로 실패합니다.

## 재생 검증 { #verify-playback }

`tests/test_video_layers.py`의 3슬라이드 통합 장면은 실제 GIF, MP4, WebM 출력을 검사합니다. 선택한 픽셀과 기준 샘플 비교, 들어오는 전환, 자막 시작/종료 구간, 인코딩 타이밍, 디코딩한 사운드트랙 및 내레이션 주파수를 확인합니다. 동작 줄이기 사례는 정지한 클립 영상과 시간 지정 자막을 확인합니다. FFmpeg와 ffprobe를 설치한 뒤 실행하세요.

```bash
uv run --locked pytest tests/test_video_layers.py -k motion_package --no-cov
```

기존 HTML 타임라인 테스트는 Node 스테이지 픽스처에서 JavaScript를 실행합니다. 대상별 브라우저 충실도는 별도의 검사입니다.
