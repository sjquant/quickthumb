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

from quickthumb import Canvas, FitMode, LinearGradient, TextPart
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
        brightness=0.75,
    )
    # 2. Dark gradient overlay — bottom two-thirds darkened for text legibility
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#00000000", 0.0), ("#000000CC", 0.45), ("#000000F0", 1.0)],
        ),
    )
    # 3. "BREAKING NEWS" badge near the top
    .text(
        content="BREAKING NEWS",
        size=38,
        color="#FFFFFF",
        weight=900,
        letter_spacing=4,
        position=("50%", "8%"),
        align=("center", "top"),
        effects=[
            Background(color="#CC0000", padding=(14, 28), border_radius=4),
        ],
    )
    # 4. Main headline — large, bold, white with shadow
    .text(
        content="Wildfires Spread\nAcross Thousands\nof Acres",
        size=96,
        color="#FFFFFF",
        weight=900,
        position=("8%", "48%"),
        align=("left", "middle"),
        line_height=1.15,
        effects=[
            Stroke(width=2, color="#000000"),
            Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=6),
        ],
    )
    # 5. Sub-headline / context line
    .text(
        content="Emergency evacuations ordered in three regions as firefighters battle the blaze",
        size=36,
        color="#E0E0E0",
        weight=400,
        position=("8%", "79%"),
        align=("left", "top"),
        max_width="84%",
        effects=[
            Shadow(offset_x=2, offset_y=2, color="#000000", blur_radius=4),
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
