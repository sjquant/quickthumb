# YouTube Thumbnails

Three complete 1280×720 YouTube thumbnail layouts, each demonstrating a different composition strategy.

---

## Layout 1 — Bold text on darkened photo

The simplest and most common YouTube format: a background photo, a dark overlay, and oversized headline text with a neon border.

```python
from quickthumb import Canvas, Filter, Stroke, TextPart

(
    Canvas.from_aspect_ratio("16:9", base_width=1280)
    # Background photo, slightly darkened
    .background(
        image="background.jpg",
        effects=[Filter(brightness=0.7)],
    )
    # Dark overlay to push the photo back
    .background(color="#000000", opacity=0.6)
    # Headline with two-tone rich text
    .text(
        content=[
            TextPart(
                text="HOW TO MAKE\nTHUMBNAILS\nIN NO TIME\n",
                color="#B8FF00",
                effects=[Stroke(width=8, color="#000000")],
            ),
            TextPart(
                text="Try QuickThumb Today",
                color="#E0E0E0",
                size=48,
                effects=[Stroke(width=4, color="#000000")],
            ),
        ],
        size=120,
        position=("8%", "50%"),
        align=("left", "middle"),
        bold=True,
    )
    # Neon green border
    .outline(width=15, color="#B8FF00")
    .render("youtube_01.png")
)
```

**Key techniques:**

- Two `TextPart` objects in one `.text()` call for headline + subtext in a single layer
- `Stroke` on both parts to maintain legibility over any background
- `outline()` as the final layer so it sits on top of everything

---

## Layout 2 — Burnout / drama theme

A more editorial layout with a diagonal gradient, stacked text lines at different sizes and colors, and a numbered hook at the bottom.

```python
from quickthumb import (
    Background, Canvas, Filter, FitMode, LinearGradient, Shadow, Stroke,
)

(
    Canvas(1280, 720)
    # Background image with darkening filter
    .background(
        image="background.jpg",
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.7)],
    )
    # Diagonal gradient overlay — dark bottom-left for text, transparent top-right
    .background(
        gradient=LinearGradient(
            angle=120,
            stops=[("#0f0f23", 0.0), ("#0f0f23cc", 0.4), ("#0f0f2300", 1.0)],
        ),
    )
    # Subheading
    .text(
        content="ARE YOU",
        size=40,
        color="#fbbf24",
        position=(50, 80),
        weight=900,
        letter_spacing=2,
        effects=[Shadow(offset_x=3, offset_y=3, color="#000000", blur_radius=0)],
    )
    # Headline line 1
    .text(
        content="BURNING",
        size=150,
        color="#FFFFFF",
        position=(50, 130),
        weight=900,
        effects=[Shadow(offset_x=8, offset_y=8, color="#000000", blur_radius=0)],
    )
    # Headline line 2 — accent color with stroke
    .text(
        content="OUT?",
        size=150,
        color="#ff5722",
        position=(50, 260),
        weight=900,
        effects=[
            Stroke(width=3, color="#FFFFFF"),
            Shadow(offset_x=8, offset_y=8, color="#000000", blur_radius=0),
        ],
    )
    # Numbered hook: "5" in an amber box
    .text(
        content="5",
        size=70,
        color="#0f0f23",
        position=(50, 580),
        weight=900,
        effects=[
            Background(color="#fbbf24", padding=(15, 25), border_radius=8),
            Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=4),
        ],
    )
    .text(
        content="WARNING SIGNS",
        size=45,
        color="#FFFFFF",
        position=(150, 580),
        weight=700,
        effects=[Shadow(offset_x=3, offset_y=3, color="#000000", blur_radius=0)],
    )
    .text(
        content="YOU'RE IGNORING",
        size=45,
        color="#fbbf24",
        position=(150, 635),
        weight=700,
        effects=[Shadow(offset_x=3, offset_y=3, color="#000000", blur_radius=0)],
    )
    .render("youtube_02.png")
)
```

**Key techniques:**

- `LinearGradient` with three stops creates a selective dark zone without covering the whole image
- `Background` effect on the number "5" creates an inline colored badge without a separate shape layer
- Separate `.text()` calls for each line gives fine-grained pixel control over vertical spacing

---

## Layout 3 — Talking-head split

The classic "face on the right, text on the left" layout. A gradient fades the background left-to-right so the text area stays dark and the subject area stays bright.

```python
from quickthumb import (
    Canvas, Filter, FitMode, LinearGradient, Shadow, Stroke, TextPart,
)

PORTRAIT_URL = "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=900&q=80"

(
    Canvas(1280, 720)
    # Background: muted, darkened
    .background(
        image="background.jpg",
        fit=FitMode.COVER,
        effects=[Filter(brightness=0.5, saturation=0.75)],
    )
    # Left-to-right gradient: dark on left for text, transparent on right for subject
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[("#0A0A0A", 0.0), ("#0A0A0ACC", 0.48), ("#0A0A0A00", 1.0)],
        )
    )
    # Topic badge
    .shape(
        shape="rectangle",
        position=(52, 56),
        width=244,
        height=52,
        color="#E53E3E",
        border_radius=8,
        effects=[Shadow(offset_x=0, offset_y=6, color="#00000066", blur_radius=10)],
    )
    .text(
        content="MY HONEST REVIEW",
        size=22,
        color="#FFFFFF",
        weight=900,
        letter_spacing=1,
        position=(174, 82),
        align=("center", "middle"),
    )
    # Main headline: two-tone, tight line height
    .text(
        content=[
            TextPart(text="THE TRUTH\nABOUT\n", color="#FFFFFF", weight=900),
            TextPart(text="AI TOOLS", color="#FFD700", weight=900),
        ],
        size=96,
        line_height=0.95,
        position=(52, 155),
        align=("left", "top"),
        max_width="52%",
        effects=[
            Stroke(width=4, color="#000000"),
            Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=8),
        ],
    )
    # Sub-copy anchored near the bottom-left
    .text(
        content="What nobody tells you",
        size=36,
        color="#D4D4D4",
        weight=500,
        position=(52, 620),
        effects=[Shadow(offset_x=2, offset_y=2, color="#000000", blur_radius=6)],
    )
    # Subject portrait — bottom-right, background removed
    .image(
        path=PORTRAIT_URL,
        position=(1280, 720),
        width=480,
        height=680,
        fit=FitMode.COVER,
        align=("right", "bottom"),
        remove_background=True,
        effects=[Shadow(offset_x=-14, offset_y=0, color="#00000088", blur_radius=22)],
    )
    .outline(width=12, color="#FFD700")
    .render("youtube_talking_head.png")
)
```

**Key techniques:**

- `align=("right", "bottom")` with `position=(1280, 720)` anchors the portrait to the bottom-right canvas corner
- `remove_background=True` cuts out the subject — requires `quickthumb[rembg]`
- Negative `offset_x` on the portrait shadow casts it leftward, adding depth between the person and the text

!!! note "Background removal"
    The talking-head example uses `remove_background=True`. Install the extra before running:
    ```bash
    pip install "quickthumb[rembg]"
    ```

---

## Layout 4 — Tutorial / explainer

A clean numbered-steps layout on a pure gradient background — no background photo required.

```python
from quickthumb import Canvas, LinearGradient, Shadow, Stroke, TextPart

BLUE = "#3B82F6"
DARK = "#0F172A"


def add_step(canvas, number, label, x, y):
    """Render a numbered circle badge + step label."""
    canvas.shape(
        shape="ellipse",
        position=(x, y),
        width=72,
        height=72,
        color=BLUE,
        align=("center", "middle"),
        effects=[Shadow(offset_x=0, offset_y=6, color="#00000066", blur_radius=10)],
    )
    canvas.text(
        content=str(number),
        size=38,
        color="#FFFFFF",
        weight=900,
        position=(x, y),
        align=("center", "middle"),
    )
    canvas.text(
        content=label,
        size=36,
        color="#E2E8F0",
        weight=700,
        position=(x + 48, y),
        align=("left", "middle"),
        effects=[Shadow(offset_x=2, offset_y=2, color="#000000", blur_radius=4)],
    )


canvas = (
    Canvas(1280, 720)
    # Deep blue gradient background
    .background(
        gradient=LinearGradient(
            angle=135,
            stops=[("#0F172A", 0.0), ("#1E3A5F", 0.6), ("#0F172A", 1.0)],
        )
    )
    # Subtle left-edge accent glow
    .background(
        gradient=LinearGradient(
            angle=90,
            stops=[(BLUE + "22", 0.0), (BLUE + "00", 0.55)],
        )
    )
    # "HOW TO" badge
    .shape(shape="rectangle", position=(52, 52), width=168, height=48, color=BLUE,
           border_radius=6)
    .text(content="HOW TO", size=22, color="#FFFFFF", weight=900, letter_spacing=2,
          position=(136, 76), align=("center", "middle"))
    # Two-tone headline
    .text(
        content=[
            TextPart(text="MASTER\n", color="#FFFFFF", weight=900),
            TextPart(text="PYTHON", color="#60A5FA", weight=900),
        ],
        size=118,
        line_height=0.95,
        position=(52, 135),
        align=("left", "top"),
        effects=[
            Stroke(width=4, color=DARK),
            Shadow(offset_x=4, offset_y=4, color="#000000", blur_radius=10),
        ],
    )
    .text(content="in 30 days — from scratch", size=36, color="#94A3B8",
          weight=500, position=(52, 418))
    # Thin vertical divider
    .shape(shape="rectangle", position=(696, 148), width=3, height=390,
           color="#3B82F630", border_radius=2)
)

add_step(canvas, 1, "Learn the basics", 754, 210)
add_step(canvas, 2, "Build real projects", 754, 330)
add_step(canvas, 3, "Ship and deploy", 754, 450)

canvas.outline(width=12, color=BLUE)
canvas.render("youtube_tutorial.png")
```

**Key techniques:**

- `add_step()` helper function keeps repeated badge+label patterns DRY while still using the standard QuickThumb API
- Two gradient backgrounds create a blue glow on the left edge without a visible boundary
- The `"#3B82F630"` color (with `30` alpha) renders the divider as a subtle translucent line
