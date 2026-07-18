"""복잡한 학습법을 한 장의 커리큘럼으로 보여주는 튜토리얼 썸네일."""

import os

from quickthumb import Canvas
from quickthumb.models import Shadow

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_tutorial_explainer.png")
PRETENDARD = os.path.join(ASSETS_DIR, "fonts", "Pretendard-Bold.woff2")

canvas = Canvas(1280, 720).background(color="#1A332D")

canvas.text(
    content="LEARNING MAP  /  01",
    font=PRETENDARD,
    size=18,
    color="#B8D0C8",
    weight=700,
    letter_spacing=3,
    position=(62, 54),
)
canvas.text(
    content="파이썬,\n30일의 지도",
    font=PRETENDARD,
    size=92,
    color="#F5F0E5",
    weight=700,
    line_height=1.08,
    letter_spacing=-4,
    position=(62, 140),
)
canvas.text(
    content="외우지 않고 완성하는 첫 프로젝트",
    font=PRETENDARD,
    size=25,
    color="#B8D0C8",
    weight=400,
    position=(66, 396),
)

steps = [
    ("01", "읽기", "문법보다 흐름"),
    ("02", "만들기", "작게, 매일"),
    ("03", "보내기", "세상에 공개"),
]
for index, (number, title, detail) in enumerate(steps):
    x = 650 + index * 196
    canvas.shape(
        shape="rectangle",
        position=(x, 142),
        width=164,
        height=430,
        color="#F1EBDD" if index != 1 else "#FF6B45",
        border_radius=82,
        effects=[Shadow(offset_x=0, offset_y=12, color="#07130F44", blur_radius=18)],
    )
    canvas.text(
        content=number,
        font=PRETENDARD,
        size=18,
        color="#68746E" if index != 1 else "#4A1D14",
        weight=700,
        position=(x + 82, 190),
        align=("center", "middle"),
    )
    canvas.text(
        content=title,
        font=PRETENDARD,
        size=34,
        color="#1A332D" if index != 1 else "#2A1712",
        weight=700,
        position=(x + 82, 348),
        align=("center", "middle"),
    )
    canvas.text(
        content=detail,
        font=PRETENDARD,
        size=18,
        color="#68746E" if index != 1 else "#54261C",
        weight=500,
        position=(x + 82, 506),
        align=("center", "middle"),
    )

canvas.text(
    content="DAY 01 — 30",
    font=PRETENDARD,
    size=16,
    color="#B8D0C8",
    weight=700,
    letter_spacing=2,
    position=(62, 660),
)
canvas.render(OUTPUT_PATH)

print(f"✓ Curriculum thumbnail created: {OUTPUT_PATH}")
