"""Vela Analytics — evidence-led Series A investor deck.

The example uses a restrained editorial system and a complete investment arc:
thesis, problem, why now, workflow, product proof, traction, business model,
market and GTM, defensibility, and a concrete financing ask. All company data
is explicitly marked as illustrative.

Run:
    quickthumb serve examples/investor_deck.py

Export:
    uv run python examples/investor_deck.py
"""

import os

from quickthumb import Box, Canvas, Deck, Fade, Wipe
from quickthumb import transitions as tr

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUT_HTML = os.path.join(FILE_DIR, "investor_deck.html")
OUT_PPTX = os.path.join(FILE_DIR, "investor_deck.pptx")

os.environ["QUICKTHUMB_FONT_DIR"] = os.path.join(ASSETS_DIR, "fonts")
os.environ["QUICKTHUMB_DEFAULT_FONT"] = "Roboto"

PAPER = "#F5F5F7"
WHITE = "#FFFFFF"
INK = "#1D1D1F"
MUTED = "#6E6E73"
BLUE = "#0066CC"
BLUE_SOFT = "#E8F2FF"
GREEN = "#197A55"
RULE = "#D2D2D7"
PANEL = "#EDEDF0"
DARK = "#101114"


def main() -> None:
    """Render the browser and PowerPoint versions from one deck."""
    deck.render(OUT_HTML)
    deck.render(OUT_PPTX)
    print(f"✓ {OUT_HTML}")
    print(f"  {len(deck)} slides — open in a browser.")
    print("  Click / Space → advance   ArrowLeft → back")


def build_deck() -> Deck:
    """Build a ten-slide investment narrative with consistent transitions."""
    slides = [
        build_cover_slide(),
        build_problem_slide(),
        build_why_now_slide(),
        build_workflow_slide(),
        build_product_slide(),
        build_traction_slide(),
        build_business_model_slide(),
        build_market_gtm_slide(),
        build_moat_slide(),
        build_team_ask_slide(),
    ]
    notes = [
        "State the decision-intelligence thesis in one sentence.",
        "Ground the problem in weekly customer cost, not an unsupported market statistic.",
        "Explain why the category becomes possible now.",
        "Walk through one incident from detection to recorded decision.",
        "Use the product surface to prove the workflow is operational, not conceptual.",
        "Define every metric and its period before discussing growth.",
        "Explain how the initial team contract expands through the organization.",
        "Connect the initial wedge to the repeatable acquisition motion.",
        "Position Vela on context and action, then explain the compounding data moat.",
        "Close on the financing amount, deployment, and twenty-four-month milestones.",
    ]

    result = Deck(1280, 720)
    for index, slide in enumerate(slides):
        transition = None if index == 0 else tr.Fade(duration=0.35)
        result = result.slide(slide, transition=transition, notes=notes[index])
    return result


def build_cover_slide() -> Canvas:
    """Lead with a specific thesis and a product-shaped signal field."""
    canvas = stage("SERIES A", 1)
    canvas = canvas.text(
        content="Know what changed.\nDecide what to do next.",
        font="Roboto",
        size=78,
        color=INK,
        weight=500,
        line_height=1.05,
        letter_spacing=-2,
        position=(96, 180),
        max_width=760,
        animation=Fade(duration=0.45),
    )
    canvas = canvas.text(
        content=(
            "Vela turns product data into an explained, owned decision — before the moment passes."
        ),
        font="Roboto",
        size=27,
        color=MUTED,
        weight=400,
        line_height=1.45,
        position=(100, 430),
        max_width=650,
        animation=Fade(duration=0.35, trigger="after_previous"),
    )
    canvas = canvas.shape(
        shape="ellipse",
        position=(1038, 355),
        width=470,
        height=470,
        color=BLUE,
        align=("center", "middle"),
    )
    for index, width in enumerate((180, 116, 224, 148)):
        canvas = canvas.shape(
            shape="rectangle",
            position=(970, 250 + index * 70),
            width=width,
            height=8 if index == 0 else 5,
            color=WHITE,
            animation=Wipe(direction="right", duration=0.32, trigger="with_previous"),
        )
    canvas = canvas.text(
        content="Decision intelligence for product teams",
        font="Roboto",
        size=20,
        color=MUTED,
        weight=500,
        position=(100, 625),
    )
    return canvas.text(
        content="CONFIDENTIAL  ·  ILLUSTRATIVE COMPANY DATA",
        font="Roboto",
        size=18,
        color=MUTED,
        weight=500,
        letter_spacing=1,
        position=(1184, 625),
        align=("right", "top"),
    )


def build_problem_slide() -> Canvas:
    """Quantify the customer cost with an explicit illustrative source."""
    canvas = stage("THE PROBLEM", 2)
    canvas = section_title(canvas, "Teams find the signal\nafter the decision.")
    canvas = canvas.text(
        content="11.4",
        font="Roboto",
        size=190,
        color=BLUE,
        weight=500,
        letter_spacing=-8,
        position=(96, 300),
        animation=Box(direction="in", duration=0.45),
    )
    canvas = canvas.text(
        content="HOURS / WEEK",
        font="Roboto",
        size=24,
        color=INK,
        weight=700,
        letter_spacing=2,
        position=(110, 515),
    )
    canvas = canvas.text(
        content=(
            "spent reconciling dashboards, alerts, and stakeholder context "
            "before a product decision can be made."
        ),
        font="Roboto",
        size=27,
        color=MUTED,
        weight=400,
        line_height=1.45,
        position=(470, 335),
        max_width=650,
    )
    canvas = add_source_note(
        canvas,
        "Illustrative customer discovery · n=42 product teams · Q2 2026",
    )
    return add_fragments(canvas)


def build_why_now_slide() -> Canvas:
    """Explain the category timing through three connected market shifts."""
    canvas = stage("WHY NOW", 3)
    canvas = section_title(canvas, "The cost of finding context\nis collapsing.")
    shifts = [
        ("01", "MORE SIGNAL", "Product teams now operate across dozens of live data sources."),
        ("02", "LOWER COST", "Models can explain anomalies in seconds, not analyst-days."),
        (
            "03",
            "HIGHER URGENCY",
            "Shorter shipping cycles leave no room for manual reconciliation.",
        ),
    ]
    for index, (number, title, body) in enumerate(shifts):
        x = 96 + index * 390
        canvas = canvas.shape(
            shape="rectangle",
            position=(x, 360),
            width=330,
            height=4,
            color=BLUE if index == 1 else RULE,
            animation=Wipe(direction="right", duration=0.35),
        )
        canvas = canvas.text(
            content=number,
            font="Roboto",
            size=20,
            color=BLUE,
            weight=700,
            position=(x, 390),
        )
        canvas = canvas.text(
            content=title,
            font="Roboto",
            size=31,
            color=INK,
            weight=700,
            position=(x, 435),
        )
        canvas = canvas.text(
            content=body,
            font="Roboto",
            size=22,
            color=MUTED,
            weight=400,
            line_height=1.45,
            position=(x, 500),
            max_width=320,
        )
    return add_source_note(
        canvas,
        "Category drivers shown for illustration; replace with sourced market evidence.",
    )


def build_workflow_slide() -> Canvas:
    """Make the product legible as one end-to-end operating workflow."""
    canvas = stage("THE WORKFLOW", 4)
    canvas = section_title(canvas, "From anomaly to owned decision.")
    steps = [
        ("DETECT", "Conversion -18.4%"),
        ("EXPLAIN", "Payment timeout"),
        ("ROUTE", "Owner: Checkout"),
        ("DECIDE", "Rollback recorded"),
    ]
    canvas = canvas.shape(
        shape="rectangle",
        position=(135, 400),
        width=980,
        height=3,
        color=RULE,
    )
    for index, (title, detail) in enumerate(steps):
        x = 150 + index * 300
        canvas = canvas.shape(
            shape="ellipse",
            position=(x, 402),
            width=20,
            height=20,
            color=BLUE if index < 3 else GREEN,
            align=("center", "middle"),
            animation=(
                Fade(duration=0.3) if index == 0 else Fade(duration=0.3, trigger="after_previous")
            ),
        )
        canvas = canvas.text(
            content=title,
            font="Roboto",
            size=20,
            color=BLUE,
            weight=700,
            letter_spacing=2,
            position=(x, 445),
            align=("center", "top"),
        )
        canvas = canvas.text(
            content=detail,
            font="Roboto",
            size=27,
            color=INK,
            weight=500,
            line_height=1.25,
            position=(x, 505),
            align=("center", "top"),
            max_width=230,
        )
    return add_source_note(canvas, "Illustrative incident workflow")


def build_product_slide() -> Canvas:
    """Show one believable product surface instead of feature columns."""
    canvas = stage("PRODUCT PROOF", 5, dark=True)
    canvas = canvas.text(
        content="One screen explains\nwhat changed and why.",
        font="Roboto",
        size=53,
        color=WHITE,
        weight=500,
        line_height=1.05,
        letter_spacing=-1,
        position=(80, 120),
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(80, 285),
        width=1120,
        height=355,
        color="#181A1F",
        border_radius=18,
        effects=[{"type": "stroke", "width": 1, "color": "#3B3D44"}],
        animation=Fade(duration=0.35),
    )
    canvas = canvas.text(
        content="CHECKOUT CONVERSION",
        font="Roboto",
        size=18,
        color="#9A9BA1",
        weight=700,
        letter_spacing=2,
        position=(120, 325),
    )
    canvas = canvas.text(
        content="−18.4%",
        font="Roboto",
        size=78,
        color=WHITE,
        weight=500,
        letter_spacing=-2,
        position=(120, 370),
    )
    canvas = add_product_chart(canvas)
    canvas = canvas.shape(
        shape="rectangle",
        position=(740, 325),
        width=1,
        height=270,
        color="#3B3D44",
    )
    canvas = canvas.text(
        content="LIKELY CAUSE",
        font="Roboto",
        size=18,
        color=BLUE_SOFT,
        weight=700,
        letter_spacing=2,
        position=(785, 325),
    )
    canvas = canvas.text(
        content="Payment provider timeout\nafter deploy #4821",
        font="Roboto",
        size=31,
        color=WHITE,
        weight=500,
        line_height=1.25,
        position=(785, 385),
    )
    canvas = canvas.text(
        content="OWNER   Checkout team\nACTION  Roll back deploy\nSTATUS  Decision recorded",
        font="Roboto",
        size=20,
        color="#B8B8BE",
        weight=400,
        line_height=1.7,
        position=(785, 495),
    )
    return canvas


def build_traction_slide() -> Canvas:
    """Present traction with periods, definitions, and a growth shape."""
    canvas = stage("TRACTION", 6)
    canvas = section_title(canvas, "$1.8M ARR.\n3.1× year over year.")
    canvas = add_arr_chart(canvas)
    metrics = [
        ("94%", "GROSS LOGO RETENTION", "Trailing 12 months"),
        ("2,400", "WEEKLY ACTIVE TEAMS", "Four-week average"),
        ("11 WKS", "SALES CYCLE", "Median, closed-won"),
    ]
    for index, (value, label, period) in enumerate(metrics):
        x = 700 + (index % 2) * 270
        y = 300 + (index // 2) * 185
        canvas = canvas.text(
            content=value,
            font="Roboto",
            size=58,
            color=GREEN if index == 0 else INK,
            weight=500,
            letter_spacing=-2,
            position=(x, y),
        )
        canvas = canvas.text(
            content=label,
            font="Roboto",
            size=18,
            color=INK,
            weight=700,
            letter_spacing=1,
            position=(x, y + 75),
        )
        canvas = canvas.text(
            content=period,
            font="Roboto",
            size=18,
            color=MUTED,
            weight=400,
            position=(x, y + 110),
        )
    return add_source_note(canvas, "Illustrative operating metrics · Q2 2026")


def build_business_model_slide() -> Canvas:
    """Explain the land-and-expand mechanics with explicit unit metrics."""
    canvas = stage("BUSINESS MODEL", 7)
    canvas = section_title(canvas, "Land with one team.\nExpand with shared context.")
    stages = [
        ("LAND", "$24K", "Starting ACV\n1 product team"),
        ("EXPAND", "$72K", "Median year-two ACV\n3 connected teams"),
        ("COMPOUND", "118%", "Net revenue retention\nTrailing 12 months"),
    ]
    for index, (label, value, detail) in enumerate(stages):
        x = 96 + index * 390
        canvas = canvas.text(
            content=label,
            font="Roboto",
            size=18,
            color=BLUE,
            weight=700,
            letter_spacing=2,
            position=(x, 360),
        )
        canvas = canvas.text(
            content=value,
            font="Roboto",
            size=76,
            color=INK,
            weight=500,
            letter_spacing=-3,
            position=(x, 405),
        )
        canvas = canvas.text(
            content=detail,
            font="Roboto",
            size=22,
            color=MUTED,
            weight=400,
            line_height=1.4,
            position=(x, 510),
        )
        if index < 2:
            canvas = canvas.shape(
                shape="rectangle",
                position=(x + 310, 455),
                width=42,
                height=2,
                color=RULE,
            )
            canvas = canvas.shape(
                shape="ellipse",
                position=(x + 350, 456),
                width=8,
                height=8,
                color=BLUE,
                align=("center", "middle"),
            )
    return add_source_note(canvas, "Illustrative pricing and retention metrics · Q2 2026")


def build_market_gtm_slide() -> Canvas:
    """Pair a bottom-up market wedge with a repeatable acquisition motion."""
    canvas = stage("MARKET + GTM", 8)
    canvas = section_title(canvas, "Start narrow.\nExpand through the workflow.")
    canvas = canvas.text(
        content="$1.2B",
        font="Roboto",
        size=100,
        color=BLUE,
        weight=500,
        letter_spacing=-4,
        position=(96, 345),
    )
    canvas = canvas.text(
        content="INITIAL WEDGE",
        font="Roboto",
        size=18,
        color=INK,
        weight=700,
        letter_spacing=2,
        position=(102, 470),
    )
    canvas = canvas.text(
        content="50K product-led companies\n× $24K starting ACV",
        font="Roboto",
        size=22,
        color=MUTED,
        weight=400,
        line_height=1.45,
        position=(102, 515),
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(590, 325),
        width=1,
        height=280,
        color=RULE,
    )
    motions = [
        ("01", "DESIGN PARTNERS", "Founder-led proof in high-pain teams"),
        ("02", "TEAM EXPANSION", "Shared incidents invite adjacent teams"),
        ("03", "ENTERPRISE", "Security and governance unlock standardization"),
    ]
    for index, (number, title, body) in enumerate(motions):
        y = 330 + index * 100
        canvas = canvas.text(
            content=number,
            font="Roboto",
            size=18,
            color=BLUE,
            weight=700,
            position=(650, y),
        )
        canvas = canvas.text(
            content=title,
            font="Roboto",
            size=22,
            color=INK,
            weight=700,
            position=(710, y),
        )
        canvas = canvas.text(
            content=body,
            font="Roboto",
            size=19,
            color=MUTED,
            weight=400,
            position=(710, y + 38),
        )
    return add_source_note(
        canvas,
        "Illustrative bottom-up market sizing; replace assumptions with sourced account data.",
    )


def build_moat_slide() -> Canvas:
    """Position the product and explain what compounds with usage."""
    canvas = stage("DEFENSIBILITY", 9)
    canvas = section_title(canvas, "Context compounds.\nWorkflows become harder to replace.")
    canvas = add_competition_map(canvas)
    canvas = canvas.text(
        content="WHAT COMPOUNDS",
        font="Roboto",
        size=18,
        color=BLUE,
        weight=700,
        letter_spacing=2,
        position=(735, 350),
    )
    moat = [
        "Decision history tied to live product signals",
        "Organization-specific ownership and escalation graph",
        "Integration footprint across analytics and workflow tools",
    ]
    for index, item in enumerate(moat):
        canvas = canvas.text(
            content=f"0{index + 1}",
            font="Roboto",
            size=18,
            color=BLUE,
            weight=700,
            position=(735, 410 + index * 70),
        )
        canvas = canvas.text(
            content=item,
            font="Roboto",
            size=22,
            color=INK,
            weight=400,
            position=(790, 405 + index * 70),
            max_width=390,
        )
    return add_source_note(canvas, "Illustrative competitive positioning")


def build_team_ask_slide() -> Canvas:
    """Close on team credibility, financing deployment, and milestones."""
    canvas = stage("TEAM + ASK", 10)
    canvas = canvas.text(
        content="Raising $8M\nSeries A.",
        font="Roboto",
        size=78,
        color=INK,
        weight=500,
        line_height=1.02,
        letter_spacing=-2,
        position=(96, 165),
        animation=Fade(duration=0.4),
    )
    canvas = canvas.text(
        content="24 months to $8M ARR and repeatable enterprise distribution.",
        font="Roboto",
        size=25,
        color=MUTED,
        weight=400,
        position=(100, 365),
        max_width=550,
    )
    canvas = canvas.text(
        content="USE OF FUNDS",
        font="Roboto",
        size=18,
        color=BLUE,
        weight=700,
        letter_spacing=2,
        position=(100, 455),
    )
    canvas = canvas.text(
        content="45%  Product + AI\n35%  Enterprise GTM\n20%  Security + operations",
        font="Roboto",
        size=23,
        color=INK,
        weight=500,
        line_height=1.65,
        position=(100, 500),
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(690, 165),
        width=1,
        height=440,
        color=RULE,
    )
    canvas = canvas.text(
        content="FOUNDING TEAM",
        font="Roboto",
        size=18,
        color=BLUE,
        weight=700,
        letter_spacing=2,
        position=(750, 175),
    )
    team = [
        ("Maya Chen", "CEO · Product analytics, ex-Atlas"),
        ("Jon Bell", "CTO · Data systems, ex-Vector"),
        ("Priya Shah", "VP GTM · Enterprise SaaS, ex-North"),
    ]
    for index, (name, role) in enumerate(team):
        y = 245 + index * 105
        canvas = canvas.text(
            content=name,
            font="Roboto",
            size=30,
            color=INK,
            weight=500,
            position=(750, y),
        )
        canvas = canvas.text(
            content=role,
            font="Roboto",
            size=19,
            color=MUTED,
            weight=400,
            position=(750, y + 45),
        )
    canvas = canvas.text(
        content="Illustrative names, roles, and financing data",
        font="Roboto",
        size=18,
        color=MUTED,
        weight=400,
        position=(750, 585),
    )
    return canvas.text(
        content="invest@vela.so",
        font="Roboto",
        size=21,
        color=BLUE,
        weight=700,
        position=(1184, 650),
        align=("right", "top"),
    )


def stage(section: str, page: int, *, dark: bool = False) -> Canvas:
    """Create the shared editorial stage and navigation line."""
    background = DARK if dark else PAPER
    muted = "#9A9BA1" if dark else MUTED
    rule = "#34363C" if dark else RULE
    canvas = Canvas(1280, 720).background(color=background)
    canvas = canvas.text(
        content="VELA",
        font="Roboto",
        size=18,
        color=BLUE,
        weight=700,
        letter_spacing=4,
        position=(80, 55),
    )
    canvas = canvas.text(
        content=section,
        font="Roboto",
        size=18,
        color=muted,
        weight=500,
        letter_spacing=2,
        position=(640, 58),
        align=("center", "top"),
    )
    canvas = canvas.text(
        content=f"{page:02d} / 10",
        font="Roboto",
        size=18,
        color=muted,
        weight=500,
        letter_spacing=1,
        position=(1200, 58),
        align=("right", "top"),
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(80, 96),
        width=1120,
        height=1,
        color=rule,
    )
    return canvas


def section_title(canvas: Canvas, content: str) -> Canvas:
    """Place the primary editorial statement on the shared grid."""
    return canvas.text(
        content=content,
        font="Roboto",
        size=56,
        color=INK,
        weight=500,
        line_height=1.05,
        letter_spacing=-1,
        position=(96, 150),
        animation=Fade(duration=0.4),
    )


def add_source_note(canvas: Canvas, content: str) -> Canvas:
    """Attach a visible provenance note to illustrative claims."""
    return canvas.text(
        content=content,
        font="Roboto",
        size=18,
        color=MUTED,
        weight=400,
        position=(96, 666),
    )


def add_fragments(canvas: Canvas) -> Canvas:
    """Show the fragmented tools that create the problem."""
    labels = ("DASHBOARDS", "ALERTS", "TICKETS")
    for index, label in enumerate(labels):
        x = 475 + index * 220
        canvas = canvas.shape(
            shape="rectangle",
            position=(x, 520),
            width=175,
            height=5,
            color=BLUE if index == 1 else RULE,
        )
        canvas = canvas.text(
            content=label,
            font="Roboto",
            size=18,
            color=MUTED,
            weight=700,
            letter_spacing=1,
            position=(x, 550),
        )
    return canvas


def add_product_chart(canvas: Canvas) -> Canvas:
    """Draw a compact conversion series with a visible incident drop."""
    heights = (80, 92, 86, 98, 90, 56, 43, 39)
    for index, height in enumerate(heights):
        canvas = canvas.shape(
            shape="rectangle",
            position=(125 + index * 65, 585 - height),
            width=34,
            height=height,
            color=BLUE if index < 5 else "#5B5D65",
            animation=Wipe(direction="up", duration=0.3, trigger="with_previous"),
        )
    return canvas


def add_arr_chart(canvas: Canvas) -> Canvas:
    """Draw six quarterly ARR bars with explicit period labels."""
    values = (90, 130, 190, 270, 390, 540)
    labels = ("Q1'25", "Q2", "Q3", "Q4", "Q1'26", "Q2")
    for index, (height, label) in enumerate(zip(values, labels, strict=True)):
        x = 100 + index * 88
        canvas = canvas.shape(
            shape="rectangle",
            position=(x, 610 - height // 2),
            width=50,
            height=height // 2,
            color=BLUE if index == len(values) - 1 else "#A9CFF5",
            animation=Wipe(direction="up", duration=0.3, trigger="with_previous"),
        )
        canvas = canvas.text(
            content=label,
            font="Roboto",
            size=18,
            color=MUTED,
            weight=400,
            position=(x + 25, 625),
            align=("center", "top"),
        )
    return canvas


def add_competition_map(canvas: Canvas) -> Canvas:
    """Place Vela on a simple context-versus-action competitive map."""
    canvas = canvas.shape(
        shape="rectangle",
        position=(120, 365),
        width=500,
        height=1,
        color=RULE,
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(370, 275),
        width=1,
        height=300,
        color=RULE,
    )
    points = [
        ("BI", 220, 455, MUTED),
        ("ALERTING", 455, 470, MUTED),
        ("COPILOTS", 470, 320, MUTED),
        ("VELA", 550, 295, BLUE),
    ]
    for label, x, y, color in points:
        canvas = canvas.shape(
            shape="ellipse",
            position=(x, y),
            width=14 if label != "VELA" else 22,
            height=14 if label != "VELA" else 22,
            color=color,
            align=("center", "middle"),
        )
        canvas = canvas.text(
            content=label,
            font="Roboto",
            size=18,
            color=color,
            weight=700,
            position=(x + 15, y - 12),
        )
    canvas = canvas.text(
        content="MORE CONTEXT",
        font="Roboto",
        size=18,
        color=MUTED,
        weight=500,
        letter_spacing=1,
        position=(455, 585),
    )
    return canvas.text(
        content="MORE ACTION",
        font="Roboto",
        size=18,
        color=MUTED,
        weight=500,
        letter_spacing=1,
        position=(105, 275),
    )


deck = build_deck()


if __name__ == "__main__":
    main()
