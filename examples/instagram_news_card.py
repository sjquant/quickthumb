"""속보 대신 맥락을 전하는 주간 뉴스 매거진 카드."""

import os

from quickthumb import Canvas, Filter, FitMode, LinearGradient

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "instagram_news_card.png")
PRETENDARD = os.path.join(ASSETS_DIR, "fonts", "Pretendard-Bold.woff2")

(
    Canvas(1080, 1080)
    .background(color="#EEE9DE")
    .image(
        path=os.path.join(ASSETS_DIR, "images", "tobias-rademacher-wnF27F85ZKw-unsplash.jpg"),
        position=(52, 52),
        width=976,
        height=488,
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.88, contrast=1.06, saturation=0.6)],
    )
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#111A1700", 0.0), ("#111A1744", 0.5), ("#111A17AA", 1.0)],
        ),
        opacity=0.34,
    )
    .text(
        content="THE WEEKLY CONTEXT",
        font=PRETENDARD,
        size=18,
        color="#F8F3E8",
        weight=700,
        letter_spacing=3,
        position=(82, 84),
    )
    .text(
        content="기후는 숫자보다\n먼저 도착한다",
        font=PRETENDARD,
        size=79,
        color="#17211D",
        weight=700,
        line_height=1.12,
        letter_spacing=-3,
        position=(60, 606),
    )
    .text(
        content="산불과 도시의 일상을 연결해 읽는 다섯 개의 장면",
        font=PRETENDARD,
        size=27,
        color="#56605B",
        weight=400,
        position=(64, 827),
    )
    .shape(
        shape="rectangle",
        position=(64, 922),
        width=952,
        height=1,
        color="#17211D55",
    )
    .text(
        content="ENVIRONMENT  /  ISSUE 28",
        font=PRETENDARD,
        size=18,
        color="#B6402E",
        weight=700,
        letter_spacing=2,
        position=(64, 968),
    )
    .text(
        content="2026. 02. 20",
        font=PRETENDARD,
        size=18,
        color="#6E756F",
        weight=500,
        position=(1016, 968),
        align=("right", "top"),
    )
    .render(OUTPUT_PATH)
)

print(f"✓ Weekly context card created: {OUTPUT_PATH}")
