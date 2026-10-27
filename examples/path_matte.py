"""A moving path with a hole reveals two targets through the existing matte API."""

from quickthumb import AnimationSpec, Canvas, KeyframeSpec, PositionTrack, TimingSpec, TrackMatte


def build_scene():
    canvas = Canvas(240, 120).path(
        "M20 60A40 40 0 1 1 100 60A40 40 0 1 1 20 60ZM40 60A20 20 0 1 1 80 60A20 20 0 1 1 40 60Z",
        (0, 0),
        240,
        120,
        "#FFFFFF",
        id="reveal",
        animation=AnimationSpec.timeline(
            PositionTrack(
                keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=1, value=(120, 0))]
            ),
            timing=TimingSpec(duration=1),
            easing="linear",
        ),
    )
    canvas.shape("rectangle", (0, 0), 240, 60, color="#42CEB7", mask=TrackMatte(layer="reveal"))
    canvas.shape("rectangle", (0, 60), 240, 60, color="#315D8E", mask=TrackMatte(layer="reveal"))
    return canvas


if __name__ == "__main__":
    build_scene().export("path-matte.gif")
