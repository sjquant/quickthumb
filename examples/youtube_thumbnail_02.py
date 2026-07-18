"""일과 회복을 다루는 한국형 라이프스타일 에디토리얼 썸네일."""

import os

from quickthumb import Canvas, Filter, FitMode, LinearGradient
from quickthumb.models import Shadow

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_thumbnail_02.png")
PRETENDARD = os.path.join(ASSETS_DIR, "fonts", "Pretendard-Bold.woff2")

(
    Canvas(1280, 720)
    .background(color="#E9E4D8")
    .image(
        path=os.path.join(ASSETS_DIR, "images", "denise-jans-WIRvXd1PYlg-unsplash.jpg"),
        position=(500, 0),
        width=780,
        height=720,
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.86, contrast=1.03, saturation=0.68)],
    )
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#E9E4D8", 0.0), ("#E9E4D8F2", 0.34), ("#E9E4D800", 0.66)],
        )
    )
    .text(
        content="WORK / LIFE  03",
        font=PRETENDARD,
        size=18,
        color="#4A514C",
        weight=700,
        letter_spacing=3,
        position=(58, 54),
    )
    .text(
        content="잘 쉬는 것도\n연습이 필요해",
        font=PRETENDARD,
        size=82,
        color="#171A18",
        weight=700,
        line_height=1.12,
        letter_spacing=-3,
        position=(58, 154),
        effects=[Shadow(offset_x=0, offset_y=2, color="#FFFFFF55", blur_radius=4)],
    )
    .shape(
        shape="rectangle",
        position=(58, 450),
        width=54,
        height=6,
        color="#F0543C",
        border_radius=3,
    )
    .text(
        content="번아웃 전에 알아차리는\n다섯 가지 작은 신호",
        font=PRETENDARD,
        size=28,
        color="#343A36",
        weight=500,
        line_height=1.45,
        position=(58, 490),
    )
    .text(
        content="SLOW LETTER",
        font=PRETENDARD,
        size=16,
        color="#F6F1E7",
        weight=700,
        letter_spacing=2,
        position=(1224, 666),
        align=("right", "bottom"),
    )
    .render(OUTPUT_PATH)
)

print(f"✓ Lifestyle editorial thumbnail created: {OUTPUT_PATH}")
