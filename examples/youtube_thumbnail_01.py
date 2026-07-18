"""서울의 비 오는 밤을 담은 절제된 에디토리얼 썸네일."""

import os

from quickthumb import Canvas, Filter, FitMode, LinearGradient

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_thumbnail_01.png")
PRETENDARD = os.path.join(ASSETS_DIR, "fonts", "Pretendard-Bold.woff2")

(
    Canvas.from_aspect_ratio("16:9", 1280)
    .background(
        image=os.path.join(ASSETS_DIR, "images", "c-g-JgDUVGAXsso-unsplash.jpg"),
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.82, contrast=1.08, saturation=0.62)],
    )
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#101416F2", 0.0), ("#101416B8", 0.48), ("#10141612", 1.0)],
        )
    )
    .text(
        content="CITY NOTE  07",
        font=PRETENDARD,
        size=20,
        color="#D8FF4F",
        weight=700,
        letter_spacing=3,
        position=(64, 58),
    )
    .text(
        content="비가 오면\n서울은 조금\n느려진다",
        font=PRETENDARD,
        size=92,
        color="#F5F1E8",
        weight=700,
        line_height=1.08,
        letter_spacing=-3,
        position=(64, 146),
    )
    .shape(
        shape="rectangle",
        position=(64, 538),
        width=470,
        height=1,
        color="#F5F1E866",
    )
    .text(
        content="퇴근길에 발견한 빛과 소리, 그리고 작은 장면들",
        font=PRETENDARD,
        size=25,
        color="#D9D4C9",
        weight=400,
        position=(64, 570),
    )
    .text(
        content="06:42  /  EULJIRO",
        font=PRETENDARD,
        size=17,
        color="#F5F1E899",
        weight=500,
        letter_spacing=2,
        position=(1216, 662),
        align=("right", "bottom"),
    )
    .render(OUTPUT_PATH)
)

print(f"✓ Editorial city thumbnail created: {OUTPUT_PATH}")
