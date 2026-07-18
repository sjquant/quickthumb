# quickthumb Examples

실제로 공개해도 어색하지 않은 결과물을 목표로 만든 end-to-end 예제 모음입니다.
영문과 한글 구성을 거의 절반씩 나누고, 하나의 템플릿을 색만 바꾸지 않고
매거진·인터뷰·데이터 저널·제품 필름처럼 서로 다른 편집 문법을 부여했습니다.

## Run an Example

저장소 루트에서 실행합니다.

```bash
uv run python examples/youtube_thumbnail_01.py
uv run python examples/youtube_thumbnail_02.py
uv run python examples/youtube_talking_head.py
uv run python examples/youtube_reaction.py
uv run python examples/youtube_tutorial_explainer.py
uv run python examples/instagram_news_card.py
uv run python examples/podcast_interview_promo.py
uv run python examples/shorts_cover_agent.py
uv run python examples/launch_announcement.py
uv run python examples/investor_deck.py
uv run python examples/product_hype_reel.py
```

## Design Direction

- 한국어 6종, 영어 5종으로 나눈 이중 언어 포트폴리오
- Noto Serif/Sans, Roboto, Pretendard를 콘텐츠 성격에 맞게 선택
- 과장된 스트로크 대신 여백·크롭·색면·서체 대비로 만드는 위계
- 시네마틱, 브루탈리스트, 에디토리얼, 제품 UI 등 포맷별 독립 아트 디렉션
- 장식보다 실제 콘텐츠와 매체의 맥락이 먼저 보이는 구성

## Included Examples

### `youtube_thumbnail_01.py`

Output: `youtube_thumbnail_01.png`

비 오는 서울의 퇴근길을 영문 패션 저널처럼 다룬 시네마틱 썸네일입니다. 이탤릭
세리프와 산세리프 메타데이터, 앰버 포인트를 결합해 일반적인 여행 영상과 구분합니다.

### `youtube_thumbnail_02.py`

Output: `youtube_thumbnail_02.png`

번아웃을 자극적으로 소비하지 않는 라이프스타일 에디토리얼입니다. 사진을 오른쪽
영역에만 배치하고 종이색 배경과 연결해, 제목·설명·브랜드 서명이 하나의 지면처럼
보이도록 구성합니다.

### `youtube_talking_head.py`

Output: `youtube_talking_head.png`

인물의 표정보다 인터뷰의 관점이 먼저 읽히는 메이커 인터뷰 커버입니다. 카드형
프레임, 절제된 인물 크롭, 이름표를 통해 일반적인 talking-head 포맷을 독립
비즈니스 매거진 문법으로 바꿉니다.

### `youtube_reaction.py`

Output: `youtube_reaction.png`

영문 독립 문화 저널을 닮은 코멘터리 카드입니다. 차가운 페리윙클 지면, 코랄 원형,
블랙 타이포그래피만으로 “모든 것이 왜 비슷해 보이는가”라는 질문을 시각화합니다.

### `youtube_tutorial_explainer.py`

Output: `youtube_tutorial_explainer.png`

영문 Python lab을 세 개의 세로 캡슐에 담은 커리큘럼형 썸네일입니다. 네이비와
애시드 라임을 사용해 반복 레이어도 교육 브랜드 캠페인처럼 보이게 합니다.

### `instagram_news_card.py`

Output: `instagram_news_card.png`

속보 배지 대신 맥락과 발행 주기를 강조하는 주간 뉴스 카드입니다. 상단 사진,
하단 기사 제목, 이슈 번호로 이어지는 전통적인 매거진 그리드를 1:1 화면에 적용합니다.

### `podcast_interview_promo.py`

Output: `podcast_interview_promo.png`

영문 독립 오디오 저널 프로모션입니다. 전용으로 제작해 저장소에 포함한 한국인 게스트
사진, 세리프 헤드라인, 원격 스튜디오 배경을 결합합니다.

### `shorts_cover_agent.py`

Output: `shorts_cover_agent.png`

Spec: `shorts_cover_agent.json`

AI 에이전트가 만든 JSON spec을 그대로 렌더하는 세로형 1분 에세이 커버입니다.
로컬 Pretendard 경로, `auto_scale`, 이미지 필터, 안전 영역 안의 긴 한국어 조판을
모두 JSON만으로 표현합니다.

### `launch_announcement.py`

Output: `launch_announcement.png`

Spec: `launch_announcement.json`

quickthumb 0.5 기능을 코발트와 애시드 라임의 영문 릴리스 포스터에 담습니다. 테마 토큰,
중첩된 auto-layout 그룹, 8각 별 도형, 고정 seed의 `Grain`, `canvas.diagnose()`를 사용합니다.
텍스트는 그룹이 배치하므로 카피가 바뀌어도 손으로 좌표를 다시 맞출 필요가 없습니다.

### `investor_deck.py`

Output: `investor_deck.html`, `investor_deck.pptx`

개인 금융 서비스 ‘모아’의 5장짜리 seed deck입니다. 어두운 미국식 SaaS 피치덱
대신 따뜻한 종이색, 한국어 중심의 서사, 실제 사용 행동을 강조하는 지표 카드로
구성했습니다. HTML 발표 모드, speaker note, 전환 애니메이션, 편집 가능한 PPTX를
동일한 소스에서 내보냅니다.

### `product_hype_reel.py`

Output: `product_hype_reel.gif`, `product_hype_reel.mp4`,
`product_hype_reel.webm`, `product_hype_reel.html`, `product_hype_reel.pptx`

피트니스 앱 ‘결’의 8장짜리 한국어 세로 제품 필름입니다. Reels 안전 영역,
Pretendard, 128 BPM에 맞춘 전환, 실시간 지표 카드, progress rail, 36초 길이의
사운드트랙을 하나의 `Deck`으로 구성합니다. 한 포맷의 선택 렌더러가 없어도 나머지
포맷을 계속 내보내는 graceful fallback도 포함합니다.

## Assets and Fonts

정적 예제는 `assets/fonts`의 Pretendard, Noto, Roboto를 파일 경로로 직접 지정해
실행 환경과 무관하게 같은 조판을 만듭니다. 사진은 가능한 한 `assets/images`의 로컬 자산을
사용합니다. 팟캐스트의 스튜디오 배경만 네트워크에서 가져오며, 게스트 인물 사진
`assets/images/podcast_guest_editorial.png`은 저장소에 포함되어 있습니다.

제품 필름은 `ffmpeg`가 있으면 MP4/WebM을 만들고, 없어도 GIF·HTML·PPTX 렌더를
계속 시도합니다. 사운드트랙은 `assets/audio/hype_beat.wav`에 포함되어 있습니다.
