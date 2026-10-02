"""Bounded sampled affine HTML uses the same graph without matrix decomposition."""

import base64
import math
import re
from io import BytesIO

import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    Canvas,
    ExportPolicy,
    KeyframeSpec,
    OpacityTrack,
    PositionTrack,
    RotationTrack,
    ScaleTrack,
    ScaleXTrack,
    ScaleYTrack,
    TimingSpec,
)
from quickthumb._export_base import _motion_number
from quickthumb._export_html import HtmlExporter
from quickthumb._export_video import _SlideAnimator
from quickthumb._parent_export import bake_parent_html, parent_html_sampling
from quickthumb._parent_render import multiply, translate
from quickthumb.errors import RenderingError


def track(cls, first, last=None, duration=1):
    return cls(
        keyframes=[
            KeyframeSpec(time=0, value=first),
            KeyframeSpec(time=duration, value=first if last is None else last),
        ]
    )


def motion(*tracks, duration=1, **kwargs):
    return AnimationSpec.timeline(
        *tracks, timing=TimingSpec(duration=duration, **kwargs), easing="linear"
    )


def scene(animation=None):
    return (
        Canvas(220, 160)
        .null((100, 80), id="root", animation=animation)
        .null((20, -15), id="middle", parent="root", rotation=30)
        .shape("rectangle", (10, 5), 20, 10, "#FF0000", parent="middle", id="child")
    )


def bake(canvas):
    sampling = parent_html_sampling(canvas)
    assert sampling.problem is None
    return bake_parent_html(canvas, sampling.times)


def css_row(row):
    return {
        f"--qt-parent-{name}": _motion_number(value)
        for name, value in zip(("a", "b", "c", "d", "e", "f", "opacity"), row, strict=True)
    }


def source_image(source):
    return Image.open(BytesIO(source.png)).convert("RGBA")


def reference_row(node, sample):
    paint, _, state, _ = sample
    matrix = multiply(paint, translate(-node.padding, -node.padding))
    opacity = 1.0
    if state.hidden:
        opacity = 0.0
    elif state.canonical:
        opacity = min(1.0, max(0.0, state.canonical.layer.opacity)) * state.canonical.alpha_scale
    return (*matrix, opacity)


def test_three_level_shear_and_css_order_match_independent_corner_math():
    canvas = scene(motion(track(RotationTrack, 45), track(ScaleXTrack, 2), track(ScaleYTrack, 0.5)))
    baked = bake(canvas)
    source = baked.sources[id(canvas.layers[-1])]
    values = list(css_row(source.rows[0]).values())
    a, b, c, d, e, f, opacity = map(float, values)
    x = 20 + 10 * math.cos(math.pi / 6) - 5 * math.sin(math.pi / 6)
    y = -15 + 10 * math.sin(math.pi / 6) + 5 * math.cos(math.pi / 6)
    expected = (100 + (2 * x - 0.5 * y) / math.sqrt(2), 80 + (2 * x + 0.5 * y) / math.sqrt(2))
    # Locate the authored 20-by-10 rectangle inside its padded source image.
    px, py = (source.width - 20) / 2, (source.height - 10) / 2
    actual = (a * px + b * py + c, d * px + e * py + f)
    assert actual == pytest.approx(expected)
    assert a * b + d * e != pytest.approx(0)  # nonorthogonal columns retain shear
    assert opacity == 1
    stage = HtmlExporter(canvas).render_stage()
    assert "matrix(var(--qt-parent-a),var(--qt-parent-d),var(--qt-parent-b)" in stage.body
    assert "transform-origin:0 0" in stage.body
    assert sum(item.startswith("@property") for item in stage.keyframes) == 7
    assert stage.timeline[0]["initial"]["--qt-parent-a"] == values[0]
    assert stage.timeline[0]["final"] == css_row(source.rows[-1])


def test_stable_reflection_does_not_fade_opacity():
    canvas = scene(motion(track(ScaleXTrack, -1, -2)))
    baked = bake(canvas)
    rows = [css_row(row) for row in baked.sources[id(canvas.layers[-1])].rows]
    assert {row["--qt-parent-opacity"] for row in rows} == {"1"}
    assert float(rows[0]["--qt-parent-a"]) < 0
    assert float(rows[-1]["--qt-parent-a"]) == 2 * float(rows[0]["--qt-parent-a"])


@pytest.mark.parametrize(
    "first,last,easing",
    [(0, 0, "linear"), (1, -1, "linear"), (1, 0, "linear"), (1, 0.01, "ease_out_back")],
)
def test_axis_collapse_is_honest_static_fallback(first, last, easing):
    animation = motion(track(ScaleXTrack, first, last), track(ScaleYTrack, 1e16, 1e16))
    animation.easing = easing
    canvas = scene(animation)
    assert "collapse" in (parent_html_sampling(canvas).problem or "")
    assert not HtmlExporter(canvas).render_stage().timeline
    assert all(item.fallback == "static" for item in canvas.validate_export("html"))


def test_own_opacity_multiplies_once_and_parent_opacity_is_not_inherited():
    canvas = (
        Canvas(140, 130)
        .shape(
            "rectangle",
            (20, 20),
            10,
            10,
            "#FFFFFF",
            id="root",
            animation=motion(track(OpacityTrack, 0)),
        )
        .shape(
            "rectangle",
            (20, 0),
            10,
            10,
            "#FF0000",
            parent="root",
            opacity=0.5,
            animation=motion(track(OpacityTrack, 0.5)),
        )
    )
    stage = HtmlExporter(canvas).render_stage()
    assert [node["initial"]["--qt-parent-opacity"] for node in stage.timeline] == ["0", "0.5"]
    images = re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", stage.body)
    child = Image.open(BytesIO(base64.b64decode(images[1]))).convert("RGBA")
    assert child.getchannel("A").getextrema()[1] in {127, 128}


def test_different_durations_share_one_clock_and_keep_all_knots():
    canvas = scene(motion(track(RotationTrack, 0, 90, duration=2), duration=2))
    canvas.layers[-1].animation = motion(track(PositionTrack, (0, 0), (20, 0)))
    sampling = parent_html_sampling(canvas)
    assert 1 in sampling.times and sampling.times[-1] == 2
    stage = HtmlExporter(canvas).render_stage()
    assert [item["d"] for item in stage.timeline] == [2]
    second = canvas.layers[-1].model_copy(update={"id": "second"})
    canvas.layers = [*canvas.layers, second]
    stage = HtmlExporter(canvas).render_stage()
    assert [item["tr"] for item in stage.timeline] == ["after_previous", "with_previous"]
    assert {item["d"] for item in stage.timeline} == {2}


@pytest.mark.parametrize(
    "easing",
    [
        "linear",
        "ease",
        "ease_in_out",
        "ease_in_out_quint",
        "ease_in_back",
        "ease_out_back",
        "ease_in_out_back",
    ],
)
def test_short_full_rotation_cannot_alias_to_identical_endpoints(easing):
    animation = motion(track(RotationTrack, 0, 360, duration=0.001), duration=0.001)
    animation.easing = easing
    canvas = scene(animation)
    baked = bake(canvas)
    assert len(baked.times) >= 121
    rows = [css_row(row) for row in baked.sources[id(canvas.layers[-1])].rows]
    assert min(float(row["--qt-parent-a"]) for row in rows) < 0
    assert max(float(row["--qt-parent-a"]) for row in rows) > 0


@pytest.mark.parametrize(
    "kind",
    [
        "delay",
        "trigger",
        "compose",
        "preset",
        "uniform_zero",
        "uniform_back",
        "orient",
        "unrelated",
        "unused_null",
        "visualization",
    ],
)
def test_ineligible_clocks_and_sources_use_explicit_whole_scene_static(kind):
    canvas = scene(motion(track(RotationTrack, 0, 90)))
    animation = canvas.layers[0].animation
    if kind == "delay":
        animation.timing.delay = 0.1
    elif kind == "trigger":
        animation.timing.trigger = "on_click"
    elif kind == "compose":
        canvas.layers[0].animation = [animation, animation]
    elif kind == "preset":
        canvas.layers[0].animation = AnimationSpec.fade()
    elif kind == "uniform_zero":
        canvas.layers[0].animation = motion(track(ScaleTrack, 1, -1))
    elif kind == "uniform_back":
        canvas.layers[0].animation = motion(track(ScaleTrack, 1, 2))
        canvas.layers[0].animation.easing = "ease_in_back"
    elif kind == "orient":
        path = track(PositionTrack, (0, 0), (5, 5))
        path.auto_orient = True
        canvas.layers[0].animation = motion(path)
    elif kind == "unrelated":
        canvas.shape("rectangle", (0, 0), 4, 4, "#0000FF", animation=animation)
    elif kind == "unused_null":
        canvas.null(id="unused", animation=animation)
    else:
        canvas.qr_code("hello", position=(0, 0), parent="root", animation=AnimationSpec.qr_reveal())
    assert parent_html_sampling(canvas).problem
    stage = HtmlExporter(canvas).render_stage()
    assert not stage.timeline
    assert len(re.findall("data:image/png;base64,", stage.body)) == 1
    reports = canvas.validate_export("html")
    assert all(item.support == "fallback" and item.fallback == "static" for item in reports)
    with pytest.raises(RenderingError, match="authored-static"):
        canvas.to_html(policy=ExportPolicy(unsupported_motion="error"))


def test_bounded_sampling_falls_back_before_allocating_sources(monkeypatch):
    from quickthumb import _parent_export

    canvas = scene(motion(track(RotationTrack, 0, 1e9)))
    monkeypatch.setattr(canvas, "_render_to_image", lambda **_: pytest.fail("source allocation"))
    assert "4097" in (parent_html_sampling(canvas).problem or "")
    canvas.layers[0].animation = motion(track(RotationTrack, 0, 90))
    monkeypatch.setattr(_parent_export, "MAX_PARENT_ROWS", 1)
    assert "32768" in (parent_html_sampling(canvas).problem or "")


@pytest.mark.parametrize(
    "policy",
    [
        ExportPolicy(reduced_motion=True),
        ExportPolicy(unsupported_motion="static"),
        ExportPolicy(unsupported_motion="rasterize"),
    ],
)
def test_explicit_static_policies_match_report_and_authored_pixels(policy):
    canvas = scene(motion(track(PositionTrack, (50, 0), (100, 0))))
    html = canvas.to_html(policy=policy)
    data = re.findall(r"data:image/png;base64,([A-Za-z0-9+/=]+)", html)
    actual = Image.open(BytesIO(base64.b64decode(data[0]))).convert("RGBA")
    assert actual.tobytes() == canvas._render_to_image().tobytes()
    assert all(item.fallback == "static" for item in canvas.validate_export("html", policy))


def test_eligible_support_is_partial_and_strict_export_preserves_destination(tmp_path):
    canvas = scene(motion(track(RotationTrack, 0, 30)))
    assert all(
        item.support == "partial" and item.fallback is None
        for item in canvas.validate_export("html")
    )
    path = tmp_path / "existing.html"
    path.write_bytes(b"existing")
    with pytest.raises(RenderingError, match="sampled approximation"):
        canvas.export(path, policy=ExportPolicy(unsupported_motion="error"))
    assert path.read_bytes() == b"existing"


def test_sampling_failure_always_cleans_up_render_context(monkeypatch):
    from quickthumb._parent_render import ParentRenderPlan

    canvas = scene(motion(track(RotationTrack, 0, 30)))
    closed = []
    monkeypatch.setattr(canvas._ctx, "close_video_decoders", lambda: closed.append(True))
    monkeypatch.setattr(
        ParentRenderPlan, "sample", lambda *_: (_ for _ in ()).throw(ValueError("sample"))
    )
    with pytest.raises(ValueError, match="sample"):
        HtmlExporter(canvas).render_stage()
    assert canvas._ctx.motion_time is None and closed


@pytest.mark.parametrize("null_only", [False, True])
def test_invisible_hierarchy_keeps_its_clock(null_only):
    from quickthumb._export_video import _SlideAnimator

    canvas = Canvas(140, 130).null(id="root", animation=motion(track(RotationTrack, 0, 30)))
    if null_only:
        canvas.null(id="child", parent="root")
    else:
        canvas.shape("rectangle", (0, 0), 10, 10, "#FF0000", parent="root", opacity=0)
    stage = HtmlExporter(canvas).render_stage()
    assert stage.timeline[0]["d"] == _SlideAnimator(canvas, {}).duration == 1
    assert len(stage.timeline) == 1
    assert 'data-qt-parent-clock="1"' in stage.body
    assert "<img " not in stage.body


def test_leading_animated_null_is_not_a_backdrop_visual():
    from quickthumb import BackdropBlur

    canvas = (
        Canvas(140, 130)
        .null(id="root", animation=motion(track(RotationTrack, 0, 30)))
        .background(color="#112233")
        .shape("rectangle", (0, 0), 100, 80, "#FFFFFF", effects=[BackdropBlur(radius=2)])
        .shape("rectangle", (20, 10), 10, 10, "#FF0000", parent="root")
    )
    stage = HtmlExporter(canvas).render_stage()
    assert len(stage.timeline) == 1
    assert stage.body.count("data:image/png;base64,") == 2


def test_video_sources_fall_back_without_opening_assets():
    canvas = Canvas(140, 130).null(id="root").video("missing.mp4", (0, 0), 20, 20, parent="root")
    assert "static local sources" in (parent_html_sampling(canvas).problem or "")


@pytest.mark.parametrize("invisible", [False, True])
def test_runtime_preserves_group_reset_finish_and_stale_callback_boundaries(invisible):
    import json
    import subprocess
    from importlib.resources import files

    canvas = scene(motion(track(RotationTrack, 0, 90), track(ScaleXTrack, -1, -2)))
    canvas.shape("ellipse", (0, 0), 10, 10, "#00FF00", parent="root")
    if invisible:
        canvas.layers[-1].opacity = canvas.layers[-2].opacity = 0
    nodes = HtmlExporter(canvas).render_stage().timeline
    script = r"""
const assert=require('node:assert/strict');
const input=JSON.parse(require('fs').readFileSync(0,'utf8'));
const timers=[];const CSS={escape:x=>x};
function setTimeout(fn,delay){timers.push({fn,delay});}
eval(input.runtime);
const elements={};const values={};
for(const node of input.nodes){for(const id of node.t){
  values[id]={...node.initial};const listeners=new Set();
  elements[id]={listeners,style:{opacity:'var(--qt-parent-opacity)',
    setProperty:(k,v)=>{values[id][k]=String(v);}},
    addEventListener:(_,fn)=>listeners.add(fn),removeEventListener:(_,fn)=>listeners.delete(fn),
    get offsetWidth(){return 20;}};
}}
const stage={getAttribute:()=>JSON.stringify(input.nodes),querySelector:s=>elements[s.slice(1)]};
const tl=new qtTimeline(stage);
function check(which){for(const node of input.nodes){for(const id of node.t){
  const actual=Object.fromEntries(Object.keys(node[which]).map(k=>[k,values[id][k]]));
  assert.deepEqual(actual,node[which]);assert.equal(elements[id].style.visibility,'visible');
}}}
async function drain(){for(const timer of timers.splice(0))timer.fn();await Promise.resolve();}
(async()=>{
  tl.reset();check('initial');assert.equal(tl.position(),0);
  let playing=tl.advance();check('initial');assert.ok(timers.every(t=>t.delay===1000));
  let stale=Object.values(elements).flatMap(el=>[...el.listeners]);
  tl.reset();check('initial');assert.equal(tl.position(),0);
  stale.forEach(fn=>fn());await drain();await playing;check('initial');
  assert.equal(tl.position(),0);
  playing=tl.advance();tl.finish();check('final');
  await drain();await playing;check('final');assert.equal(tl.position(),input.nodes.length);
  tl.setPosition(0);check('initial');
  tl.setPosition(input.nodes.length);check('final');
  tl.reset();playing=tl.start();await drain();await playing;
  check('final');assert.equal(tl.position(),input.nodes.length);
  for(const el of Object.values(elements))assert.equal(el.listeners.size,0);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run(
        ["node", "-e", script],
        input=json.dumps(
            {
                "nodes": nodes,
                "runtime": files("quickthumb.html").joinpath("timeline.js").read_text(),
            }
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_sampled_css_matches_graph_at_every_shared_observation():
    from examples.parent_transforms import build_scene

    canvas = build_scene()
    baked = bake(canvas)
    animator = _SlideAnimator(canvas, {})
    plan = next(unit.parent_plan for unit in animator._units if unit.parent_plan is not None)
    for index, time in enumerate(baked.times):
        sampled = plan.sample(time)
        for layer_id, source in baked.sources.items():
            node = plan.nodes[layer_id]
            assert source.rows[index] == reference_row(node, sampled[id(node)])
    assert len(baked.times) <= 4097


def test_no_motion_and_instant_track_scenes_need_no_clock():
    canvas = scene()
    assert not HtmlExporter(canvas).render_stage().timeline
    canvas.layers[0].animation = AnimationSpec.timeline(
        RotationTrack(keyframes=[KeyframeSpec(time=0, value=45)])
    )
    stage = HtmlExporter(canvas).render_stage()
    assert not stage.timeline and "data-qt-parent-node" in stage.body


def test_nulls_cannot_bypass_graph_evaluation_budget(monkeypatch):
    from quickthumb import _parent_export

    canvas = scene(motion(track(RotationTrack, 0, 30)))
    monkeypatch.setattr(_parent_export, "MAX_PARENT_EVALUATIONS", 2)
    assert "graph evaluations" in (parent_html_sampling(canvas).problem or "")


def test_example_numeric_css_interpolation_has_small_midpoint_error():
    from examples.parent_transforms import build_scene

    canvas = build_scene()
    baked = bake(canvas)
    animator = _SlideAnimator(canvas, {})
    plan = next(unit.parent_plan for unit in animator._units if unit.parent_plan is not None)
    maximum = 0
    for index, (left, right) in enumerate(zip(baked.times, baked.times[1:], strict=False)):
        sample = plan.sample((left + right) / 2)
        for layer_id, source in baked.sources.items():
            node = plan.nodes[layer_id]
            first = [float(value) for value in css_row(source.rows[index]).values()][:6]
            last = [float(value) for value in css_row(source.rows[index + 1]).values()][:6]
            css = [(a + b) / 2 for a, b in zip(first, last, strict=True)]
            exact = [
                float(value) for value in css_row(reference_row(node, sample[id(node)])).values()
            ][:6]
            for x, y in [(0, 0), (source.width, source.height)]:
                maximum = max(
                    maximum,
                    math.hypot(
                        (css[0] - exact[0]) * x + (css[1] - exact[1]) * y + css[2] - exact[2],
                        (css[3] - exact[3]) * x + (css[4] - exact[4]) * y + css[5] - exact[5],
                    ),
                )
    # A numerical fixture regression, not a general browser/screen-space guarantee.
    assert maximum < 0.01


def test_baked_values_release_graph_and_remain_usable_without_sampling(monkeypatch):
    import gc
    import pickle
    import weakref

    from quickthumb import _export_video

    canvas = scene(motion(track(RotationTrack, 0, 30)))
    canvas.shape("rectangle", (0, 0), 10, 10, "#000000", parent="root", opacity=0)
    expected = HtmlExporter(canvas).render_stage()
    references = []

    def prepare(*args, **kwargs):
        animator = _SlideAnimator(*args, **kwargs)
        plan = next(unit.parent_plan for unit in animator._units if unit.parent_plan is not None)
        references.extend(weakref.ref(item) for item in (animator, plan, *animator._units))
        for node in plan.nodes.values():
            references.append(weakref.ref(node))
            if node.image is not None:
                references.append(weakref.ref(node.image))
            if node.source is not None:
                references.append(weakref.ref(node.source))
        return animator

    monkeypatch.setattr(_export_video, "_SlideAnimator", prepare)
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        baked = bake(canvas)
        assert references and all(reference() is None for reference in references)
    finally:
        if was_enabled:
            gc.enable()
    assert baked.layer_ids == frozenset(id(layer) for layer in canvas.layers)
    assert set(baked.sources) == {id(canvas.layers[2])}
    source = baked.sources[id(canvas.layers[2])]
    assert source_image(source).size == (source.width, source.height)
    assert len(source.rows) == len(baked.times)
    assert all(len(row) == 7 for row in source.rows)
    # A serialization round-trip cannot retain callbacks, iterators or graph objects.
    restored = pickle.loads(pickle.dumps(baked))
    assert restored == baked
    monkeypatch.setattr(
        _export_video, "_SlideAnimator", lambda *_: pytest.fail("emission reopened the graph")
    )
    exporter = HtmlExporter(Canvas(canvas.width, canvas.height))
    for layer in canvas.layers:
        if source := restored.sources.get(id(layer)):
            exporter._emit_parent_source(source, restored.times)
    exporter._emit_parent_clock(restored.times[-1])
    assert "\n".join(exporter._body) == expected.body
    assert exporter._keyframes == expected.keyframes
    assert exporter._timeline == expected.timeline


def test_parent_registration_occurs_at_first_visible_source_and_survives_exporter_reuse():
    canvas = scene(motion(track(RotationTrack, 0, 30)))
    canvas.shape("ellipse", (5, 5), 8, 8, "#00FF00", parent="root")
    exporter = HtmlExporter(canvas)
    exporter._keyframes.append("/* existing keyframe position */")
    first = exporter.render_stage()
    second = exporter.render_stage()
    assert first.keyframes[0] == second.keyframes[0] == "/* existing keyframe position */"
    assert all(item.startswith("@property") for item in first.keyframes[1:8])
    assert sum(item.startswith("@property") for item in second.keyframes) == 7
    assert second.keyframes[: len(first.keyframes)] == first.keyframes
    assert len(second.keyframes) == len(first.keyframes) + 2
    assert second.body.startswith(first.body + "\n")
    assert re.findall(r'id="([^"]+)"', second.body) == ["qt-l1", "qt-l2", "qt-l3", "qt-l4"]
    assert [item["k"] for item in second.timeline] == ["qt-k1", "qt-k2", "qt-k3", "qt-k4"]
    assert second.timeline[:2] == first.timeline
    assert [item["tr"] for item in second.timeline[2:]] == ["with_previous", "with_previous"]


def test_two_parent_slides_keep_stage_ids_keyframes_registration_and_morph_exclusion():
    from quickthumb import Deck, Morph

    from tests.test_export_html import timelines

    first = scene(motion(track(RotationTrack, 0, 30)))
    second = scene(motion(track(RotationTrack, 30, 60)))
    for canvas in (first, second):
        canvas.layers[2].motion_key = "matching-child"
        canvas.shape("ellipse", (5, 5), 8, 8, "#00FF00", parent="root")
    deck = Deck(220, 160).slide(first).slide(second, transition=Morph())
    html = deck.to_html()
    nodes = timelines(html)
    assert len(nodes) == 2
    names = re.findall(r"@keyframes ([^\{]+)\{", html)
    for index, stage_nodes in enumerate(nodes):
        assert [node["t"] for node in stage_nodes] == [["qt-l1"], ["qt-l2"]]
        assert [node["k"] for node in stage_nodes] == [f"qt-s{index}-k1", f"qt-s{index}-k2"]
        assert all(names.count(node["k"]) == 1 for node in stage_nodes)
        assert [node["tr"] for node in stage_nodes] == ["after_previous", "with_previous"]
    for prop in ("a", "b", "c", "d", "e", "f", "opacity"):
        assert html.count(f"@property --qt-parent-{prop}{{") == 2
    assert 'data-qt-morph="1"' not in html
    assert 'data-qt-motion-key="matching-child"' not in html
    assert "@keyframes qt-t1{from{opacity:0}to{opacity:1}}" in html
    assert all(
        item.fallback == "fade"
        for item in deck.validate_export("html")
        if item.feature == "parent_morph"
    )


class _Cancelled(BaseException):
    pass


class _Reader:
    def __init__(self, error=None):
        self.error = error
        self.calls = 0

    def close(self):
        self.calls += 1
        if self.error is not None:
            raise self.error


@pytest.mark.parametrize("phase", ["preparation", "sampling", "emission", "static"])
@pytest.mark.parametrize("error_type", [RenderingError, _Cancelled])
@pytest.mark.parametrize("cleanup_error_type", [RuntimeError, _Cancelled])
def test_stage_preserves_primary_error_and_retries_failed_readers(
    monkeypatch, phase, error_type, cleanup_error_type
):
    from quickthumb import _export_video, _parent_export
    from quickthumb._parent_render import ParentRenderPlan

    canvas = scene(motion(track(RotationTrack, 0, 30)))
    original = error_type("primary stage failure")
    readers = [_Reader(cleanup_error_type("first cleanup")), _Reader(), _Reader(RuntimeError())]

    def fail(*args, **kwargs):
        canvas._ctx.video_decoder_cache.update(
            zip(("first", "second", "third"), readers, strict=True)
        )
        canvas._ctx.motion_time = 0.5
        raise original

    if phase == "preparation":
        monkeypatch.setattr(_export_video, "_SlideAnimator", fail)
    elif phase == "sampling":
        monkeypatch.setattr(ParentRenderPlan, "sample", fail)
    elif phase == "emission":
        monkeypatch.setattr(HtmlExporter, "_emit_parent_source", fail)
    else:
        # Exercise errors reaching this boundary; nested raster cleanup has its own lifecycle.
        monkeypatch.setattr(_parent_export, "static_parent_fragment", fail)
    with pytest.raises(error_type) as raised:
        HtmlExporter(canvas, parent_static=phase == "static").render_stage()
    assert raised.value is original
    assert canvas._ctx.motion_time is None
    assert [reader.calls for reader in readers] == [1, 1, 1]
    assert canvas._ctx.video_decoder_cache == {"first": readers[0], "third": readers[2]}
    readers[0].error = readers[2].error = None
    canvas._ctx.close_video_decoders()
    assert [reader.calls for reader in readers] == [2, 1, 2]
    assert not canvas._ctx.video_decoder_cache


@pytest.mark.parametrize("cleanup_error_type", [RuntimeError, _Cancelled])
def test_successful_stage_surfaces_cleanup_failure_and_retries_failed_readers(
    monkeypatch, cleanup_error_type
):
    canvas = scene(motion(track(RotationTrack, 0, 30)))
    original = cleanup_error_type("cleanup after successful emission")
    readers = [_Reader(original), _Reader(), _Reader(RuntimeError())]
    emit = HtmlExporter._emit_parent_source

    def emit_with_readers(exporter, *args):
        emit(exporter, *args)
        canvas._ctx.video_decoder_cache.update(
            zip(("first", "second", "third"), readers, strict=True)
        )
        canvas._ctx.motion_time = 0.5

    monkeypatch.setattr(HtmlExporter, "_emit_parent_source", emit_with_readers)
    with pytest.raises(cleanup_error_type) as raised:
        HtmlExporter(canvas).render_stage()
    assert raised.value is original
    assert canvas._ctx.motion_time is None
    assert [reader.calls for reader in readers] == [1, 1, 1]
    assert canvas._ctx.video_decoder_cache == {"first": readers[0], "third": readers[2]}
    readers[0].error = readers[2].error = None
    canvas._ctx.close_video_decoders()
    assert [reader.calls for reader in readers] == [2, 1, 2]
    assert not canvas._ctx.video_decoder_cache
