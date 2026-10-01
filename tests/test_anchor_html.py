"""Opt-in HTML geometry tracks preserve anchors, independent clocks, and replay."""

import base64
import json
import re
import subprocess
from html import unescape
from importlib.resources import files
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from quickthumb import (
    AnimationSpec,
    Canvas,
    KeyframeSpec,
    OpacityTrack,
    PositionKeyframeSpec,
    PositionTrack,
    RotationTrack,
    ScaleTrack,
    ScaleXTrack,
    ScaleYTrack,
    TimingSpec,
)
from quickthumb._export_base import rasterize_layers
from quickthumb._export_html import (
    HtmlExporter,
    _supports_transform_extensions_html,
    css_easing,
)
from quickthumb.errors import RenderingError
from quickthumb.models import (
    AnimatedTextValue,
    BackdropBlur,
    BlurTrack,
    ImageLayer,
    Shadow,
    StaggerSpec,
    TextLayer,
    VideoLayer,
)
from quickthumb.motion import LayerState, compile_timeline


def _track(kind, *keys):
    return kind(keyframes=[KeyframeSpec(time=time, value=value) for time, value in keys])


def _canvas(animation, **kwargs):
    return Canvas(180, 160).shape(
        "rectangle", (35, 40), 40, 30, "#ff8844", animation=animation, **kwargs
    )


def _match(pattern, text):
    match = re.search(pattern, text)
    assert match is not None
    return match


def _nodes(html):
    return json.loads(unescape(_match(r"data-qt-timeline='([^']*)'", html)[1]))


def _stops(html, name):
    body = _match(r"@keyframes " + re.escape(name) + r"\{((?:[^{}]+\{[^{}]*\})+)\}", html)[1]
    return {
        float(percent): {
            key: float(value)
            for declaration in declarations.split(";")
            if declaration
            for key, value in [declaration.split(":")]
        }
        for percent, declarations in re.findall(r"([\d.e+-]+)%\{([^{}]*)\}", body)
    }


def _css_sample(stops, prop, percent):
    keys = [(time, values[prop]) for time, values in stops.items() if prop in values]
    if percent <= keys[0][0]:
        return keys[0][1]
    for (left_time, left), (right_time, right) in zip(keys, keys[1:], strict=False):
        if percent <= right_time:
            return left + (right - left) * (percent - left_time) / (right_time - left_time)
    return keys[-1][1]


def test_tracks_keep_independent_times_and_multiply_scale_continuously():
    animation = AnimationSpec.timeline(
        _track(PositionTrack, (0.25, (3, 6)), (1.5, (18, -9))),
        _track(ScaleTrack, (0, 1), (2, 3)),
        _track(ScaleXTrack, (0, 1), (0.5, 2), (1.75, -1)),
        _track(ScaleYTrack, (0, 0.5), (1, 1.5), (2, 0)),
        _track(RotationTrack, (0, 5), (0.75, 25), (2, 90)),
        _track(OpacityTrack, (0.5, 0.2), (1.25, 0.8)),
        timing=TimingSpec(duration=2, delay=0.5, trigger="on_click"),
    )
    canvas = _canvas(animation, anchor=(0.25, 0.75))
    html = canvas.to_html()
    node = _nodes(html)[0]
    assert node["a"] == "transform"
    assert node["tr"] == "on_click"
    assert node["delay"] == 0.5
    assert node["e"] == "linear"
    assert html.count("@property ") == 7
    assert "transform-origin:25% 75%;" in html
    assert "transform:translate(" in html
    assert "rotate(calc(var(--qt-motion-rotation)*1deg)) scale(" in html
    assert "var(--qt-motion-scale)*var(--qt-motion-scale-x)" in html
    assert "var(--qt-motion-scale)*var(--qt-motion-scale-y)" in html
    stops = _stops(html, node["k"])
    assert stops[25] == {"--qt-motion-scale-x": 2, "--qt-motion-opacity": 0.2}
    assert "--qt-motion-scale" not in stops[25]
    timeline = compile_timeline(animation)
    # Every authored knot plus interior points, first-key holds, and tail holds.
    for local in [0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 1, 1.25, 1.5, 1.75, 2]:
        state = timeline.sample(local + node["delay"])
        for prop in ["scale", "scale_x", "scale_y", "rotation", "opacity"]:
            name = "--qt-motion-" + prop.replace("_", "-")
            assert _css_sample(stops, name, local / 2 * 100) == pytest.approx(getattr(state, prop))
        assert state.position is not None
        for axis, value in zip("xy", state.position, strict=True):
            assert _css_sample(stops, f"--qt-motion-{axis}", local / 2 * 100) == pytest.approx(
                value
            )
        sx = _css_sample(stops, "--qt-motion-scale", local / 2 * 100)
        sx *= _css_sample(stops, "--qt-motion-scale-x", local / 2 * 100)
        assert sx == pytest.approx(state.scale * state.scale_x)
    assert node["initial"]["--qt-motion-opacity"] == "1"
    assert node["final"]["--qt-motion-opacity"] == "0.8"
    assert timeline.sample(0.49) == LayerState()


def test_transform_uses_rendered_ink_bounds_and_baked_static_styles():
    animation = AnimationSpec.timeline(_track(ScaleXTrack, (0, 1), (1, 2)))
    canvas = _canvas(
        animation,
        anchor=(0, 1),
        rotation=30,
        opacity=0.4,
        effects=[Shadow(color="#000000", offset_x=5, offset_y=3, blur_radius=2)],
    )
    fragment = rasterize_layers(canvas, [canvas.layers[0]])
    assert fragment is not None
    html = canvas.to_html()
    image_tag = _match(r'<img id="qt-l1"[^>]+>', html)[0]
    assert f"left:{fragment.x}px;top:{fragment.y}px" in image_tag
    assert f"width:{fragment.width}px;height:{fragment.height}px" in image_tag
    assert "transform-origin:0% 100%" in image_tag
    assert "rotate(30" not in image_tag
    encoded = _match(r"base64,([^\"]+)", image_tag)[1]
    assert base64.b64decode(encoded) == fragment.png_bytes
    pixels = Image.open(BytesIO(fragment.png_bytes))
    assert max(pixels.getchannel("A").tobytes()) < 255


def test_duplicate_replace_tracks_discard_all_earlier_property_stops():
    animation = AnimationSpec.timeline(
        _track(ScaleXTrack, (0, 7), (0.5, 9), (1, 10)),
        _track(ScaleXTrack, (0.25, -2), (1, 0)),
    )
    html = _canvas(animation).to_html()
    node = _nodes(html)[0]
    stops = _stops(html, node["k"])
    assert stops == {
        0: {"--qt-motion-scale-x": -2},
        25: {"--qt-motion-scale-x": -2},
        100: {"--qt-motion-scale-x": 0},
    }
    assert node["final"]["--qt-motion-scale-x"] == "0"


def test_zero_duration_and_high_precision_keyframes():
    html = _canvas(AnimationSpec.timeline(_track(ScaleYTrack, (0, -0.123456789012345)))).to_html()
    node = _nodes(html)[0]
    assert node["d"] == 0
    assert _stops(html, node["k"]) == {
        0: {"--qt-motion-scale-y": -0.123456789012345},
        100: {"--qt-motion-scale-y": -0.123456789012345},
    }


@pytest.mark.parametrize("easing", [None, "linear", "ease_in_quad", "ease_out_back"])
def test_uses_existing_easing_vocabulary(easing):
    animation = AnimationSpec.timeline(_track(ScaleXTrack, (0, 1), (1, 2)), easing=easing)
    node = _nodes(_canvas(animation).to_html())[0]
    assert node["e"] == css_easing(easing or "linear")


def test_absolute_start_joins_legacy_group_and_rebases_delay():
    canvas = _canvas(AnimationSpec.fade(duration=1, trigger="after_previous"))
    canvas.shape(
        "rectangle",
        (80, 80),
        20,
        20,
        "#ffffff",
        animation=AnimationSpec.timeline(
            _track(ScaleXTrack, (0, 1), (2, 2)), timing=TimingSpec(start=1.5, duration=2)
        ),
    )
    nodes = _nodes(canvas.to_html())
    assert nodes[1]["tr"] == "with_previous"
    assert nodes[1]["delay"] == 1.5
    assert "abs" not in nodes[1]


@pytest.mark.parametrize(
    "animation",
    [
        AnimationSpec.zoom(),
        AnimationSpec.timeline(_track(BlurTrack, (0, 0), (1, 2))),
        [AnimationSpec.timeline(_track(ScaleXTrack, (0, 1), (1, 2))), AnimationSpec.fade()],
        AnimationSpec(
            tracks=[_track(ScaleXTrack, (0, 1), (1, 2))],
            stagger=StaggerSpec(delay=0.1, target="children"),
        ),
        AnimationSpec.timeline(_track(ScaleTrack, (0, 0), (1, 2))),
        AnimationSpec.timeline(_track(ScaleTrack, (0, -1), (1, 2))),
        AnimationSpec.timeline(_track(ScaleTrack, (0, 1), (1, 2)), easing="ease_in_back"),
    ],
)
def test_unsupported_extension_combinations_use_authored_static_fallback(animation):
    canvas = _canvas(animation, anchor=(0, 0))
    assert not _supports_transform_extensions_html(canvas.layers[0])
    html = canvas.to_html()
    assert _nodes(html) == []
    assert "@property " not in html
    assert "@keyframes qt-k" not in html
    assert "visibility:hidden" not in _match(r'<img id="qt-l1"[^>]+>', html)[0]
    fragment = rasterize_layers(canvas, [canvas.layers[0]])
    assert fragment is not None
    encoded = _match(r"data:image/png;base64,([^\"]+)", html)[1]
    assert base64.b64decode(encoded) == fragment.png_bytes


def test_image_axis_scale_maps_but_uniform_viewport_zoom_falls_back():
    source = str(Path(__file__).parent / "fixtures" / "sample_image.jpg")
    animation = AnimationSpec.timeline(_track(ScaleXTrack, (0, 1), (1, 2)))
    canvas = Canvas(120, 100).image(source, (10, 10), width=50, height=40, animation=animation)
    assert _supports_transform_extensions_html(canvas.layers[0])
    assert _nodes(canvas.to_html())[0]["a"] == "transform"
    layer = ImageLayer(
        type="image",
        path=source,
        position=(0, 0),
        anchor=(0, 0),
        animation=AnimationSpec.timeline(_track(ScaleTrack, (0, 1), (1, 2))),
    )
    assert not _supports_transform_extensions_html(layer)


def test_dynamic_sources_and_animated_group_children_are_not_claimed_supported():
    animation = AnimationSpec.timeline(_track(ScaleXTrack, (0, 1), (1, 2)))
    counter = TextLayer(
        type="text",
        content="0",
        animation=animation,
        value=AnimatedTextValue.model_validate({"from": 0, "to": 100, "duration": 1}),
    )
    video = VideoLayer(
        type="video", source="clip.mp4", width=20, height=20, position=(0, 0), animation=animation
    )
    assert not _supports_transform_extensions_html(counter)
    assert not _supports_transform_extensions_html(video)
    child = {"type": "shape", "shape": "rectangle", "width": 20, "height": 15, "color": "#ffffff"}
    canvas = Canvas(100, 100).group(
        [child, {**child, "animation": AnimationSpec.fade()}], animation=animation
    )
    assert not _supports_transform_extensions_html(canvas.layers[0])
    assert _nodes(canvas.to_html()) == []


def test_static_group_is_one_fragment_with_whole_group_anchor():
    child = {"type": "shape", "shape": "rectangle", "width": 20, "height": 15, "color": "#ffffff"}
    canvas = Canvas(100, 100).group(
        [child, child],
        gap=5,
        padding=7,
        position=(20, 20),
        anchor=(1, 0),
        animation=AnimationSpec.timeline(_track(ScaleYTrack, (0, 1), (1, 2))),
    )
    html = canvas.to_html()
    assert _supports_transform_extensions_html(canvas.layers[0])
    assert len(_nodes(html)) == 1
    assert html.count("<img id=") == 1
    assert "transform-origin:100% 0%;" in html


def test_backdrop_dependent_layers_and_descendants_are_not_claimed_supported():
    animation = AnimationSpec.timeline(_track(ScaleXTrack, (0, 1), (1, 2)))
    canvas = _canvas(animation, effects=[BackdropBlur(radius=3)])
    assert not _supports_transform_extensions_html(canvas.layers[0])
    with pytest.raises(RenderingError, match="cannot animate layers.*rasterized together"):
        canvas.to_html()
    child = {
        "type": "shape",
        "shape": "rectangle",
        "width": 20,
        "height": 15,
        "color": "#ffffff",
        "effects": [BackdropBlur(radius=3)],
    }
    canvas = Canvas(100, 100).group([child], animation=animation)
    assert not _supports_transform_extensions_html(canvas.layers[0])
    assert _nodes(canvas.to_html()) == []


def test_later_blend_layer_preserves_established_animated_prefix_error():
    canvas = _canvas(AnimationSpec.timeline(_track(ScaleXTrack, (0, 1), (1, 2))))
    source = str(Path(__file__).parent / "fixtures" / "sample_image.jpg")
    canvas.image(source, (10, 10), width=50, height=40, blend_mode="multiply")
    with pytest.raises(RenderingError, match="cannot animate layers.*rasterized together"):
        canvas.to_html()


def test_one_item_spec_list_maps_and_centered_legacy_documents_keep_old_adapter():
    tracks = AnimationSpec.timeline(_track(ScaleTrack, (0, 1), (1, 2)))
    original = _canvas(tracks).to_html()
    explicit = _canvas(tracks, anchor=(0.5, 0.5)).to_html()
    assert original == explicit
    assert "@property " not in original
    assert _nodes(original)[0]["a"] == "entrance"
    html = _canvas([tracks], anchor=(0, 0)).to_html()
    assert _nodes(html)[0]["a"] == "transform"


def test_reduced_motion_keeps_authored_static_appearance_without_track_css():
    canvas = _canvas(AnimationSpec.timeline(_track(ScaleXTrack, (0, 1), (1, 2))))
    html = HtmlExporter(canvas, reduced_motion=True).export()
    assert _nodes(html) == []
    assert "@property " not in html
    assert "@keyframes qt-k" not in html


@pytest.mark.parametrize("motion_path", [False, True])
def test_runtime_settles_seeks_resets_replays_and_ignores_stale_callbacks(motion_path):
    animation = AnimationSpec.timeline(
        _track(ScaleTrack, (0, 1), (2, 3)),
        _track(ScaleXTrack, (0, 1), (2, -2)),
        _track(PositionTrack, (0, (0, 0)), (2, (13, 21))),
        _track(RotationTrack, (0, 0), (2, 45)),
        _track(OpacityTrack, (0, 0.2), (2, 0.7)),
        timing=TimingSpec(duration=2, delay=0.25, trigger="on_click"),
    )
    if motion_path:
        assert animation.tracks is not None
        animation.tracks[2] = PositionTrack(
            auto_orient=True,
            keyframes=[
                PositionKeyframeSpec(time=0, value=(0, 0), out_tangent=(0, 30)),
                PositionKeyframeSpec(time=2, value=(13, 21), in_tangent=(30, 0)),
            ],
        )
    node = _nodes(_canvas(animation, anchor=(0, 1)).to_html())[0]
    script = r"""
const assert=require('node:assert/strict');
const input=JSON.parse(require('fs').readFileSync(0,'utf8'));
const timers=[];
const CSS={escape:x=>x};
function setTimeout(fn,delay){timers.push({fn,delay});}
eval(input.runtime);
const values={...input.node.initial};
const listeners=new Set();
const style={opacity:'var(--qt-motion-opacity)',setProperty:(k,v)=>{values[k]=String(v);}};
let layoutReads=0;
const el={style,addEventListener:(type,fn)=>listeners.add(fn),
  removeEventListener:(type,fn)=>listeners.delete(fn),
  get offsetWidth(){layoutReads++;return 40;}};
const stage={getAttribute:()=>JSON.stringify([input.node]),querySelector:()=>el};
const tl=new qtTimeline(stage);
function motionValues(){
  return Object.fromEntries(Object.keys(input.node.initial).map(k=>[k,values[k]]));
}
function initial(){assert.deepEqual(motionValues(),input.node.initial);
  assert.equal(style.visibility,'visible');}
function final(){assert.deepEqual(motionValues(),input.node.final);
  assert.equal(style.visibility,'visible');
  assert.equal(style.animation,'');assert.equal(style.willChange,'');}
async function drain(){for(const t of timers.splice(0))t.fn();await Promise.resolve();}
(async()=>{
  tl.reset();initial();assert.equal(tl.position(),0);
  let playing=tl.advance();
  initial();assert.match(style.animation,/2s linear forwards 0.25s$/);
  assert.equal(timers[0].delay,2250);
  for(const fn of [...listeners])fn();
  final();assert.equal(listeners.size,0);
  await drain();await playing;assert.equal(tl.position(),1);
  tl.reset();initial();assert.equal(tl.hasNext(),true);
  tl.finish();final();assert.equal(tl.hasNext(),false);
  tl.setPosition(0);initial();
  tl.setPosition(1);final();
  tl.setPosition(-100);initial();
  tl.setPosition(100);final();
  tl.reset();playing=tl.advance();
  const stale=[...listeners][0];
  tl.reset();initial();assert.equal(listeners.size,0);
  stale();initial();await drain();await playing;
  initial();assert.equal(tl.position(),0);
  playing=tl.advance();tl.finish();final();
  await drain();await playing;final();assert.equal(tl.position(),1);
  tl.reset();playing=tl.advance();
  // A missing animationend still settles at the authored delay + duration.
  await drain();await playing;final();assert.equal(tl.position(),1);
  assert.ok(layoutReads>=4);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run(
        ["node", "-e", script],
        input=json.dumps(
            {"node": node, "runtime": files("quickthumb.html").joinpath("timeline.js").read_text()}
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
