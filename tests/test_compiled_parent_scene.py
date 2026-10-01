"""Complete scene scheduling preserves parent motion ownership."""

from typing import Any, cast

from quickthumb import Canvas, Dissolve, Fade
from quickthumb import _export_video as video


def test_mixed_scene_schedules_once_and_preserves_null_clocks_and_dissolve_seeds(monkeypatch):
    canvas = (
        Canvas(120, 90)
        .background(color="#112233")
        .shape("rectangle", (5, 5), 12, 10, "#CC0000", animation=Fade(duration=0.4))
        .null(id="root", animation=Fade(duration=0.6, trigger="with_previous"))
        .shape(
            "rectangle",
            (25, 20),
            18,
            14,
            "#00CC00",
            parent="root",
            animation=Fade(duration=0.3, delay=0.1, trigger="on_click"),
        )
        .shape(
            "rectangle",
            (55, 45),
            10,
            15,
            "#0000CC",
            animation=Fade(duration=0.2, trigger="with_previous"),
        )
        .null(id="clock", animation=Fade(duration=0.5, trigger="after_previous"))
        .shape(
            "rectangle",
            (75, 65),
            22,
            18,
            "#CCCC00",
            parent="root",
            animation=Dissolve(duration=0.25, trigger="after_previous"),
        )
    )
    reference = Canvas.from_json(canvas.to_json())
    for layer in reference.layers:
        if getattr(layer, "parent", None):
            cast(Any, layer).parent = None
    expected = video._SlideAnimator(reference, {})
    schedule = video._schedule_units
    calls = []

    def schedule_once(units):
        calls.append(tuple(id(unit) for unit in units))
        return schedule(units)

    monkeypatch.setattr(video, "_schedule_units", schedule_once)
    animator = video._SlideAnimator(canvas, {})
    assert animator.duration == expected.duration == 1.75
    assert [len(unit.nodes) for unit in animator._units] == [0, 1, 1, 1, 1, 1, 1]
    assert [unit.nodes[0].start for unit in animator._units[1:]] == [0, 0, 0.6, 0.6, 1, 1.5]
    assert [unit.seed for unit in animator._units] == [31, 32, 33, 34, 35, 36, 37]
    assert animator._static_plate is not None
    assert all(unit in animator._frame_units for unit in animator._parent_units.values())
    for time in (1.625, 0, 0.3, 0.7, 1, 1.75, 1.625):
        assert animator.frame_at(time).tobytes() == expected.frame_at(time).tobytes()
    assert calls == [tuple(id(unit) for unit in animator._units)]
    assert [len(unit.nodes) for unit in animator._units] == [0, 1, 1, 1, 1, 1, 1]
