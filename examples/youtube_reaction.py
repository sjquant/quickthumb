"""유행을 차분하게 해부하는 데이터 저널형 코멘터리 썸네일."""

import os

from quickthumb import Canvas, LinearGradient

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUTPUT_PATH = os.path.join(FILE_DIR, "youtube_reaction.png")
PRETENDARD = os.path.join(ASSETS_DIR, "fonts", "Pretendard-Bold.woff2")

(
    Canvas(1280, 720)
    .background(color="#F2EFE6")
    .background(
        gradient=LinearGradient(
            angle=135,
            stops=[("#F2EFE6", 0.0), ("#E6E0D2", 1.0)],
        )
    )
    .shape(
        shape="ellipse",
        position=(1034, 336),
        width=390,
        height=390,
        color="#FF5A3D",
        align=("center", "middle"),
    )
    .shape(
        shape="ellipse",
        position=(1034, 336),
        width=246,
        height=246,
        color="#F2EFE6",
        align=("center", "middle"),
    )
    .text(
        content="24H",
        font=PRETENDARD,
        size=76,
        color="#17221E",
        weight=700,
        position=(1034, 336),
        align=("center", "middle"),
    )
    .text(
        content="CULTURE CHECK  /  09",
        font=PRETENDARD,
        size=18,
        color="#68706A",
        weight=700,
        letter_spacing=3,
        position=(62, 56),
    )
    .text(
        content="하루 만에\n모두가 따라 한\n그 장면",
        font=PRETENDARD,
        size=90,
        color="#17221E",
        weight=700,
        line_height=1.08,
        letter_spacing=-4,
        position=(62, 138),
    )
    .shape(
        shape="rectangle",
        position=(64, 534),
        width=620,
        height=2,
        color="#17221E",
    )
    .text(
        content="유행의 속도보다 오래 남는 이유를 봅니다",
        font=PRETENDARD,
        size=25,
        color="#4F5853",
        weight=400,
        position=(64, 570),
    )
    .text(
        content="TREND ≠ TASTE",
        font=PRETENDARD,
        size=16,
        color="#17221E",
        weight=700,
        letter_spacing=2,
        position=(1216, 664),
        align=("right", "bottom"),
    )
    .render(OUTPUT_PATH)
)

print(f"✓ Culture commentary thumbnail created: {OUTPUT_PATH}")
