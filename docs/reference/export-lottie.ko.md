---
description: 벡터 로고 애니메이션, 스스로 그려지는 외곽선, 재사용 가능한 인트로를 만듭니다.
---

<a id="lottie-vectors"></a>

# Lottie 애니메이션 { #lottie-animations }

[내보내기 레퍼런스](../exports.md) · [출력 형식 선택](../output-guide.md)

모양이 바뀌는 로고, 스스로 그려지는 외곽선, 제목과 움직이는 배지가 있는 인트로를 만드세요.
Canvas를 `.lot`으로 내보내면 Lottie 플레이어에서 벡터로 재생할 수 있습니다.
렌더링한 영상 프레임이나 뷰어용 글꼴 파일을 함께 배포할 필요가 없습니다.

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

사각형이 1초 동안 마름모로 바뀐 뒤 0.5초 멈춥니다.
두 경로, 색상, 크기, easing을 바꿔 원하는 로고를 만드세요.

<a id="playback-verification"></a>

## 웹에서 재생하기 { #play-it-on-the-web }

웹 프로젝트에 `lottie-web@5.13.0`을 설치하고
`<div id="logo" style="width:120px;height:120px"></div>` 같은 컨테이너를 추가하세요.
`logo.lot`을 공개 정적 파일 디렉터리에 넣은 뒤 다음처럼 재생합니다:

```javascript
import lottie from "lottie-web";

lottie.loadAnimation({
  container: document.getElementById("logo"),
  renderer: "svg",
  loop: true,
  autoplay: true,
  path: "/logo.lot",
});
```

채우기·선·레이어의 불투명도를 일관되게 재생하려면 `renderer: "svg"`를 사용하세요.
lottie-web 5.12.2·5.13.0의 Canvas 렌더러에는 불투명도 결합 문제가 있습니다.
게시 전 실제 사이트나 앱의 플레이어에서 파일을 확인하세요. 기준 버전과 반복 가능한
비교 방법은 [개발자용 플레이어 검증](export-validation.md#lottie-reference-player)에 있습니다.

## 완성된 인트로 재사용하기 { #reuse-a-complete-intro }

저장소 루트에서 실행하면 외곽선 제목, 그려진 뒤 원으로 변하는 로고, 회전하는 배지가
있는 2초 인트로를 만들 수 있습니다:

```bash
pip install 'quickthumb[lottie]'
python -m examples.lottie_intro /tmp/intro.lot
```

인트로는 마지막에 0.5초 멈춥니다. [인트로 예제](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_intro.py)의
제목·색상·경로·회전을 바꿔 재사용하세요. 내보낸 제목은 뷰어에 글꼴을 설치하지 않아도 보입니다.

## 아트워크와 타이밍 선택 { #choose-artwork-and-timing }

단색 배경·도형, 채우기·선·구멍이 있는 SVG Path에 위치·크기·회전·불투명도 트랙을
조합하세요. [정적 도형](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_static.py),
[곡선 Path](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_paths.py),
[움직이는 도형](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_motion.py) 예제로 시작할 수 있습니다.

`LottieOptions(fps=24, hold=0.5)`는 모션을 초당 24회 샘플링하고 끝에 0.5초 멈춤을 더합니다.
기본값은 30 fps이며 최대 120까지 높여 모션을 세밀하게 만들 수 있습니다. fps가 높을수록
파일이 커집니다. 각 자세는 다음 샘플까지 유지됩니다. 내보내기 결과에서 프레임 수와 길이를 확인하세요.

## Lottie 경로 모핑 { #lottie-path-morph }

`PathMorphTrack`에 채우기·선·불투명도·변환·트림을 함께 적용하세요.
곡선 로고는 [모핑 예제](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_morph.py)를 응용할 수 있습니다.

모든 경로의 윤곽 수와 열림·닫힘 상태를 맞추세요. `view_box`에는 곡선·제어점·선이
들어갈 여유를 두고, 선이 있는 경로는 균일하게 확대·축소하세요. 기하 구조나 작업량 오류가
나면 안내에 따라 view box를 넓히거나 경로를 단순화하거나 fps를 낮추세요.
자세한 제작 규칙은 [경로 모핑](../api/path.md#path-morphing)을 참고하세요.

## Lottie 선 트림 { #lottie-stroke-trim }

`TrimEndTrack`으로 외곽선이 그려지는 애니메이션을 만듭니다. 위 로고 예제에 이어서 실행하세요:

```python
from quickthumb import TrimEndTrack

outline = AnimationSpec.timeline(
    TrimEndTrack(keyframes=[
        KeyframeSpec(time=0, value=0),
        KeyframeSpec(time=1, value=1),
    ]),
    timing=TimingSpec(duration=1),
    easing="ease_in_out",
)
Canvas(120, 120).path(
    square, (10, 10), 100, 100, None,
    view_box=(0, 0, 100, 100), stroke="#159A8C", stroke_width=3,
    animation=outline,
).export("outline.lot", animation=LottieOptions(fps=24, hold=0.5))
```

보이는 구간을 이동하려면 `TrimStartTrack`과 `TrimOffsetTrack`을 쓰세요. 정적인
`trim_start`, `trim_end`, `trim_offset`도 사용할 수 있습니다. 위치 0부터 1은 모핑 중에도
윤곽 순서대로 전체 경로 길이를 나타내며, 오프셋은 양방향으로 순환합니다.
0→1은 선 전체를 그리고, 끝점이 같거나 1→0이면 숨깁니다. 아래 채우기는 그대로 남습니다.
단색 실선을 사용하고 잘린 끝의 모양은 `line_cap`으로 고르세요. 아주 짧은 구간에서 정밀도
오류가 나면 구간을 넓히세요. [선 트림 예제](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_trim.py)를 참고하세요.

## 도형을 함께 이동 { #move-shapes-together }

Shape를 Null에 `parent`로 연결하면 여러 도형을 함께 회전하거나 이동할 수 있습니다.
[부모 연결 예제](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_parenting.py)로 시작하세요.
자식은 그리기 순서와 불투명도를 독립적으로 유지합니다. 그룹을 함께 페이드하려면 보이는
각 자식의 불투명도를 애니메이션하세요. 백분율 위치는 Canvas 크기를 기준으로 합니다.
부모가 없는 애니메이션 도형의 제작 자세는 Canvas 안에 두세요. 부모에 연결된 도형은
밖에서 진입할 수 있습니다. 부모 연결은 Shape와 Null에 사용할 수 있습니다.

## Lottie 텍스트 외곽선 { #lottie-outlined-text }

`quickthumb[lottie]`를 설치하면 정적인 한 줄 인쇄 가능 ASCII 제목을 벡터 외곽선으로
넣을 수 있습니다. 뷰어에 글꼴이 필요 없으며, 제목을 바꾸려면 원본을 수정해 다시 내보내세요.
[텍스트 예제](https://github.com/sjquant/quickthumb/blob/main/examples/lottie_text.py)처럼 로컬 외곽선 글꼴,
불투명 텍스트 색상, 여러 글자에 0이 아닌 `letter_spacing`을 사용하세요. 반투명 표현은
레이어의 `opacity`로 조절합니다. 제목은 회전·부모 연결 없이 배치하세요. 움직이는 글자나
한글을 포함한 다국어 타이포그래피에는 [영상 출력](../output-guide.md)을 선택하세요.

## 내보내기 전 호환성 확인 { #check-compatibility-before-exporting }

기존 디자인을 가져올 때는 먼저 `canvas.validate_export("lottie")`를 호출하세요.
그라디언트·이미지·효과·텍스트 애니메이션 등 바꿔야 할 레이어와 필드를 알려 줍니다.
내보내기도 샘플 기하 구조와 정밀도를 쓰기 전에 검사하므로, 거부된 내보내기는 기존 파일을 보존합니다.

벡터 Lottie에는 위 예제의 아트워크와 트랙을 사용하세요. 이미지·효과 등도 그대로 유지하려면
[영상 출력](../output-guide.md)을 선택하세요.

정지 버전은 양수 `hold`와 `ExportPolicy(reduced_motion=True)`로 만드세요.
애니메이션의 마지막 자세가 아니라 제작한 아트워크를 내보냅니다.
