"""
Instagram News Card Example

Creates a breaking news-style Instagram card (1080x1080) with:
- Fire background image (cover fit, darkened)
- Dark gradient overlay for text legibility
- "BREAKING NEWS" badge
- Bold headline with stroke
- Source and timestamp at the bottom
"""

import os

from quickthumb import Canvas, Filter, FitMode, LinearGradient, TextPart
from quickthumb.models import Background, Shadow, Stroke

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

SIZE = 1080

(
    Canvas(SIZE, SIZE)
    # 1. Background: fire image, cropped to fill the square
    .background(
        image=os.path.join(ASSETS_DIR, "images", "tobias-rademacher-wnF27F85ZKw-unsplash.jpg"),
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.9, contrast=1.1, saturation=0.9)],
    )
    # 2. Dark gradient overlay — bottom two-thirds darkened for text legibility
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#00000000", 0.0), ("#000000B8", 0.42), ("#000000F2", 1.0)],
        ),
    )
    .text(
        content="QUICKTHUMB  /  LIVE DESK",
        size=19,
        color="#FFFFFFAA",
        weight=700,
        letter_spacing=3,
        position=("8%", "6%"),
        align=("left", "top"),
    )
    .shape(
        shape="rectangle",
        position=("8%", "11%"),
        width=908,
        height=2,
        color="#FFFFFF44",
    )
    # 3. "BREAKING NEWS" badge near the top
    .text(
        content="BREAKING NEWS",
        size=28,
        color="#FFFFFF",
        weight=900,
        letter_spacing=4,
        position=("8%", "15%"),
        align=("left", "top"),
        effects=[
            Background(color="#CC0000", padding=(11, 22), border_radius=2),
        ],
    )
    .shape(
        shape="rectangle",
        position=("8%", "34%"),
        width=9,
        height=336,
        color="#E11D2E",
        border_radius=4,
    )
    # 4. Main headline — large, bold, white with shadow
    .text(
        content="Wildfires Spread\nAcross Thousands\nof Acres",
        font="NotoSerif",
        size=88,
        color="#FFFFFF",
        weight=900,
        position=("11%", "50%"),
        align=("left", "middle"),
        line_height=1.12,
        effects=[
            Stroke(width=1, color="#000000"),
            Shadow(offset_x=0, offset_y=6, color="#000000AA", blur_radius=10),
        ],
    )
    # 5. Sub-headline / context line
    .text(
        content="Emergency evacuations ordered in three regions as firefighters battle the blaze",
        size=30,
        color="#E0E0E0",
        weight=400,
        position=("8%", "79%"),
        align=("left", "top"),
        max_width="78%",
        effects=[
            Shadow(offset_x=0, offset_y=3, color="#00000099", blur_radius=6),
        ],
    )
    # 6. Source and timestamp row
    .text(
        content=[
            TextPart(text="WORLD NEWS  ", color="#FF4444", weight=700),
            TextPart(text="·  Feb 20, 2026", color="#AAAAAA", weight=400),
        ],
        size=30,
        position=("8%", "92%"),
        align=("left", "top"),
    )
    # Render
    .render(os.path.join(FILE_DIR, "instagram_news_card.png"))
)

print(f"✓ Instagram news card created: {os.path.join(FILE_DIR, 'instagram_news_card.png')}")
