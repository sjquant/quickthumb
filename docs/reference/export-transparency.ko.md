---
description: quickthumb에서 투명 동영상을 내보내는 방법과 코덱·알파 지원의 한계를 설명합니다.
---

# 투명 동영상 { #transparent-video }

[내보내기 레퍼런스](../exports.md) · [출력 형식 선택](../output-guide.md)

## 투명 WebM { #transparent-webm }

VP9 WebM은 `VideoOptions(transparent=True)` 또는 `Canvas.to_webm()`, `Deck.to_webm()`의 키워드 전용 `transparent=True`로 알파를 보존할 수 있습니다.
기본값은 `False`이며 기존 불투명 출력은 매트와 인코더 설정을 유지합니다.
레이어나 모션에 저장하는 속성이 아니라 내보낼 때 적용하는 옵션입니다. 따라서 Canvas/Deck JSON이나 `inspect_motion()` 결과에는 포함되지 않습니다.
`VideoOptions.model_validate_json()`과 모델 JSON 스키마는 이 엄격한 불리언 옵션을 제공합니다.
`validate_export()`는 계속 문서 모션을 설명하며 `render()`는 지원하지 않는 출력 형식의 투명 옵션을 거부합니다.

```python
canvas.render("overlay.webm", animation=VideoOptions(transparent=True))
deck.render("overlay.webm", animation=VideoOptions(transparent=True, render_quality="high", workers=2))
webm_bytes = canvas.to_webm(transparent=True)
options = VideoOptions.model_validate_json('{"transparent": true, "fps": 24}')
```

내보내기 매트만 생략합니다.
제작한 배경은 계속 보이고 빈 영역과 크기가 섞인 슬라이드의 레터박스는 투명하게 유지되며, 0번 슬라이드 전환은 투명 상태에서 시작합니다.
페이드·마스크 전환은 미리 곱한 색상을 보간하고 덮기·크기 조절 슬라이드는 source-over 알파로 합성합니다.
키가 있는 Morph는 크기가 다른 슬라이드를 첫 슬라이드의 출력 공간에 정규화한 뒤 위치, 크기, 반투명 픽셀을 보간합니다.
기존 부모·자막 Morph 대체 표현 제한은 그대로 적용됩니다.

두 합성 품질 모드, spawn 워커, 사운드트랙, Deck 내레이션은 투명 WebM에서도 동작합니다.
인코더는 알파 평면을 보호하기 위해 무손실 VP9 코딩으로 RGBA를 VP9 `yuva420p`에 스트리밍합니다.
RGBA에서 YUV로 변환하면서 디코딩된 알파가 8비트 한 단계 바뀔 수 있습니다.
RGB는 4:2:0 색차 서브샘플링을 사용하므로 원본 색상 픽셀은 무손실이 아닙니다.
불투명 WebM보다 파일이 클 수 있습니다. 기존의 제한된 프레임 배치와 원자적인 목적지 대체는 유지됩니다.
투명 전환은 정확한 미리 곱한 혼합을 위해 임시 부동소수점 평면을 사용하므로 프레임 크기와 워커 수에 따라 메모리가 늘어납니다.
MP4, GIF, 문서·래스터 출력은 목적지에 쓰기 전에 이 동영상 옵션을 거부합니다.
PNG 애니메이션 시퀀스에는 별도 [`export_image_sequence()` API](export-frames.md#image-sequences)를 사용합니다.

VP9 WebM 알파를 지원하는 플레이어나 편집기를 사용하세요.
FFmpeg로 실제 알파 평면을 검사하려면 입력 **앞에** libvpx 디코더를 지정하세요.

```bash
ffmpeg -c:v libvpx-vp9 -i overlay.webm -frames:v 1 -pix_fmt rgba frame.png
```

기본 VP9 디코더는 색상만 보고하거나 디코딩할 수 있습니다.
`alpha_mode` 값이 있다고 해서 투명도가 제대로 보존되었다고 단정할 수는 없습니다.
회귀 테스트는 libvpx로 RGBA를 디코딩하고 투명·반투명·불투명 픽셀을 비교합니다.
제작한 반투명 패널과 투명한 주변부가 있는 오버레이는 `examples/transparent_lower_third.py`를 참고하세요.

## ProRes 4444 MOV { #prores-4444-mov }

Canvas와 Deck은 FFmpeg의 `prores_ks` 인코더를 사용해 고정 ProRes 4444 프로필의 `.mov`를 내보낼 수 있습니다.
MOV는 Deck 전환과 내레이션을 포함한 애니메이션 타임라인을 항상 재생합니다.
`transparent`는 WebM과 같은 엄격한 불리언이며 기본값은 `False`입니다.
일반 MOV는 매트에 합성하고 알파를 선택하면 그 매트만 생략합니다.
제작한 배경, 레터박스, 전환, 품질 모드, 워커는 위 투명 WebM 동작을 따릅니다.

```python
canvas.render("overlay.mov", animation=VideoOptions(transparent=True, fps=24))
deck.export("overlay.mov", animation=VideoOptions(transparent=True, render_quality="high", workers=2))
mov_bytes = canvas.to_mov(hold=2.0, transparent=True)
mov_bytes = deck.to_mov(hold=2.0, transparent=True, soundtrack="music.wav")
```

MOV는 홀수 너비·높이 프레임을 자르지 않고 정확한 캔버스 크기를 유지합니다.
투명 출력은 4:4:4 색차와 16비트 알파 코딩(`yuva444p10le`)으로 인코딩해 Final Cut Pro, DaVinci Resolve, Adobe Premiere 같은 전문 편집 도구에 표준적인 알파 충실도를 제공합니다.

사운드트랙, 슬라이드별 내레이션, 포함된 동영상 오디오는 애니메이션 MP4와 같은 예약·반복·채움·자르기 규칙으로 AAC에 인코딩합니다.
오디오 입력이 없는 Canvas MOV는 영상만 포함합니다.
Deck MOV는 내레이션 슬라이드가 없어도 기존 내레이션 작업 흐름의 무음 AAC 바닥 트랙을 유지합니다.
고정 코덱·프로필과 오디오 형식을 선택하는 API는 없습니다.
ProRes 파일은 WebM/MP4보다 훨씬 클 수 있고 ProRes 지원 플레이어나 편집기가 필요합니다.
인코딩 구간은 제한된 크기로 유지되며 전체 인코딩과 멀티플렉싱이 성공한 뒤에만 목적지를 대체합니다.
`prores_ks` 인코더가 없으면 렌더링 오류를 발생시키고 기존 목적지 파일은 보존합니다.
알파를 확인할 때는 프로필 메타데이터 대신 픽셀을 디코딩하세요.

```bash
ffmpeg -i overlay.mov -frames:v 1 -pix_fmt rgba frame.png
```

`examples/transparent_lower_third.py`는 WebM과 ProRes MOV 오버레이를 모두 기록합니다.
