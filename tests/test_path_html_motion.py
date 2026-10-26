"""Native HTML SVG stroke motion preserves paint and declares bounded fallback routes."""

import re
import xml.etree.ElementTree as ET

import pytest
from quickthumb import (
    AnimationSpec,
    Canvas,
    DashOffsetTrack,
    ExportPolicy,
    KeyframeSpec,
    TimingSpec,
    TrimEndTrack,
    TrimOffsetTrack,
    TrimStartTrack,
)
from quickthumb.errors import RenderingError

from tests.test_anchor_html import _nodes
from tests.test_path_motion import motion, track


def scene(animation=None, **style):
    return Canvas(240, 120).path(
        "M10 30L50 5L90 30",
        (10, 10),
        200,
        80,
        "#CCDDFF",
        view_box=(0, 0, 100, 40),
        stroke="#227755",
        stroke_width=3,
        animation=animation,
        **style,
    )


def svg_paths(html):
    return [
        path
        for source in re.findall(r"<svg\b.*?</svg>", html, re.DOTALL)
        for path in ET.fromstring(source).findall("{http://www.w3.org/2000/svg}path")
    ]


def test_native_trim_separates_fill_and_retains_clock(tmp_path):
    """A delayed trim reveal keeps fill static and targets only native stroke styles."""
    # Given: outgoing holds, authored trim, and a relative delay on one canonical timeline
    end = TrimEndTrack(
        keyframes=[
            KeyframeSpec(time=0, value=0.25, hold=True),
            KeyframeSpec(time=0.5, value=0.75),
            KeyframeSpec(time=1, value=1),
        ]
    )
    animation = AnimationSpec.timeline(
        end, timing=TimingSpec(duration=1, delay=0.2, trigger="on_click"), easing="ease_in"
    )
    canvas = scene(animation, trim_end=0.6)

    # When: strict native export emits the real SVG and existing CSS timeline contract
    result = canvas.export(
        tmp_path / "native.html", policy=ExportPolicy(unsupported_motion="error")
    )
    html = (tmp_path / "native.html").read_text()
    paths = svg_paths(html)
    (node,) = _nodes(html)

    # Then: fill cannot inherit animated dash state, and the authored pre-delay state stays visible
    assert len(paths) == 2 and paths[0].attrib["fill"] == "#CCDDFF"
    assert "stroke" not in paths[0].attrib and "pathLength" not in paths[0].attrib
    assert paths[1].attrib["fill"] == "none" and paths[1].attrib["pathLength"] == "1"
    assert node["t"] == [paths[1].attrib["id"]]
    assert node["delay"] == 0.2 and node["d"] == 1 and node["tr"] == "on_click"
    assert node["initial"]["stroke-dasharray"] == "0.6px 1.4px"
    assert node["final"]["stroke-dasharray"] == "1px 1px"
    assert "50%{stroke-dasharray:0.75px" in html
    assert "stroke-dasharray:0.25px 1.75px" in html
    assert "data:image/png" not in html
    rows = [row for row in result.capability_report if row.feature == "trim_end"]
    assert rows[0].support == "native" and rows[0].fallback is None
    assert "120 Hz" in rows[0].message and "4097-stop" in rows[0].message


def test_dash_motion_keeps_authored_local_pattern():
    """Native dash-offset motion retains odd local dash lengths and relative phase composition."""
    # Given: two ordered relative phase tracks over an authored odd pattern
    replace = track(DashOffsetTrack, 0, 12)
    add = DashOffsetTrack(keyframes=[KeyframeSpec(time=0, value=-2)], blend="add")
    canvas = scene(motion(replace, add), dash_array=(5, 2, 1), dash_offset=-3, line_cap="round")

    # When: native SVG stroke attributes and timeline final state are observed
    html = canvas.to_html()
    stroke = svg_paths(html)[1]
    (node,) = _nodes(html)

    # Then: dash units remain local SVG distances without trim normalization
    assert stroke.attrib["stroke-dasharray"] == "5 2 1"
    assert "pathLength" not in stroke.attrib
    assert node["initial"] == {"stroke-dashoffset": "-3px"}
    assert node["final"] == {"stroke-dashoffset": "7px"}
    assert all(row.support == "native" for row in canvas.validate_export("html"))
    assert any(row.fallback == "static" for row in canvas.validate_export("pptx"))


def test_start_and_offset_motion_keep_ordered_window():
    """Native trim start and additive offset tracks emit their combined normalized cut positions."""
    # Given: a quarter-length window moving within the open contour
    start = track(TrimStartTrack, 0.1, 0.2)
    offset = TrimOffsetTrack(keyframes=[KeyframeSpec(time=0, value=0.05)], blend="add")
    canvas = scene(motion(start, offset), trim_start=0.1, trim_end=0.5, trim_offset=0.1)

    # When/Then: final native dash geometry uses absolute boundaries plus relative turns
    html = canvas.to_html()
    (node,) = _nodes(html)
    assert node["final"]["stroke-dasharray"] == "0.3px 1.7px"
    assert float(node["final"]["stroke-dashoffset"].removesuffix("px")) == pytest.approx(-0.35)


@pytest.mark.parametrize(
    ("style", "animation", "reason"),
    [
        (
            {"dash_array": (5, 3), "dash_offset": 1e8},
            motion(track(DashOffsetTrack, 0, 1)),
            "phase exceeds numeric precision",
        ),
        (
            {"dash_array": (5, 3), "dash_offset": 2**18},
            motion(
                track(DashOffsetTrack, 0, 2**18),
                DashOffsetTrack(
                    keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=2**19)],
                    blend="add",
                ),
            ),
            "phase exceeds numeric precision",
        ),
        ({"trim_start": 0.75, "trim_end": 0.25}, None, "nonwrapping"),
        (
            {"trim_start": 0.75, "trim_end": 0.25},
            motion(track(TrimStartTrack, 0, 0.1), track(TrimEndTrack, 0.5, 1)),
            "authored window",
        ),
        ({"line_cap": "round"}, motion(track(TrimEndTrack, 0, 1)), "butt caps"),
        ({"dash_array": (5, 3)}, motion(track(TrimEndTrack, 0, 1)), "authored dashes"),
        ({}, [motion(track(TrimEndTrack, 0, 1))], "one stroke-property"),
        (
            {},
            AnimationSpec.timeline(track(TrimEndTrack, 0, 1), easing="ease_out_back"),
            "overshooting",
        ),
        (
            {},
            AnimationSpec.timeline(track(TrimEndTrack, 0, 1), timing=TimingSpec(duration=40)),
            "4097-stop",
        ),
    ],
)
def test_unrepresentable_native_motion_declares_static_fallback(style, animation, reason, tmp_path):
    """Unsupported stroke combinations keep authored raster output and fail strict policy."""
    # Given: a path combination outside the bounded native admission rules
    canvas = scene(animation, **style)

    # When: fallback export reports its real route and strict export inspects the same admission
    rows = canvas.validate_export("html")
    assert any(
        row.feature == "path" and row.fallback == "rasterize" and reason in row.message
        for row in rows
    )
    html = canvas.to_html()
    assert "data:image/png" in html and not svg_paths(html)
    target = tmp_path / "preserved.html"
    target.write_text("keep")
    with pytest.raises(RenderingError, match=reason):
        canvas.export(target, policy=ExportPolicy(unsupported_motion="error"))

    # Then: no fake entrance animation is registered and strict rejection preserves prior output
    assert not _nodes(html)
    assert target.read_text() == "keep"


def test_complex_and_degenerate_contours_do_not_receive_native_motion():
    """Complex contours and zero-length strokes retain explicit authored-static fallback."""
    # Given: motion whose contour semantics cannot use one native SVG trim window
    for data in ("M0 10H40M50 10H90", "M10 10H40V30Z", "M10 10L10 10"):
        canvas = Canvas(100, 40).path(
            data,
            (0, 0),
            100,
            40,
            None,
            stroke="#227755",
            line_cap="round",
            animation=motion(track(TrimEndTrack, 0, 1)),
        )

        # When/Then: actual HTML stays authored static and diagnostics name the fallback
        assert "data:image/png" in canvas.to_html()
        assert any(
            row.feature == "path" and row.fallback == "rasterize"
            for row in canvas.validate_export("html")
        )
