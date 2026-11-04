---
description: 모양이 바뀌는 로고, 스스로 그려지는 외곽선, 움직이는 도형을 Lottie 벡터 애니메이션 파일로 만듭니다.
---

<a id="lottie-vectors"></a>

# Lottie 애니메이션 { #lottie-animations }

[내보내기 레퍼런스](../exports.md) · [출력 형식 선택](../output-guide.md)

Lottie 플레이어용으로 모양이 바뀌는 로고, 스스로 그려지는 외곽선, 움직이는 도형을 벡터 애니메이션으로 내보냅니다.
`.lot` 파일은 프레임 이미지나 오디오를 포함하지 않는 표준 Lottie JSON입니다.

## 모양이 바뀌는 로고 만들기 { #create-a-shape-changing-logo }

```python
from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    LottieOptions,
    PathMorphTrack,
    TimingSpec,
)

square = "M20 20 H80 V80 H20 Z"
diamond = "M50 10 L90 50 L50 90 L10 50 Z"
morph = AnimationSpec.timeline(
    PathMorphTrack(keyframes=[
        KeyframeSpec(time=0, value=square),
        KeyframeSpec(time=1, value=diamond),
    ]),
    timing=TimingSpec(duration=1),
    easing="ease_in_out",
)
Canvas(120, 120).path(
    square, (10, 10), 100, 100, "#159A8C",
    view_box=(0, 0, 100, 100), animation=morph,
).export("logo.lot", animation=LottieOptions(fps=24, hold=0.5))
```

사각형에서 마름모로 1초 동안 변한 뒤 0.5초 멈추는 애니메이션을 만듭니다.
게시 전에 사용할 Lottie 플레이어에서 미리 확인하세요.
곡선, 채우기, 선이 있는 로고는 [로고 모핑 예제](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_morph.py)를 실행하세요.

## 아트워크와 타이밍 선택 { #choose-artwork-and-timing }

Canvas 하나에 단색 배경·도형, SVG Path, 위치·크기·회전·불투명도 애니메이션, 선 트림, 지원되는 정적 텍스트를 포함할 수 있습니다.
도형은 사각형, 둥근 사각형, 타원, 캡슐, 삼각형, 별, 다각형을 포함합니다.
경로는 `M/L/H/V/C/S/Q/T/A/Z`, 단색 채우기·선, 짝홀 채우기 구멍을 지원합니다.

`LottieOptions.fps`는 기본 30이며 최대 120을 지원합니다.
fps가 높으면 모션 단계가 세밀해지고 파일이 커집니다.
이 비율과 제작한 키·이벤트 경계에서 모션을 표본 추출하며 각 자세는 다음 표본까지 유지됩니다.
플레이어는 표본 사이를 부드럽게 보간하지 않습니다. 정적 아트워크도 벡터로 유지됩니다.

`hold`는 마지막 멈춤을 초 단위로 추가하며 0 이상이어야 합니다.
마지막 애니메이션 종료에 이 멈춤을 더한 뒤 전체 프레임 수로 올림한 길이가 됩니다.
유지 시간이 0인 정적 Canvas도 한 프레임을 차지합니다.
내보내기 결과에 프레임 수와 길이가 담깁니다.

예제: [정적 도형](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_static.py), [곡선 Path](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_paths.py), [움직이는 도형](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_motion.py).

## Lottie 경로 모핑 { #lottie-path-morph }

`PathMorphTrack`은 제작한 view box를 유지하면서 Path 기하 구조를 바꿉니다.
채우기, 단색 선, 불투명도, 변환, 선 트림을 함께 적용할 수 있습니다.
[경로 모핑 제한](../api/path.md#path-morphing) 안에서 열린 윤곽, 닫힌 윤곽, 중첩 구멍을 지원합니다.

제작한 Path와 모든 키는 윤곽 수와 열림·닫힘 상태가 같아야 합니다.
표본 곡선, 제어점, 선 여백이 모두 view box 안에 들어와야 합니다.
겉으로는 들어맞아 보여도 이 경계를 넘는 곡선이 있을 수 있으므로 기하 구조를 조절하거나 위치를 바꾸세요.
선이 있는 Path는 view box의 균일한 크기 조절이 필요하며 퇴화한 선 윤곽은 거부됩니다.

크거나 복잡한 애니메이션은 Canvas 전체의 자세·윤곽 정점 관찰 100,000회 제한을 넘을 수 있습니다.
이 제한을 보고하면 fps를 낮추거나 경로를 단순화하세요.
중간 모핑은 렌더링된 Quickthumb 프레임과 같은 근사 외곽선을 따르며 정확한 제작 끝점은 곡선을 유지합니다.

## Lottie 선 트림 { #lottie-stroke-trim }

`TrimEndTrack`으로 외곽선을 점진적으로 그리거나 `TrimStartTrack`, `TrimOffsetTrack`으로 보이는 구간을 이동합니다.
정적 `trim_start`, `trim_end`, `trim_offset`도 지원합니다.
[선 트림 예제](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_trim.py)를 참고하세요.

트림 위치는 윤곽 순서대로 전체 경로 길이의 0부터 1까지입니다.
오프셋은 순환하며 음수나 1보다 큰 값도 가능합니다.
전체 0→1은 오프셋과 무관하게 선 전체를 유지하며 끝점이 같거나 1→0이면 숨깁니다.
아래의 채우기는 전체로 남습니다. 닫힌 이음새는 연결 모양을, 잘린 끝점은 선택한 끝점 모양을 사용합니다.
점선과 점선 오프셋 애니메이션은 지원하지 않습니다.
플레이어 반올림으로 사라지거나 끝점이 눈에 띄게 이동할 정도의 아주 작은 트림 구간은 거부될 수 있습니다.

## 도형을 함께 이동 { #move-shapes-together }

[부모 연결 예제](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_parenting.py)처럼 `parent`로 지원되는 Shape와 Null 레이어를 연결하세요.
자식은 독립적인 그리기 순서와 불투명도를 유지하며 부모 변환을 따릅니다.
부모 불투명도는 자식을 흐리게 하지 않습니다.
자식의 백분율 위치도 Canvas를 기준으로 해석합니다. Path 부모 연결은 지원하지 않습니다.

연결되지 않은 애니메이션 도형은 애니메이션 전에 Canvas 안에 들어와야 합니다.
연결된 도형은 부모 변환으로 보이는 영역에 들어온다면 밖에서 시작해도 됩니다.
0 이하의 균일한 Shape/Null 크기는 지원하지 않습니다.
축별 크기 조절은 반사와 붕괴를 포함해 기존 동작을 유지합니다.

## Lottie 텍스트 외곽선 { #lottie-outlined-text }

정적인 한 줄 인쇄 가능 ASCII 텍스트를 포함하려면 `quickthumb[lottie]`를 설치하세요.
텍스트는 벡터 외곽선이 되므로 뷰어에 글꼴이 필요하지 않지만 텍스트로 편집할 수 없습니다.
Shape와 Path 내보내기에는 이 추가 의존성이 필요하지 않습니다.
[텍스트 외곽선 예제](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_text.py)를 참고하세요.

불투명 텍스트 색상과 필요한 모든 글리프를 가진 로컬 비가변·비컬러 글꼴을 사용하세요.
지원되지 않는 글리프는 오류를 발생시킵니다.
텍스트 애니메이션, 부모 연결, 회전, 줄바꿈·맞춤, 부분별 서식, 카운터, 효과, 마스크, 그라디언트, 원격 글꼴, 복잡한 문자 조형은 지원하지 않습니다.
RAQM 레이아웃에서 여러 문자는 0이 아닌 `letter_spacing`을 명시해야 합니다.
자간이 없는 BASIC 텍스트는 문자 전진 폭이 가산적이어야 합니다.
레이어당 최대 문자 1024개, 외곽선 정점 65,536개, 글꼴 소스 64 MiB를 허용합니다.

## 내보내기 전 호환성 확인 { #check-compatibility-before-exporting }

`canvas.validate_export("lottie")`는 지원하지 않는 레이어와 필드를 식별합니다.
내보내기는 목적지를 열기 전에 미지원 콘텐츠를 거부하므로 기존 파일을 보존합니다.
일부 중간 모핑, 정밀도, 자원 제한 오류는 애니메이션 컴파일 중에만 발견할 수 있습니다.

그라디언트, 효과·프리셋, stagger, 마스크, 뷰포트 클리핑, 색칠·점선 트랙, 모션 경로, 이미지, 플러그인, Deck 출력은 지원하지 않습니다.
내보내기 정책에서 요청해도 정적 또는 래스터 대체 표현을 사용할 수 없습니다.
Lottie 불러오기, ZIP 패키징, 기존 Lottie 파일 편집은 제공하지 않습니다.

`ExportPolicy(reduced_motion=True)`는 제작한 정적 아트워크를 `hold`초 동안 내보냅니다.
애니메이션의 최종 자세를 선택하지 않으며 다른 미지원 기능은 여전히 제거해야 합니다.
