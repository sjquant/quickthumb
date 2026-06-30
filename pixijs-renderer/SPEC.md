# PixiJS Deck Renderer — 요구사항 명세 (v1)

> **상태**: P1 정적 렌더 코어 **구현·검증 완료**. 나머지(텍스트/애니메이션/전환)는 단계별 진행.
> 구현·실행 방법은 [`README.md`](./README.md) 참고.
>
> **검증된 것**: background(solid/linear/radial gradient), shape(rectangle/ellipse/
> pill/triangle/star/polygon, opacity·9방향 align·rotation), outline 레이어가
> quickthumb PIL 출력과 픽셀 일치(§13 기준 mean abs diff < 1.0/255, solid·outline은
> byte-exact). 헤드리스 Chromium 렌더 → PNG 픽셀 diff 하니스가 9개 픽스처에서 그린.
>
> **충실도 기준 검증**: §4 충실도 규칙과 §3 IR 계약은 quickthumb 소스(`a359d9c`)와
> 대조 확인했고, 그라데이션 수식은 PIL 출력에서 **경험적으로 역추출**해 고정했다
> (`src/core/gradient.ts`). 주요 확인 사항은 각 절의 *(소스 확인)* 주석 참고.

## 0. 목적 / 철학
- quickthumb(파이썬) 덱을 웹에서 GPU로 렌더링하는 새 렌더러를 PixiJS v8로 구축한다.
- 기존 quickthumb HTML export(DOM/CSS + JS 타임라인)는 그대로 유지한다. 이건 별도/대체 백엔드다.
- Figma 모델을 따른다: 브라우저 DOM 렌더러에 의존하지 않고 캔버스 1장(WebGL2/WebGPU)에 직접 그린다.
  → 머신 간 일관성 + CSS로 불가능한 셰이더 이펙트.
- 핵심 자산: quickthumb는 이미 장면을 JSON IR로 내보낸다(`Canvas.to_json()`, `Deck.to_json()`).
  새 렌더러는 "이 IR을 소비하는 GPU 백엔드"다. 스키마를 새로 만들지 말 것.

## 1. 결정해야 할 최상위 선택 (먼저 못박기)
- **[DECISION-1] 충실도 기준 — 채택: (b) + PIL 수식 재현**:
    (a) quickthumb PIL 래스터 출력과 픽셀 일치를 목표로 한다(PNG/PPTX와 비교 대상), 또는
    (b) 새 렌더러가 자체 source-of-truth가 된다(Figma처럼, 다른 포맷과 다를 수 있음).
  → **(b)로 가되 "도형/그라데이션/그림자 수식은 PIL을 재현", "텍스트는 SDF로 고품질·크리스프"**.
  현재 구현은 도형/그라데이션/배경/outline에서 PIL과 mean<1/255로 일치함을 검증(§13). 글자만
  byte-identical을 포기하고 나머지는 일치. (a)가 꼭 필요하면 §6의 PIL-bake 경로 사용.
- **[DECISION-2] 텍스트 전략 — 권장: A(MSDF) 주, B(PIL-bake) 옵션 (미구현)**:
  SDF/MSDF(크리스프·GPU 이펙트) vs PIL-baked 텍스처(픽셀 일치). 텍스트 슬라이스에서 확정. §6 참고.
- **[DECISION-3] 타겟 — 채택: WebGPU 우선 + WebGL2 폴백 (PixiJS v8)**.
  런타임은 Pixi 기본 선호(WebGPU)를 따르고, 결정적 픽셀 diff 하니스는 WebGL로 고정 실행.

## 2. 기술 스택
- 렌더러: PixiJS v8 (WebGPU 백엔드 우선, WebGL2 폴백)
- 언어/빌드: TypeScript + Vite, 출력은 단일 자기완결 번들(+ assets) 또는 단일 HTML
- 셰이더: WGSL(WebGPU) / GLSL(WebGL2) — Pixi Filter/Mesh/Shader API
- 텍스트: msdf-atlas-gen 또는 troika-style MSDF (DECISION-2가 SDF인 경우)
- 전환 셰이더: gl-transitions 포팅 + 커스텀
- 테스트: 정적 슬라이드 스냅샷을 PNG와 픽셀 diff(§13)

## 3. 입력 계약 (quickthumb JSON IR)

*(소스 확인: `Deck.to_json()` @ `deck.py:290`, `Canvas.to_json()` @ `canvas.py:585`)*

- 진입점: **Deck JSON** = `{ width?, height?, theme?, transition?, slides: [CanvasModel + transition?...] }`
  - `width`/`height`는 덱에 명시적 크기가 있을 때만 포함된다.
  - `transition`은 덱 전역 기본 전환. 슬라이드별 `transition` override가 slide dict에 직접 붙는다.
- **CanvasModel** = `{ width, height, layers: [Layer...] }`
- 좌표/단위:
  - 캔버스는 고정 픽셀 크기(예: 1280×720). 전 레이어 이 좌표계 기준.
  - position 값은 px(number) 또는 `"%"` 문자열. x는 width 기준, y는 height 기준. 음수 % 허용.
    *(소스 확인: `parse_coordinate` @ `_base.py:38` — `int(dimension * percentage / 100)`)*
  - align: 9방향 enum(`"center"`,`"top-left"`,…) 또는 (horizontal, vertical) 튜플.
    도형/이미지/텍스트의 앵커를 정함(아래 align 규칙).
    *(소스 확인: `Align` enum @ `models.py:78` — vertical은 `top`/`middle`/`bottom`)*
  - rotation: degrees. 회전 시 확장 바운딩박스 계산 필요(expanded rotation size).
    *(소스 확인: `expanded_rotation_size` @ `_base.py:102` — 4x 슈퍼샘플 회전 후 다운스케일, 직각은 transpose)*
- Layer 종류 (discriminator = `"type"`) — *(소스 확인: `LayerType` union @ `models.py:815`)*:
  - **background**: color(hex/tuple) | gradient(Linear|Radial) | image, opacity, blend_mode, fit, effects[Filter|Grain]
  - **text**: content(str | TextPart[]), font, size, color, fill(Linear|Radial|TextFillImage),
          position, align, bold, italic, weight, max_width, line_height, letter_spacing,
          auto_scale, rotation, opacity, effects[Stroke|Shadow|Glow|Background], animation
  - **outline**: width, color, offset, opacity (캔버스 안쪽으로 그려지는 테두리, box-sizing border-box 개념)
  - **shape**: shape(rectangle|ellipse|pill|triangle|star|polygon), position, width, height, color,
           border_radius, opacity, rotation, align, points(폴리곤 0..1 정규화), star_points,
           inner_radius, effects[Stroke|Shadow|Glow], animation
  - **image**: path, position, width?, height?, opacity, rotation, remove_background, align,
           border_radius, fit(cover|contain|fill), blend_mode, effects[Stroke|Shadow|Glow|Filter|Grain], animation
  - **svg**: path, position, width?, height?, opacity, rotation, align, blend_mode, effects, animation
  - **group**: direction(row|column), gap, padding, position, align, item_align(start|center|end),
           children[자식 레이어들 — position 금지, 그룹이 배치], animation
    * 그룹은 자식들을 flex처럼 배치. 자식 위치는 그룹이 계산.
      *(소스 확인: `GroupLayer.validate_children` @ `models.py:731` — children은 position을 설정할 수 없고,
      image/svg/shape 자식은 `(0,0)`으로 강제된다)*
- **TextPart**(리치 텍스트 조각): text, color?, fill?, effects?, size?, bold?, italic?, weight?,
  line_height?, letter_spacing?, font?

## 4. 렌더링 충실도 규칙 (PIL = 기준; 반드시 셰이더에서 재현)

### 4.1 Linear Gradient (가장 중요, 흔히 틀림)

*(소스 확인: `create_linear_gradient` @ `_effects.py:216`)*

- PIL은 0→1 램프를 박스의 "대각선 길이" `D = ceil(sqrt(w²+h²))`에 걸쳐 만들고, 박스 중앙에 정렬한 뒤 crop한다.
  → 박스는 색 범위의 "가운데 일부"만 보여준다. **절대 0%~100% 전체를 박스에 펴지 말 것.**
  (구현 디테일: `Image.linear_gradient("L")`는 세로 램프 → `diagonal×diagonal`로 resize →
  `rotate(90 - angle)` (PIL은 반시계) → 중앙 `width×height` crop.)
- 방향: angle 0 = 가로(왼→오). 화면 좌표(x 오른쪽+, y 아래+). 방향벡터 d=(cosθ, sinθ).
- 어떤 점 p의 그라데이션 값 g = 0.5 + (signed projection of (p − boxCenter) onto d) / D.
- stops는 (color, pos∈[0,1]). pos는 위 g 공간의 위치.
  *(소스 확인: `_create_gradient_lut` @ `_effects.py:169` — 256-entry LUT, stops 정렬, 첫/끝 stop 밖은 clamp,
  alpha 채널 보간 포함)*
- 멀티라인 텍스트: 그라데이션은 "텍스트 블록 전체"에 연속으로 걸린다(라인마다 리셋 금지).
  라인/런 단위로 그릴 땐, 그 런 박스가 블록 그라데이션의 어느 슬라이스인지 계산해 그 슬라이스만 그린다.
- 구현: 프래그먼트 셰이더에서 위 g를 직접 계산(uniform: boxCenter, dir, D, stops) → LUT 보간.

### 4.2 Radial Gradient

*(소스 확인: `create_radial_gradient` @ `_effects.py:243`)*

- center(0..1 분수). radius = 네 꼭짓점까지 거리 중 max.
- stops는 0..1 = 중심→radius. 셰이더에서 dist/radius로 LUT.

### 4.3 Shadow

*(소스 확인: `_text.py:1416` `GaussianBlur(radius=shadow.blur_radius)`)*

- PIL: 텍스트/도형을 그림자색으로 그리고 offset 후 GaussianBlur(radius=blur_radius), 합성.
- blur_radius == 가우시안 표준편차 σ. (CSS는 blur=2σ라 DOM export에선 ×2 했지만, 셰이더에선 σ 그대로.)
- 셰이더: separable Gaussian, σ = blur_radius. 색 alpha 보존.

### 4.4 Glow

*(소스 확인: `_text.py:1293` `expansion = max(1, glow.radius // 2)`, `stroke_width = expansion*2`,
`GaussianBlur(radius=glow.radius)`, 이후 opacity 곱)*

- PIL: 글리프/도형 마스크를 팽창(expansion=radius//2, stroke_width=expansion*2)한 뒤 GaussianBlur(σ=radius),
  그 후 opacity 곱. 즉 "dilate then blur then multiply".
- 셰이더: dilation(radius/2) + Gaussian(σ=radius) + 알파*opacity.

### 4.5 Stroke
- width px, color. 텍스트는 외곽선(paint-order: stroke fill). 도형은 외곽 테두리.

### 4.6 Filter (이미지/배경)

*(소스 확인: `apply_filter` @ `_effects.py:70` — brightness → blur → contrast → saturation 순서.
blur는 RGB만 가우시안, alpha 원본 보존: `_apply_blur` @ `_effects.py:55`)*

- blur(px, 가우시안 σ=blur), brightness(곱), contrast, saturation. 셰이더 체인.

### 4.7 Grain (필름 그레인)

*(소스 확인: `Grain` @ `models.py:271`, `_blend_grain` @ `_effects.py:125`. blend_mode는
`overlay|screen|multiply|normal`만 허용, 기본값 `overlay`, monochrome 기본 `True`)*

- intensity(0..1), monochrome, blend_mode(overlay|screen|multiply|normal), opacity, seed.
- seed 고정 시 결정적 노이즈(`random.Random(seed).randbytes`). 셰이더 노이즈 + blend.

### 4.8 Blend modes

*(소스 확인: `BlendMode` @ `models.py:63`, `apply_blend_mode` @ `_effects.py:300`)*

- multiply, overlay, screen, darken, lighten, normal. 레이어 합성 시 적용.

### 4.9 도형 지오메트리
- rectangle(+border_radius), ellipse, pill(=min(w,h)/2 radius), triangle, star(star_points, inner_radius),
  polygon(points 0..1 정규화). 삼각형/별/폴리곤은 정규화 좌표 → 박스에 매핑 후 테셀레이션.
  *(소스 확인: `ShapeLayer` @ `models.py:604` — `inner_radius`는 0<x<1, `star_points`≥3, `points`는 0..1 정규화 ≥3개)*
- outline 레이어: 캔버스 안쪽 offset, 두께 width, 안쪽으로 그림(box-sizing border-box 동일).

### 4.10 align / 회전
- align 9방향으로 레이어 박스의 앵커 결정 후 position에 배치.
  *(소스 확인: `apply_alignment` @ `_base.py:73` — center는 `x - w//2`, right는 `x - w`; middle/bottom 동일)*
- rotation은 박스 중심 기준. 회전 후 확장 바운딩박스로 배치 보정.

## 5. 좌표/스케일 (반응형)
- 고정 크기 stage를 뷰포트에 "하나의 단위"로 스케일(aspect 유지, contain). 절대 reflow 금지.
- WebGPU/WebGL이라 devicePixelRatio 처리 필수(레티나 선명도). 렌더 타깃 해상도 = stageSize × min(fitScale, cap) × dpr.
- 리사이즈는 ResizeObserver 하나만(이중 핸들러 금지).

## 6. 텍스트 렌더링 (DECISION-2)

### 옵션 A — SDF/MSDF (추천: 크리스프 + GPU 이펙트, Figma류)
- 폰트 파일에서 MSDF 아틀라스 생성(msdf-atlas-gen). 셰이핑은 HarfBuzz(웹: harfbuzzjs)로
  kerning/ligature 적용(PIL이 raqm/HarfBuzz라 셰이핑 규칙 동일하게 맞춤).
- 장점: 무한 확대 크리스프, per-glyph 셰이더 이펙트(그라데이션 fill, 글로우, 디졸브).
- 단점: PIL과 byte-identical은 아님(안티에일리어싱 방식 차이). DECISION-1=(b)면 OK.
- 메트릭: ascent/descent, line_height = multiplier × (ascent+descent), letter_spacing px,
  baseline 배치. weight/bold/italic 베리언트.
  *(소스 확인: `DEFAULT_LINE_HEIGHT_MULTIPLIER = 1.2`, `LINE_HEIGHT_REFERENCE = "Aby"` @ `_base.py:13`)*

### 옵션 B — PIL-baked 텍스처 (픽셀 일치 필요할 때)
- 파이썬 측에서 각 텍스트 런/라인을 FreeType로 2× DPI 렌더 → 텍스처 아틀라스 + 위치 JSON 출력.
- 웹은 그 텍스처를 스프라이트로 합성. 글자 픽셀 = PNG와 동일.
- 단점: 확대 시 흐려짐(2× 한도), 텍스트 선택 불가, 파일 큼.
- 절충: 정적 본문은 B(정확), 큰 헤드라인 애니메이션은 A(크리스프) 혼용 가능.

### 공통
- 텍스트 fill: solid color | LinearGradient | RadialGradient | image(TextFillImage). 그라데이션은 §4.1 규칙.
- 텍스트 effects: Stroke, Shadow, Glow, Background(텍스트 뒤 박스: color, padding, border_radius, opacity).
  *(소스 확인: `TextEffect` union @ `models.py:294`)*
- max_width 줄바꿈 + auto_scale(맞을 때까지 축소). 멀티라인 line_height. 회전.
  *(소스 확인: `auto_scale`는 `max_width` 필수 @ `models.py:520`)*
- 접근성: 가능하면 보이지 않는 DOM 텍스트 레이어를 겹쳐 셀렉션/스크린리더 지원(선택).

## 7. 레이어별 애니메이션 (entrance/exit)

*(소스 확인: `Animation` union @ `models.py:396`, `_AnimationBase` @ `models.py:311`.
주의: 레이어 애니메이션은 현재 PPTX 출력에서만 동작 — raster/SVG/PDF는 무시. 새 렌더러는 이 IR을 살려 웹에서 재생한다.)*

- 효과: Appear, Fade, Wipe(up/down/left/right), Box(in/out), Blinds(orientation),
  Checkerboard(across/down), Circle, Diamond, Dissolve, Wheel(spokes).
  - 가능한 건 셰이더로 정확히(clip 기반 reveal: wipe=inset, circle=원, box=중앙확장, diamond=마름모,
    wheel=각도 sweep, blinds/checker/dissolve=마스크). CSS보다 자유로움.
- 타이밍 필드: animate(entrance|exit), duration(s, 기본 0.5), delay(s), trigger(on_click|with_previous|after_previous).
- 시퀀싱 규칙(quickthumb 동일):
  - entrance 요소는 시작 시 숨김.
  - on_click: 클릭으로 진행. with_previous: 직전 것과 동시. after_previous: 직전 끝나면 자동 연쇄.
  - 한 그룹(= 리드 + 뒤따르는 with_previous들)을 동시에 재생, 그 후 after_previous 체인 자동 진행.
- exit는 같은 효과를 역방향으로.
- 정착(settle): 애니메이션 끝나면 원래 상태 복원(특히 clip 계열은 원래 클립 유지).

## 8. 슬라이드 전환 (덱)

*(소스 확인: `Transition` union @ `transitions.py:166`. 전환도 현재 PPTX 전용 — 새 렌더러가 웹에서 살린다.)*

### 8.1 두-슬라이드 모델 (이전 슬라이드가 사라지는 어색함 금지)
- 나가는 슬라이드를 전환 동안 화면에 유지:
  - cover/fade/zoom/wipe/clip류: 나가는 슬라이드는 "정적으로 아래"에 두고 들어오는 게 위에서 연출.
  - push/uncover: push=둘 다 이동(옛 슬라이드 밀려나며 새 슬라이드 진입), uncover=옛 슬라이드가 비켜 새 슬라이드 노출.
  - z-order는 효과별로. cut=즉시 교체(애니메이션 없음).
- 방향: PowerPoint 명명 기준. "left" push = 콘텐츠가 왼쪽으로, 새 슬라이드는 오른쪽에서 진입.

### 8.2 전환 효과 (IR 매핑)
- Cut, Fade, Dissolve, Newsflash, Wedge, Circle, Diamond, Random, Wheel(spokes),
  Push(dir), Wipe(dir), Cover(dir), Uncover(dir), Zoom(in/out), Split(orientation,dir),
  Blinds(orientation), Checker(orientation), Comb(orientation).
- 타이밍: duration(기본 1.0), advance_on_click(기본 true), advance_after(자동 진행 초, nullable).

### 8.3 셰이더 전환 (WebGL의 본 목적)
- 나가는/들어오는 슬라이드를 각각 RenderTexture로 떠서, 두 텍스처 사이를 셰이더로 보간.
- gl-transitions 포팅: ripple, morph, burn, glitch, fold, displacement, page-curl 등.
- 새 전환 타입을 IR에 확장 가능하게(예: transition effect="shader", name="ripple", params{}).

## 9. "쩌는" 웹 전용 확장 (CSS/PPTX 불가)
- Bloom/글로우 포스트프로세스, 색수차, 비네팅, 필름그레인 포스트.
- 3D 트랜스폼 전환(카드 플립, 큐브, 원근 push), parallax(레이어 깊이 + 포인터/스크롤 반응).
- 제너러티브 배경: 셰이더 그라데이션 메시, 유체/노이즈, 입자.
- 텍스트 per-glyph 연출(글자별 stagger, 디스플레이스, 메탈/홀로 머티리얼).
- 모션 블러, 이징 커브 커스텀, 물리 기반 스프링 entrance.
- 전부 GPU 타임라인(uniform 구동), 메인스레드 재draw 금지.

## 10. 네비게이션 / 입력 / 런타임
- 진행: 클릭 / ArrowRight / Space = 다음(현재 슬라이드 애니메이션 먼저 소진 후 다음 슬라이드).
- 뒤로: ArrowLeft. (옵션: 슬라이드 점프, 진행바, 발표자 노트, 풀스크린, 자동재생 advance_after.)
- URL 해시로 슬라이드 인덱스 동기화(딥링크).
- 슬라이드 진입 시 해당 슬라이드 타임라인 리셋 후 재생.

## 11. 성능 요구
- 전환/이펙트는 GPU 합성(텍스처+셰이더). 60fps 목표(고사양 120).
- 레이어/텍스트 아틀라스는 1회 업로드 후 재사용. 매 프레임 재업로드 금지.
- will-change식 레이어 승격 개념 = Pixi RenderGroup/cacheAsTexture 적절히.
- 폰트/아틀라스/이미지 프리로드 후 첫 슬라이드 렌더(FOUC 방지).
- 유휴 시 렌더 루프 정지(애니메이션 없을 때 rAF 중단).

## 12. 패키징 / 출력
- 산출물: (a) 단일 자기완결 HTML(+inline assets) 또는 (b) JS 위젯 + assets 폴더.
- 입력: quickthumb Deck JSON + 폰트/이미지 assets(또는 baked 아틀라스).
- 임베드 가능(iframe/웹컴포넌트). API: `new Deck(el, json, opts).render() / .next() / .prev() / .goto(i)`.
- SSR/정적 호스팅 가능(서버 불필요; baked 아틀라스는 빌드시 생성).

## 13. 정밀도 / 수용 기준 (테스트)
- 정적 슬라이드를 캡처해 quickthumb PNG와 픽셀 diff.
  - 도형/그라데이션/그림자/배경: mean abs diff < 1.0 / 255 목표(셰이더로 PIL 수식 재현).
  - 텍스트: 옵션B면 거의 0; 옵션A면 글자 가장자리 차이 허용(지각 불가 수준).
- 전환/애니메이션: 시각 회귀(스냅샷 시퀀스) + 60fps 확인.
- 크로스 브라우저/머신 일관성(자체 렌더러라 동일해야 함).

## 14. 진단 (선택, quickthumb 동등)

*(소스 확인: `Diagnostic` @ `models.py:808`, 구현 `_diagnostics.py`)*

- off-canvas(화면 밖), tiny-text(너무 작은 글자), text-overflow(max_width 초과 단어),
  low-contrast(배경 대비 부족). 빌드/저작 단계 경고.

## 15. 단계별 로드맵
- **P0 (de-risk)**: PIL 스냅샷 2장 + Pixi 셰이더 전환 1개 + bloom 데모. "쩌는 느낌" 검증.
- **P1**: IR 소비 정적 렌더(도형/그라데이션/이미지/배경/effects) → PNG 픽셀 diff 통과.
- **P2**: 텍스트(DECISION-2 경로) + 레이어 entrance/exit 애니메이션 + 타임라인 시퀀싱.
- **P3**: 두-슬라이드 전환 모델 + 셰이더 전환 라이브러리.
- **P4**: 웹 전용 연출(bloom/parallax/3D/제너러티브) + 발표자 모드/오토플레이 + 패키징.

## 16. 참고 (quickthumb 소스, 충실도 기준)
- 모델/스키마: `quickthumb/models.py` (레이어, 효과, 애니메이션 enum)
- 전환 정의: `quickthumb/transitions.py`
- 그라데이션/블러 알고리즘: `quickthumb/_effects.py` (`create_linear_gradient` / `create_radial_gradient` / `_apply_blur`)
- 텍스트 레이아웃: `quickthumb/_export_base.py` (`compute_text_layout`), `quickthumb/_text.py`
- 정렬/좌표/회전: `quickthumb/_base.py` (`apply_alignment`, `parse_coordinate`, `expanded_rotation_size`)
- 기존 HTML 런타임(타임라인/전환 시퀀싱 참고): `quickthumb/_export_html.py`
- IR 출력: `Canvas.to_json()` (`canvas.py`) / `Deck.to_json()` (`deck.py`)

## 17. 결정사항
- **DECISION-1** — ✅ 채택: (b) 자체 source-of-truth + 도형/그라데이션/그림자 PIL 수식 재현 (§1, P1에서 검증).
- **DECISION-2** — ⏳ 권장 A(MSDF) 주 / B(PIL-bake) 옵션; 텍스트 슬라이스(P2)에서 확정.
- **DECISION-3** — ✅ 채택: WebGPU 우선 + WebGL2 폴백 (§1).
- ⏳ 편집 기능 필요 여부(뷰어 전용인지 / Figma식 에디터까지인지) — 스코프 크게 갈림. 미정.
- ⏳ 비디오/프레임 export 필요 여부(있으면 결정적 타임라인 + 오프스크린 렌더 설계 반영). 미정.

## 18. 구현 진행 현황 (로드맵 대비)
- ✅ **P1 코어(정적 렌더)**: background(solid/linear/radial), shape(전 종류 지오메트리·opacity·align·
  rotation), outline → PNG 픽셀 diff 통과(9/9, mean<1/255). 하니스: `test/run-visual.mjs`.
- ⏳ **P1 잔여**: image/svg 레이어, background image·blend_mode·fit, 도형/이미지 effects
  (Shadow/Glow/Stroke/Filter/Grain) — §4.3~4.8 수식은 소스 확인 완료, 셰이더 구현 대기.
- ⏳ **P2**: 텍스트(DECISION-2), 레이어 entrance/exit 애니메이션, 타임라인 시퀀싱.
- ⏳ **P3/P4**: 두-슬라이드 전환 모델·셰이더 전환, 웹 전용 연출, 패키징/뷰어 API.
