"""모아 — 생활비 데이터로 내일을 설계하는 한국형 투자 제안서."""

import os

from quickthumb import Box, Canvas, Deck, Fade, Wipe
from quickthumb import transitions as tr
from quickthumb.models import Shadow

FILE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(FILE_DIR, "..", "assets")
OUT_HTML = os.path.join(FILE_DIR, "investor_deck.html")
OUT_PPTX = os.path.join(FILE_DIR, "investor_deck.pptx")
PRETENDARD_REGULAR = os.path.join(ASSETS_DIR, "fonts", "Pretendard-Regular.woff2")
PRETENDARD_BOLD = os.path.join(ASSETS_DIR, "fonts", "Pretendard-Bold.woff2")

PAPER = "#EEE9DE"
INK = "#17211D"
GREEN = "#1D4A3C"
ORANGE = "#F45A3A"
MINT = "#B9D9C8"
MUTED = "#68716C"
RULE = "#17211D33"
WHITE = "#FFFDF7"
DROP = Shadow(offset_x=0, offset_y=16, color="#0B171240", blur_radius=28)


def main() -> None:
    """Build and export the complete investor deck."""
    deck = build_deck()
    deck.render(OUT_HTML)
    deck.render(OUT_PPTX)
    print(f"✓ {OUT_HTML}")
    print(f"✓ {OUT_PPTX}")


def build_deck() -> Deck:
    """Return a five-slide editorial investor narrative."""
    cover = build_cover()
    tension = build_tension()
    product = build_product()
    traction = build_traction()
    ask = build_ask()
    return (
        Deck(1280, 720)
        .slide(cover, notes="숫자보다 먼저, 모아가 바꾸려는 생활의 장면을 소개합니다.")
        .slide(
            tension,
            transition=tr.Push(direction="left", duration=0.6),
            notes="소득의 문제가 아니라 불확실성을 해석할 도구가 없다는 점을 강조합니다.",
        )
        .slide(
            product,
            transition=tr.Wipe(direction="up", duration=0.5),
            notes="기록, 예측, 행동이 하나의 짧은 루프로 연결된 제품 경험을 설명합니다.",
        )
        .slide(
            traction,
            transition=tr.Push(direction="left", duration=0.6),
            notes="성장률보다 반복 사용과 실제 절약액을 먼저 보여줍니다.",
        )
        .slide(
            ask,
            transition=tr.Cover(direction="up", duration=0.6),
            notes="18개월의 구체적인 목표와 이번 라운드의 쓰임을 남깁니다.",
        )
    )


def build_cover() -> Canvas:
    """Open on a calm, human promise rather than a category claim."""
    canvas = Canvas(1280, 720).background(color=PAPER)
    canvas = add_header(canvas, "MOA  /  SEED ROUND", "2026. 07")
    canvas.shape(
        shape="ellipse",
        position=(1000, 352),
        width=430,
        height=430,
        color=GREEN,
        align=("center", "middle"),
        animation=Box(direction="in", duration=0.55),
    )
    canvas.shape(
        shape="ellipse",
        position=(1000, 352),
        width=190,
        height=190,
        color=ORANGE,
        align=("center", "middle"),
        animation=Fade(duration=0.4, trigger="after_previous"),
    )
    canvas.text(
        content="돈을 관리하는 일이\n삶을 미루는 일이\n되지 않도록",
        font=PRETENDARD_BOLD,
        size=80,
        color=INK,
        weight=700,
        line_height=1.12,
        letter_spacing=-3,
        position=(72, 152),
        animation=Wipe(direction="up", duration=0.55),
    )
    canvas.text(
        content="생활비 데이터를 오늘의 선택으로 바꾸는 개인 금융 코파일럿",
        font=PRETENDARD_REGULAR,
        size=25,
        color=MUTED,
        position=(76, 514),
        animation=Fade(duration=0.4, trigger="after_previous"),
    )
    canvas.shape(shape="rectangle", position=(72, 636), width=1136, height=1, color=RULE)
    canvas.text(
        content="CONFIDENTIAL",
        font=PRETENDARD_BOLD,
        size=14,
        color=MUTED,
        weight=700,
        letter_spacing=3,
        position=(1208, 664),
        align=("right", "top"),
    )
    return canvas


def add_header(
    canvas: Canvas,
    section: str,
    page: str,
    *,
    accent: str = ORANGE,
    meta: str = MUTED,
) -> Canvas:
    """Add the restrained folio shared by every slide."""
    canvas.text(
        content=section,
        font=PRETENDARD_BOLD,
        size=16,
        color=accent,
        weight=700,
        letter_spacing=3,
        position=(72, 54),
    )
    canvas.text(
        content=page,
        font=PRETENDARD_BOLD,
        size=15,
        color=meta,
        weight=700,
        letter_spacing=2,
        position=(1208, 54),
        align=("right", "top"),
    )
    return canvas


def build_tension() -> Canvas:
    """Frame the problem as uncertainty people feel every day."""
    canvas = Canvas(1280, 720).background(color=INK)
    canvas = add_header(canvas, "01  /  THE TENSION", "02")
    canvas.text(
        content="월급은 숫자인데,\n불안은 감각입니다.",
        font=PRETENDARD_BOLD,
        size=75,
        color=WHITE,
        weight=700,
        line_height=1.14,
        letter_spacing=-3,
        position=(72, 130),
        animation=Wipe(direction="up", duration=0.5),
    )
    canvas.text(
        content="68%",
        font=PRETENDARD_BOLD,
        size=172,
        color=ORANGE,
        weight=700,
        position=(842, 142),
        animation=Box(direction="in", duration=0.5),
    )
    canvas.text(
        content="다음 달 지출을 정확히\n예상하지 못하는 직장인",
        font=PRETENDARD_REGULAR,
        size=23,
        color=MINT,
        line_height=1.4,
        position=(858, 332),
        animation=Fade(duration=0.35, trigger="after_previous"),
    )
    problems = [
        ("01", "흩어진 기록", "카드, 계좌, 메모에\n생활의 맥락이 나뉩니다."),
        ("02", "늦은 알림", "이미 쓴 뒤에야\n예산 초과를 알게 됩니다."),
        ("03", "막연한 조언", "내 일상과 무관한\n평균만 돌아옵니다."),
    ]
    for index, (number, title, body) in enumerate(problems):
        x = 72 + index * 386
        canvas.shape(shape="rectangle", position=(x, 500), width=348, height=1, color="#FFFFFF33")
        canvas.text(
            content=number,
            font=PRETENDARD_BOLD,
            size=16,
            color=ORANGE,
            weight=700,
            position=(x, 532),
        )
        canvas.text(
            content=title,
            font=PRETENDARD_BOLD,
            size=26,
            color=WHITE,
            weight=700,
            position=(x + 52, 526),
        )
        canvas.text(
            content=body,
            font=PRETENDARD_REGULAR,
            size=19,
            color="#C7D0CB",
            line_height=1.45,
            position=(x + 52, 574),
        )
    return canvas


def build_product() -> Canvas:
    """Show the product as one short, legible daily loop."""
    canvas = Canvas(1280, 720).background(color=PAPER)
    canvas = add_header(canvas, "02  /  THE PRODUCT", "03")
    canvas.text(
        content="기록에서 행동까지,\n하루 한 번이면 충분합니다.",
        font=PRETENDARD_BOLD,
        size=59,
        color=INK,
        weight=700,
        line_height=1.18,
        letter_spacing=-2,
        position=(72, 122),
        animation=Fade(duration=0.45),
    )
    canvas.text(
        content="모아는 거래 내역을 보여주는 대신\n오늘 바꿀 수 있는 한 가지를 제안합니다.",
        font=PRETENDARD_REGULAR,
        size=23,
        color=MUTED,
        line_height=1.5,
        position=(790, 146),
    )
    steps = [
        ("01", "모으고", "자동으로 맥락화", GREEN),
        ("02", "내다보고", "7일 뒤를 예측", ORANGE),
        ("03", "바꿉니다", "한 가지 행동 제안", GREEN),
    ]
    for index, (number, title, body, accent) in enumerate(steps):
        x = 72 + index * 386
        canvas.shape(
            shape="rectangle",
            position=(x, 382),
            width=348,
            height=236,
            color=WHITE,
            border_radius=8,
            effects=[DROP],
            animation=Box(direction="in", duration=0.4),
        )
        canvas.shape(
            shape="ellipse",
            position=(x + 48, 430),
            width=56,
            height=56,
            color=accent,
            align=("center", "middle"),
        )
        canvas.text(
            content=number,
            font=PRETENDARD_BOLD,
            size=16,
            color=WHITE,
            weight=700,
            position=(x + 48, 430),
            align=("center", "middle"),
        )
        canvas.text(
            content=title,
            font=PRETENDARD_BOLD,
            size=32,
            color=INK,
            weight=700,
            position=(x + 28, 494),
        )
        canvas.text(
            content=body,
            font=PRETENDARD_REGULAR,
            size=21,
            color=MUTED,
            position=(x + 28, 552),
        )
    return canvas


def build_traction() -> Canvas:
    """Let product behavior, not vanity growth, carry the proof."""
    canvas = Canvas(1280, 720).background(color=GREEN)
    canvas = add_header(canvas, "03  /  MOMENTUM", "04")
    canvas.text(
        content="사람들이 돌아오는 이유는\n절약이 눈에 보이기 때문입니다.",
        font=PRETENDARD_BOLD,
        size=58,
        color=WHITE,
        weight=700,
        line_height=1.18,
        letter_spacing=-2,
        position=(72, 120),
        animation=Wipe(direction="up", duration=0.5),
    )
    metrics = [
        ("4.8만", "월간 활성 사용자"),
        ("71%", "8주차 잔존율"),
        ("₩84,000", "월평균 절약액"),
    ]
    for index, (value, label) in enumerate(metrics):
        x = 72 + index * 386
        canvas.shape(shape="rectangle", position=(x, 390), width=348, height=1, color="#FFFFFF44")
        canvas.text(
            content=value,
            font=PRETENDARD_BOLD,
            size=69,
            color=ORANGE if index == 2 else WHITE,
            weight=700,
            letter_spacing=-2,
            position=(x, 432),
            animation=Box(direction="in", duration=0.4),
        )
        canvas.text(
            content=label,
            font=PRETENDARD_REGULAR,
            size=21,
            color=MINT,
            position=(x, 526),
        )
    canvas.text(
        content="“처음으로 다음 달이 덜 막막해졌어요.”  —  베타 사용자 인터뷰",
        font=PRETENDARD_REGULAR,
        size=21,
        color="#E7F0EB",
        position=(72, 650),
        italic=True,
        animation=Fade(duration=0.4, trigger="after_previous"),
    )
    return canvas


def build_ask() -> Canvas:
    """Close with a concrete destination and a disciplined use of funds."""
    canvas = Canvas(1280, 720).background(color=ORANGE)
    canvas = add_header(canvas, "04  /  THE ASK", "05", accent=INK, meta=INK)
    canvas.text(
        content="18개월 뒤,\n100만 명의 내일을\n조금 더 선명하게.",
        font=PRETENDARD_BOLD,
        size=76,
        color=INK,
        weight=700,
        line_height=1.1,
        letter_spacing=-3,
        position=(72, 128),
        animation=Box(direction="in", duration=0.55),
    )
    canvas.shape(
        shape="rectangle",
        position=(818, 132),
        width=390,
        height=430,
        color=INK,
        border_radius=8,
        effects=[DROP],
    )
    canvas.text(
        content="SEED ROUND",
        font=PRETENDARD_BOLD,
        size=16,
        color=MINT,
        weight=700,
        letter_spacing=3,
        position=(858, 176),
    )
    canvas.text(
        content="30억 원",
        font=PRETENDARD_BOLD,
        size=65,
        color=WHITE,
        weight=700,
        position=(856, 228),
    )
    canvas.shape(shape="rectangle", position=(858, 324), width=310, height=1, color="#FFFFFF33")
    canvas.text(
        content="제품  45%\n데이터  35%\n시장 확장  20%",
        font=PRETENDARD_REGULAR,
        size=23,
        color="#D8E3DD",
        line_height=1.8,
        position=(858, 358),
    )
    canvas.text(
        content="hello@moa.money  ·  moa.money/deck",
        font=PRETENDARD_BOLD,
        size=18,
        color=INK,
        weight=700,
        letter_spacing=1,
        position=(72, 650),
        animation=Fade(duration=0.4, trigger="after_previous"),
    )
    return canvas


if __name__ == "__main__":
    main()
