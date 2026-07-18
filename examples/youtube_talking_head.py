"""인물보다 관점이 먼저 보이는 인터뷰형 썸네일."""

import os

from quickthumb import Canvas, Filter, FitMode, LinearGradient
from quickthumb.models import Shadow

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_talking_head.png")
PRETENDARD = os.path.join(ASSETS_DIR, "fonts", "Pretendard-Bold.woff2")
PORTRAIT_URL = (
    "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=900&q=80"
)

(
    Canvas(1280, 720)
    .background(color="#172C28")
    .shape(
        shape="rectangle",
        position=(40, 40),
        width=1200,
        height=640,
        color="#EDE9DE",
        border_radius=4,
        effects=[Shadow(offset_x=0, offset_y=16, color="#07110E55", blur_radius=28)],
    )
    .image(
        path=PORTRAIT_URL,
        position=(746, 40),
        width=494,
        height=640,
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.94, contrast=0.96, saturation=0.52)],
    )
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#EDE9DE00", 0.52), ("#172C2822", 1.0)],
        )
    )
    .text(
        content="MAKERS  /  014",
        font=PRETENDARD,
        size=17,
        color="#A43E2D",
        weight=700,
        letter_spacing=3,
        position=(84, 80),
    )
    .text(
        content="좋은 도구는\n사라져야 합니다",
        font=PRETENDARD,
        size=77,
        color="#18221F",
        weight=700,
        line_height=1.14,
        letter_spacing=-3,
        position=(84, 168),
        max_width=620,
    )
    .text(
        content="제품을 더하는 대신 경험을 덜어내는 법",
        font=PRETENDARD,
        size=25,
        color="#59635F",
        weight=400,
        position=(88, 456),
    )
    .shape(
        shape="rectangle",
        position=(84, 562),
        width=248,
        height=68,
        color="#172C28",
        border_radius=34,
    )
    .text(
        content="알렉스 리 · 제품 디자이너",
        font=PRETENDARD,
        size=20,
        color="#F5F1E7",
        weight=500,
        position=(208, 596),
        align=("center", "middle"),
    )
    .render(OUTPUT_PATH)
)

print(f"✓ Editorial interview thumbnail created: {OUTPUT_PATH}")
