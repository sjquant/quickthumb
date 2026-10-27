"""A reusable moving layer reveals two targets without painting the matte itself."""

from quickthumb import AnimationSpec, Canvas, KeyframeSpec, PositionTrack, TimingSpec, TrackMatte


def build_scene():
    canvas = Canvas(480, 180)
    canvas.shape(
        "ellipse",
        (30, 20),
        120,
        120,
        color="#FFFFFF",
        id="reveal",
        animation=AnimationSpec(
            timing=TimingSpec(duration=1.5),
            easing="ease_in_out",
            tracks=[
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=1.5, value=(280, 0)),
                    ]
                )
            ],
        ),
    )
    canvas.shape("rectangle", (0, 0), 480, 90, color="#42CEB7", mask=TrackMatte(layer="reveal"))
    canvas.shape("rectangle", (0, 90), 480, 90, color="#315D8E", mask=TrackMatte(layer="reveal"))
    return canvas


if __name__ == "__main__":
    build_scene().export("track-mattes.gif")
