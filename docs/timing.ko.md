---
description: quickthumb의 애니메이션 길이, 슬라이드 전환, 소리와 재생을 제어합니다.
---

# 애니메이션 타이밍 { #animation-timing }

애니메이션과 슬라이드 길이는 초 단위로 설정합니다.
무음 반복은 GIF, 소리 있는 모션은 동영상, 대화형 프레젠테이션은 HTML로 내보내세요.

## 장면 애니메이션과 유지 { #animate-and-hold-a-scene }

이 예제는 도형을 1초 동안 페이드인하고 마지막 이미지를 2초 유지합니다.
작업 디렉터리에 `timed.gif`를 기록하며 같은 이름의 기존 파일을 덮어씁니다.

```python
from quickthumb import AnimationSpec, Canvas, GifOptions

canvas = Canvas(320, 180).background(color="#102030").shape(
    "rectangle", (80, 40), 160, 100, "#42CEB7",
    animation=AnimationSpec.fade(duration=1),
)
canvas.export("timed.gif", animation=GifOptions(hold=2))
```

MP4, WebM, MOV에는 `VideoOptions(hold=2)`를 사용하세요. 동영상 내보내기에는 FFmpeg가 필요합니다.
`GifOptions`와 `VideoOptions`는 `fps`도 받으며 각각 기본값은 20, 30입니다.
GIF에는 오디오가 없습니다. 설치는 [출력 형식](output-guide.md)을 참고하세요.

## 슬라이드 길이와 전환 { #slide-duration-and-transitions }

Deck은 각 슬라이드의 모션과 진입 전환을 재생하고 정착된 슬라이드를 `hold`초(기본 3초) 유지합니다.
다른 전환을 선택하지 않으면 두 번째 이후 슬라이드는 0.5초 크로스페이드를 사용합니다. `Cut()`은 즉시 전환합니다.

Deck 동영상에서 `slide(duration=...)`는 진입 전환과 애니메이션을 포함한 슬라이드 전체 구간을 설정합니다.
길이를 명시하지 않으면 내레이션이 구간을 정할 수 있습니다.
더 긴 시각적 애니메이션은 끝까지 재생하게 두며 내레이션은 예정 구간에 맞춰 자르거나 채웁니다.
GIF는 슬라이드 내레이션과 `slide(duration=...)`를 무시합니다.

전환의 `advance_after`는 일반적인 유지 시간을 대체합니다.
그래도 슬라이드는 자신의 애니메이션과 동영상 내레이션 또는 명시적 길이가 끝날 때까지 기다립니다.
정확한 경계 규칙은 [타이밍 레퍼런스](reference/timing-details.md#slide-duration-and-transitions)를 참고하세요.

## 오디오, 자막과 모션 줄이기 { #audio-captions-and-reduced-motion }

MP4, WebM, MOV에는 지원되는 클립 오디오, 슬라이드 내레이션, 사운드트랙을 포함할 수 있습니다.
GIF는 무음입니다. 동영상 클립의 자막은 배치한 클립 기준 시각을 사용하며 지원되는 동영상 프레임에 직접 그립니다.

`ExportPolicy(reduced_motion=True)`는 제작한 레이어 모션과 전환을 억제하되 유지 시간, 내레이션, 자막 타이밍은 유지합니다.
Deck의 기본 크로스페이드는 남을 수 있습니다.
HTML 프레젠테이션은 대화형 클릭 큐를 유지하지만 Deck 내레이션을 재생하지 않고 동영상 레이어를 정지 프레임으로 보여 줍니다.
실제로 사용할 앱에서 내보내기 결과를 확인하세요.

## 시간 노출 { #temporal-exposure }

GIF, 동영상, 이미지 시퀀스에 모션 블러를 추가하려면 해당 내보내기 옵션에 `MotionBlur`를 전달합니다.

```python
from quickthumb import MotionBlur, VideoOptions

canvas.export(
    "exposure.mp4",
    animation=VideoOptions(fps=30, motion_blur=MotionBlur(samples=8, shutter_angle=180)),
)
```

모션 블러는 내보내기 설정이므로 HTML과 PowerPoint에서 재현되지 않습니다.
`MotionBlur`는 표본 수 2–64와 0보다 크고 360도 이하인 셔터 각도를 받습니다.
타이밍, 지원 범위, 내보내기 결과는 [모션 블러 레퍼런스](reference/timing-details.md#temporal-exposure)를 참고하세요.

### 지원과 결과 보고 { #support-and-receipts }

내보낸 뒤 적용된 모션 블러는 `result.capability_report`, 인코딩된 재생은 `result.timing_metrics`로 검사합니다.
[지원 표](reference/timing-details.md#support-and-receipts)를 참고하세요.

## 시계 선택 { #choose-the-clock }

`sample()`은 제작한 타임라인을 관찰합니다.
인코딩한 GIF나 동영상은 형식의 특성상 길이나 프레임 수가 조금 다를 수 있습니다.
HTML은 고정 길이 동영상이 아닌 대화형입니다.
정확한 프레임 시각이나 내보내기 지표가 중요하면 [표본 추출과 타이밍 레퍼런스](reference/timing-details.md#choose-the-clock)를 참고하세요.

## 재생 확인 { #verify-playback }

공유할 앱에서 내보낸 파일을 재생하고 슬라이드 전환, 자막, 소리, 마지막 유지 구간을 확인하세요.
정확한 타이밍은 `result.timing_metrics`를 검사합니다.
프로젝트의 재생 테스트는 [타이밍 레퍼런스](reference/timing-details.md#verify-playback)에 설명되어 있습니다.
