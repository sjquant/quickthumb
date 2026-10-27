"""Compare actual OFF/8-sample GIF exposures of the same fast moving marker.

Run from the repository root: uv run python examples/motion_blur.py
The exports share one scene, 12 fps and standard rendering quality.
"""

from pathlib import Path

from quickthumb import (
    AnimationSpec,
    Canvas,
    Deck,
    GifOptions,
    KeyframeSpec,
    MotionBlur,
    PositionTrack,
)
from quickthumb.transitions import Cut


def build_deck() -> Deck:
    canvas = (
        Canvas(512, 288)
        .background(color="#000000")
        .shape(
            "rectangle",
            (44, 100),
            40,
            88,
            "#FFFFFF",
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=2, value=(340, 0)),
                    ]
                ),
                easing="linear",
            ),
        )
    )
    return Deck(512, 288).slide(canvas, duration=2, transition=Cut(advance_after=2))


def main() -> None:
    output = Path(__file__).resolve().parent / "output"
    output.mkdir(parents=True, exist_ok=True)
    for samples in (None, 8):
        result = build_deck().export(
            output / f"motion-blur-{samples or 'off'}.gif",
            animation=GifOptions(
                fps=12,
                motion_blur=MotionBlur(samples=samples) if samples else None,
            ),
        )
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
