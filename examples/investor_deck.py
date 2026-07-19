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
    """Lead with the thesis inside a decisive split editorial composition."""
    canvas = Canvas(1280, 720).background(color=PAPER)
    canvas = canvas.shape(
        shape="rectangle",
        position=(940, 0),
        width=340,
        height=720,
        color=BLUE,
        animation=Wipe(direction="left", duration=0.45),
    )
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
        content="SERIES A  ·  2026",
        font="Roboto",
        size=18,
        color=MUTED,
        weight=500,
        letter_spacing=2,
        position=(860, 58),
        align=("right", "top"),
    )
    canvas = canvas.text(
        content="Know what\nchanged.",
        font="Roboto",
        size=92,
        color=INK,
        weight=500,
        line_height=0.98,
        letter_spacing=-4,
        position=(80, 145),
        max_width=800,
        animation=Fade(duration=0.45),
    )
    canvas = canvas.text(
        content="Decide what happens next.",
        font="Roboto",
        size=39,
        color=BLUE,
        weight=500,
        letter_spacing=-1,
        position=(86, 365),
        animation=Fade(duration=0.35, trigger="after_previous"),
    )
    canvas = canvas.text(
        content=(
            "Vela turns product data into an explained, owned decision — before the moment passes."
        ),
        font="Roboto",
        size=24,
        color=MUTED,
        weight=400,
        line_height=1.4,
        position=(86, 455),
        max_width=650,
    )
    signal_widths = (118, 190, 86, 230, 154)
    for index, width in enumerate(signal_widths):
        canvas = canvas.shape(
            shape="rectangle",
            position=(980, 170 + index * 67),
            width=width,
            height=6,
            color=WHITE,
            animation=Wipe(direction="right", duration=0.32, trigger="with_previous"),
        )
    canvas = canvas.text(
        content="01",
        font="Roboto",
        size=104,
        color=WHITE,
        weight=500,
        letter_spacing=-5,
        position=(1172, 535),
        align=("right", "top"),
    )
    return canvas.text(
        content="DECISION INTELLIGENCE FOR PRODUCT TEAMS  ·  CONFIDENTIAL",
        font="Roboto",
        size=18,
        color=MUTED,
        weight=500,
        letter_spacing=1,
        position=(80, 640),
    )


def build_problem_slide() -> Canvas:
    """Quantify the customer cost with an explicit illustrative source."""
    canvas = stage("THE PROBLEM", 2)
    canvas = section_title(canvas, "The decision arrives\nbefore the context.")
    canvas = canvas.text(
        content="11.4",
        font="Roboto",
        size=230,
        color=BLUE,
        weight=500,
        letter_spacing=-8,
        position=(88, 265),
        animation=Box(direction="in", duration=0.45),
    )
    canvas = canvas.text(
        content="HOURS / WEEK",
        font="Roboto",
        size=24,
        color=INK,
        weight=700,
        letter_spacing=2,
        position=(104, 530),
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
        position=(570, 320),
        max_width=540,
    )
    canvas = add_source_note(
        canvas,
        "Illustrative customer discovery · n=42 product teams · Q2 2026",
    )
    return add_fragments(canvas)


def build_why_now_slide() -> Canvas:
    """Explain category timing as three forces converging on one moment."""
    canvas = stage("WHY NOW", 3)
    canvas = section_title(canvas, "Three forces converge.\nThe category opens now.")
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
        x = 96 + index * 370
        y = 345 + index * 52
        canvas = canvas.shape(
            shape="rectangle",
            position=(x, y),
            width=300,
            height=7,
            color=BLUE,
            animation=Wipe(direction="right", duration=0.35),
        )
        canvas = canvas.text(
            content=number,
            font="Roboto",
            size=20,
            color=BLUE,
            weight=700,
            position=(x, y + 28),
        )
        canvas = canvas.text(
            content=title,
            font="Roboto",
            size=31,
            color=INK,
            weight=700,
            position=(x, y + 68),
        )
        canvas = canvas.text(
            content=body,
            font="Roboto",
            size=22,
            color=MUTED,
            weight=400,
            line_height=1.45,
            position=(x, y + 118),
            max_width=300,
        )
    return add_source_note(
        canvas,
        "Category drivers shown for illustration; replace with sourced market evidence.",
    )


def build_workflow_slide() -> Canvas:
    """Make the product legible as one end-to-end operating workflow."""
    canvas = stage("THE WORKFLOW", 4)
    canvas = section_title(canvas, "One signal.\nOne accountable decision.")
    steps = [
        ("DETECT", "Conversion -18.4%"),
        ("EXPLAIN", "Payment timeout"),
        ("ROUTE", "Owner: Checkout"),
        ("DECIDE", "Rollback recorded"),
    ]
    for index, (title, detail) in enumerate(steps):
        x = 80 + index * 300
        color = GREEN if index == 3 else BLUE
        canvas = canvas.shape(
            shape="rectangle",
            position=(x, 370),
            width=280,
            height=205,
            color=WHITE if index < 3 else "#E8F5EF",
            effects=[{"type": "stroke", "width": 1, "color": RULE}],
            animation=Fade(duration=0.3, trigger="after_previous"),
        )
        canvas = canvas.shape(
            shape="ellipse",
            position=(x + 32, 405),
            width=12,
            height=12,
            color=color,
            align=("center", "middle"),
        )
        canvas = canvas.text(
            content=title,
            font="Roboto",
            size=20,
            color=color,
            weight=700,
            letter_spacing=2,
            position=(x + 55, 394),
        )
        canvas = canvas.text(
            content=detail,
            font="Roboto",
            size=29,
            color=INK,
            weight=500,
            line_height=1.25,
            position=(x + 28, 465),
            max_width=220,
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
    """Make the growth trajectory the dominant visual proof."""
    canvas = stage("TRACTION", 6)
    canvas = canvas.text(
        content="$1.8M",
        font="Roboto",
        size=132,
        color=INK,
        weight=500,
        letter_spacing=-6,
        position=(88, 125),
        animation=Fade(duration=0.4),
    )
    canvas = canvas.text(
        content="ARR",
        font="Roboto",
        size=25,
        color=MUTED,
        weight=700,
        letter_spacing=2,
        position=(102, 285),
    )
    canvas = canvas.text(
        content="3.1× YoY",
        font="Roboto",
        size=36,
        color=BLUE,
        weight=500,
        position=(330, 265),
    )
    canvas = add_arr_chart(canvas)
    metrics = [
        ("94%", "GROSS LOGO RETENTION", "Trailing 12 months"),
        ("2,400", "WEEKLY ACTIVE TEAMS", "Four-week average"),
        ("11 WKS", "SALES CYCLE", "Median, closed-won"),
    ]
    for index, (value, label, period) in enumerate(metrics):
        x = 735
        y = 205 + index * 135
        canvas = canvas.shape(
            shape="rectangle",
            position=(x, y - 22),
            width=445,
            height=1,
            color=RULE,
        )
        canvas = canvas.text(
            content=value,
            font="Roboto",
            size=50,
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
            position=(x + 180, y + 5),
        )
        canvas = canvas.text(
            content=period,
            font="Roboto",
            size=18,
            color=MUTED,
            weight=400,
            position=(x + 180, y + 38),
        )
    return add_source_note(canvas, "Illustrative operating metrics · Q2 2026")


def build_business_model_slide() -> Canvas:
    """Show expansion as a visibly compounding account footprint."""
    canvas = stage("BUSINESS MODEL", 7)
    canvas = section_title(canvas, "Land with one team.\nExpand with shared context.")
    stages = [
        ("LAND", "$24K", "Starting ACV\n1 product team"),
        ("EXPAND", "$72K", "Median year-two ACV\n3 connected teams"),
        ("COMPOUND", "118%", "Net revenue retention\nTrailing 12 months"),
    ]
    circle_sizes = (150, 220, 290)
    for index, (label, value, detail) in enumerate(stages):
        x = 170 + index * 390
        canvas = canvas.shape(
            shape="ellipse",
            position=(x, 475),
            width=circle_sizes[index],
            height=circle_sizes[index],
            color=("#E8F2FF", "#CFE5FF", BLUE)[index],
            align=("center", "middle"),
            animation=Fade(duration=0.32, trigger="after_previous"),
        )
        canvas = canvas.text(
            content=label,
            font="Roboto",
            size=18,
            color=BLUE,
            weight=700,
            letter_spacing=2,
            position=(x, 362),
            align=("center", "top"),
        )
        canvas = canvas.text(
            content=value,
            font="Roboto",
            size=76,
            color=WHITE if index == 2 else INK,
            weight=500,
            letter_spacing=-3,
            position=(x, 433),
            align=("center", "top"),
        )
        canvas = canvas.text(
            content=detail,
            font="Roboto",
            size=22,
            color=WHITE if index == 2 else MUTED,
            weight=400,
            line_height=1.4,
            position=(x, 520),
            align=("center", "top"),
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
    """Position the product with a map that gives Vela unmistakable separation."""
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
        position=(760, 330),
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
            position=(760, 390 + index * 76),
        )
        canvas = canvas.text(
            content=item,
            font="Roboto",
            size=22,
            color=INK,
            weight=400,
            position=(815, 385 + index * 76),
            max_width=360,
        )
    return add_source_note(canvas, "Illustrative competitive positioning")


def build_team_ask_slide() -> Canvas:
    """Close with a financing number that feels like the final decision."""
    canvas = Canvas(1280, 720).background(color=INK)
    canvas = canvas.shape(
        shape="rectangle",
        position=(0, 0),
        width=520,
        height=720,
        color=BLUE,
        animation=Wipe(direction="right", duration=0.4),
    )
    canvas = canvas.text(
        content="VELA",
        font="Roboto",
        size=18,
        color=WHITE,
        weight=700,
        letter_spacing=4,
        position=(80, 55),
    )
    canvas = canvas.text(
        content="$8M",
        font="Roboto",
        size=160,
        color=WHITE,
        weight=500,
        letter_spacing=-7,
        position=(70, 150),
        animation=Fade(duration=0.4),
    )
    canvas = canvas.text(
        content="SERIES A",
        font="Roboto",
        size=28,
        color=WHITE,
        weight=700,
        letter_spacing=3,
        position=(82, 345),
    )
    canvas = canvas.text(
        content="24 months to $8M ARR\nand repeatable enterprise distribution.",
        font="Roboto",
        size=25,
        color="#D7E9FF",
        weight=400,
        line_height=1.35,
        position=(82, 425),
        max_width=360,
    )
    canvas = canvas.text(
        content="USE OF FUNDS",
        font="Roboto",
        size=18,
        color="#D7E9FF",
        weight=700,
        letter_spacing=2,
        position=(82, 525),
    )
    canvas = canvas.text(
        content="45%  Product + AI\n35%  Enterprise GTM\n20%  Security + operations",
        font="Roboto",
        size=21,
        color=WHITE,
        weight=500,
        line_height=1.65,
        position=(82, 555),
    )
    canvas = canvas.text(
        content="FOUNDING TEAM",
        font="Roboto",
        size=18,
        color="#80BFFF",
        weight=700,
        letter_spacing=2,
        position=(600, 105),
    )
    team = [
        ("Maya Chen", "CEO · Product analytics, ex-Atlas"),
        ("Jon Bell", "CTO · Data systems, ex-Vector"),
        ("Priya Shah", "VP GTM · Enterprise SaaS, ex-North"),
    ]
    for index, (name, role) in enumerate(team):
        y = 180 + index * 120
        canvas = canvas.text(
            content=name,
            font="Roboto",
            size=30,
            color=WHITE,
            weight=500,
            position=(600, y),
        )
        canvas = canvas.text(
            content=role,
            font="Roboto",
            size=19,
            color="#A7A7AD",
            weight=400,
            position=(600, y + 45),
        )
    canvas = canvas.text(
        content="Illustrative names, roles, and financing data",
        font="Roboto",
        size=18,
        color="#8E8E93",
        weight=400,
        position=(600, 575),
    )
    return canvas.text(
        content="invest@vela.so",
        font="Roboto",
        size=21,
        color="#80BFFF",
        weight=700,
        position=(1184, 645),
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
        x = 92 + index * 94
        canvas = canvas.shape(
            shape="rectangle",
            position=(x, 610 - height // 2),
            width=62,
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
            position=(x + 31, 625),
            align=("center", "top"),
        )
    return canvas


def add_competition_map(canvas: Canvas) -> Canvas:
    """Place Vela on a simple context-versus-action competitive map."""
    canvas = canvas.shape(
        shape="rectangle",
        position=(92, 300),
        width=570,
        height=320,
        color=WHITE,
        effects=[{"type": "stroke", "width": 1, "color": RULE}],
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(120, 455),
        width=510,
        height=1,
        color=RULE,
    )
    canvas = canvas.shape(
        shape="rectangle",
        position=(375, 325),
        width=1,
        height=265,
        color=RULE,
    )
    points = [
        ("BI", 190, 535, MUTED),
        ("ALERTING", 470, 535, MUTED),
        ("COPILOTS", 475, 390, MUTED),
        ("VELA", 585, 345, BLUE),
    ]
    for label, x, y, color in points:
        canvas = canvas.shape(
            shape="ellipse",
            position=(x, y),
            width=14 if label != "VELA" else 28,
            height=14 if label != "VELA" else 28,
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
        position=(485, 592),
    )
    return canvas.text(
        content="MORE ACTION",
        font="Roboto",
        size=18,
        color=MUTED,
        weight=500,
        letter_spacing=1,
        position=(108, 320),
    )


deck = build_deck()


if __name__ == "__main__":
    main()
