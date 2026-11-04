---
description: quickthumb로 오디오 시작점과 RMS 음량을 분석하고 타이밍 기준점과 크기 트랙을 재사용 가능한 애니메이션 JSON에 기록합니다.
---

# 오디오 반응형 제작 { #audio-reactive-authoring }

`quickthumb.audio.analyze_audio(path, cache_dir=None)`는 제작 전에 로컬 오디오 소스를 분석하며 FFmpeg가 필요합니다.
일시적인 소리 시작 시각과 소스 기준 RMS 진폭이 담긴 검증된 `AudioAnalysis` 레코드를 반환합니다.
시작점은 음량이 급격히 커지는 지점이며, 음악의 박자 격자나 템포 추정값이 **아닙니다**.

시작점을 일반 숫자형 `TimingSpec.start`로 사용하세요.
그러면 표본 추출, JSON 복원, 워커 렌더링 시 사운드트랙 옵션에 의존하지 않습니다.

```python
from quickthumb import AnimationSpec, ColorTrack, KeyframeSpec, TimingSpec
from quickthumb.audio import analyze_audio

analysis = analyze_audio("music.wav")
if analysis.onsets:
    motion = AnimationSpec.timeline(
        ColorTrack(keyframes=[
            KeyframeSpec(time=0, value="#102030"),
            KeyframeSpec(time=0.2, value="#42CEB7"),
        ]),
        timing=TimingSpec(start=analysis.onsets[0], duration=0.2),
        easing="linear",
    )
```

레이어의 `animation=`에 `motion`을 연결합니다.
실행 가능한 [`examples/audio_onsets.py`](https://github.com/sjquant/quickthumb/blob/main/examples/audio_onsets.py)는 장면, 분석 사이드카, 정규 JSON, 같은 소스를 사운드트랙으로 사용하는 MP4를 만듭니다.
숫자로 기록된 모션은 `inspect_motion()`으로도 검사할 수 있으며 각 출력 대상의 기존 색상 트랙 지원이나 명시된 대체 표현을 사용합니다.
HTML 프레젠테이션은 사운드트랙을 재생하지 않으며 GIF에는 소리가 없습니다.
타이밍을 미리 기록했다는 사실이 어느 형식에서든 실시간 오디오 동기화를 보장하지는 않습니다.

## 소스 시계와 RMS { #source-clock-and-rms }

모든 시각은 첫 번째로 디코딩된 오디오 스트림의 시작부터 센 초 단위 값입니다.
값은 소스 진폭을 나타냅니다. 무음의 RMS는 0이며 시작점이 없습니다.
시작점이 없는 트랙도 있으므로 인덱스로 접근하기 전에 `onsets`를 확인하세요.

??? info "분석 해상도와 시작점 감지"
    분석은 8 kHz로 재표본화한 모노 오디오와 연속된 160개 표본(20 ms) 구간을 사용합니다.
    `rms[i]`는 `i * 0.02`에 시작하는 구간의 선형 RMS 진폭입니다. 마지막 구간은 더 짧을 수 있습니다.
    트랙별로 정규화한 값이 아닌 소스 진폭이며 무음은 RMS가 0이고 시작점이 없습니다.

    버전이 명시된 감지기는 RMS가 0.01보다 크고 직전 구간과 이전 10개 구간 평균 모두의 두 배를 넘는 어택을 요구하며, 기준점 사이에는 최소 100 ms 간격을 둡니다.
    기준 과도 신호는 한 20 ms 구간 이내에서 검증합니다. 점진적인 어택이나 음악의 엇박은 기준점을 만들지 않을 수 있습니다.
    시작점 인덱스가 없을 수 있으므로 접근 전에 `onsets`를 확인하세요.

내보내기 게인, 사운드트랙 반복·페이드아웃, 내레이션, 다른 믹싱 오디오는 이 소스 분석을 바꾸지 않습니다.
Deck 타이밍은 슬라이드 로컬이므로 사운드트랙 시작점을 의도한 슬라이드의 시계로 직접 변환해야 합니다.
내보내기 옵션을 바꿔도 기준점을 자동으로 반복하거나 옮기지 않습니다.

## 음량에 따른 크기 조절 { #loudness-driven-scale }

`AudioAnalysis.scale_track(min_scale=1.0, max_scale=1.15)`는 일반 `ScaleTrack`을 반환합니다.
이를 `AnimationSpec.timeline()`에 연결하세요. 저장된 RMS를 모션으로 바꿀 때 사운드트랙이나 분석기를 다시 참조하지 않습니다.

```python
pulse = AnimationSpec.timeline(
    analysis.scale_track(min_scale=1.0, max_scale=1.4)
)
```

이 도우미는 각 RMS 진폭을 분석 내 가장 큰 구간의 진폭으로 나눈 뒤 요청한 크기 범위에 대응시킵니다.
무음은 `min_scale`, 최댓값은 `max_scale`에 대응하며 전체가 무음이면 `min_scale`을 유지합니다.
소스 기준 정규화이므로 조용한 녹음과 더 큰 음량의 복사본이 같은 반응을 만들 수 있으며 내보내기 음량의 영향을 받지 않습니다.
양 끝값은 유한한 양수여야 하며 `max_scale >= min_scale`이어야 합니다.

각 키프레임은 마지막의 짧은 구간을 포함해 자신의 20 ms 구간 동안 값을 유지합니다. 어택 전에는 보간하지 않습니다.
정확한 소스 종료 시각에 키프레임 하나를 더해 `min_scale`로 복귀하므로 정착 유지 구간이나 다음 슬라이드에 마지막 큰 펄스가 남지 않습니다.
추론되는 애니메이션 길이는 `analysis.duration`과 같습니다.
`TimingSpec`을 명시하면 이 전체 길이를 허용해야 하며, `start`는 소스를 자르는 대신 소스 시계 전체를 이동시킵니다.

생성된 트랙은 일반적인 정규 JSON입니다. `sample()`, `inspect_motion()`, 워커와 내보내기는 기존 크기 트랙 경로로 이를 처리합니다.
모션 줄이기 설정은 이 트랙을 억제하고 제작한 정적 도형을 유지합니다.
HTML/PPTX는 선언된 크기 조절 지원 범위를 따르며 실시간 사운드트랙 재생이나 동기화가 추가되지는 않습니다.
실행 예제는 시작점에 따른 색상 변화와 음량에 따른 크기 펄스를 소스 오디오와 함께 MP4에 담습니다.

## 저장과 재사용 { #store-and-reuse }

```python
from pathlib import Path
from quickthumb.audio import AudioAnalysis

Path("analysis.json").write_text(analysis.model_dump_json(), encoding="utf-8")
stored = AudioAnalysis.model_validate_json(Path("analysis.json").read_text())
```

레코드에는 스키마·알고리즘 버전, 소스 SHA-256, FFmpeg 버전, 표본 추출 매개변수, 길이, 정렬된 시작점과 RMS 구간이 포함됩니다.
JSON 스키마는 `AudioAnalysis.model_json_schema()`로 얻습니다.
사이드카와 문서 JSON에 기록한 모션은 소스 오디오나 FFmpeg 없이 불러와 표본을 추출할 수 있습니다.
오디오를 내보낼 때는 여전히 소스와 일반적인 미디어 도구가 필요합니다.

`analyze_audio` 자체에는 FFmpeg가 필요합니다. `QUICKTHUMB_FFMPEG`로 바이너리를 지정할 수 있습니다.
소스 바이트, 알고리즘, 고정 매개변수, FFmpeg 버전을 식별자로 사용해 시스템 임시 디렉터리의 `quickthumb-audio` 폴더 또는 지정한 `cache_dir`에 레코드를 캐시합니다.
캐시 쓰기는 원자적입니다. 소스 바이트나 디코더·알고리즘 버전이 바뀌면 새 항목을 만들며, 항목이 손상되면 제거할 파일을 알려 주는 오류를 발생시킵니다.
축출될 수 있는 캐시에 의존하기보다 사이드카를 보관해 디코더 업그레이드 후에도 제작 결과를 고정하세요.

입력은 64 MiB와 디코딩된 오디오 10분으로 제한됩니다. 분석 제한 시간은 60초입니다.
파일이 없거나 오디오가 아닌 경우, FFmpeg 필터가 지원되지 않는 경우, 제한을 넘긴 경우에는 조치 가능한 오류로 실패하며 분석을 조용히 잘라내지 않습니다.
이 제한은 렌더링 길이가 아닌 제작 작업의 범위를 제한합니다.
