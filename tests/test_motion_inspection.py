import json
import math
from io import BytesIO
from zipfile import ZipFile

import pytest
from quickthumb import (
    AnimationSpec,
    BlurTrack,
    Canvas,
    Deck,
    ExportPolicy,
    Fade,
    KeyframeSpec,
    PositionTrack,
    canvas_json_schema,
)
from quickthumb.errors import RenderingError, ValidationError


class TestMotionInspection:
    def test_should_publish_resolved_tracks_and_sampled_states_as_json(self):
        # Given: a canonical timeline attached to a stable layer
        canvas = Canvas(100, 100).text(
            "Motion",
            position=(0, 0),
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=1, value=(10, 20)),
                    ]
                )
            ),
        )

        # When: the public inspection API is called
        report = canvas.inspect_motion(target="video", fps=24)

        # Then: the result is deterministic and JSON serializable
        payload = report.model_dump(mode="json")
        layer = payload["slides"][0]["layers"][0]
        assert json.loads(json.dumps(payload))["fps"] == 24.0
        assert layer["layer_id"] == "layer:0"
        assert layer["duration"] == 1.0
        assert layer["events"][0]["tracks"][0]["type"] == "position"
        assert layer["final_state"]["position"] == [10.0, 20.0]

    def test_should_resolve_text_targets_in_stable_order(self):
        # Given: a word-staggered text preset
        canvas = Canvas(200, 100).text(
            "one two three",
            position=(0, 0),
            animation=AnimationSpec.rise(stagger=0.1, target="words"),
        )

        # When: motion is inspected
        report = canvas.inspect_motion(target="html")

        # Then: all semantic targets are exposed in document order
        targets = report.slides[0].layers[0].targets
        assert [target.index for target in targets] == [0, 1, 2]
        assert [target.source_range for target in targets] == [(0, 3), (4, 7), (8, 13)]

    def test_should_sample_canonical_motion_from_the_static_base_state_once(self):
        # Given: a rise preset whose initial position is offset from its static position
        canvas = Canvas(100, 100).text(
            "Motion",
            position=(0, 0),
            animation=AnimationSpec.rise(from_="bottom", distance=48, duration=1),
        )

        # When: the motion report samples the timeline
        layer = canvas.inspect_motion(target="video").slides[0].layers[0]

        # Then: the offset is applied once and settles at the authored position
        assert layer.initial_state["position"] == [0.0, 48.0]
        assert layer.final_state["position"] == [0.0, 0.0]

    def test_should_inspect_supported_legacy_effects(self):
        # Given: a legacy layer animation still accepted by the public layer API
        canvas = Canvas(100, 100).text(
            "Motion", position=(0, 0), animation=Fade(duration=1, trigger="after_previous")
        )

        # When: motion is inspected
        layer = canvas.inspect_motion(target="video").slides[0].layers[0]

        # Then: legacy timing is represented instead of disappearing
        assert layer.events[0].source == "legacy"
        assert layer.events[0].effect == "fade"
        assert layer.duration == 1.0

    def test_should_report_legacy_effect_progress_at_inspection_samples(self):
        # Given: a legacy fade with a one-second active interval
        canvas = Canvas(100, 100).text("Motion", position=(0, 0), animation=Fade(duration=1))

        # When: motion is inspected at two frames per second
        event = canvas.inspect_motion(target="video", fps=2).slides[0].layers[0].events[0]

        # Then: the public event report exposes deterministic normalized progress
        assert event.progress == [0.0, 0.5, 1.0]

    def test_should_report_capabilities_and_policy_fallbacks_for_each_exporter(self):
        # Given: blur motion that has different exporter support
        canvas = Canvas(100, 100).text(
            "Motion",
            position=(0, 0),
            animation=AnimationSpec.timeline(
                BlurTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=4)])
            ),
        )

        # When: all default exporter families are inspected
        report = canvas.inspect_motion()

        # Then: the registry and resolved fallback remain visible together
        capabilities = {(item.target, item.feature): item for item in report.capabilities}
        assert capabilities[("html", "blur")].support == "partial"
        assert capabilities[("pptx", "blur")].fallback == "rasterize"
        assert {item.target for item in report.diagnostics} == {"raster", "html", "pptx", "video"}

    def test_should_resolve_reduced_motion_to_a_static_accessible_result(self):
        # Given: motion and an explicit reduced-motion policy
        canvas = Canvas(100, 100).text(
            "Motion",
            position=(0, 0),
            animation=AnimationSpec.rise(duration=2),
        )

        # When: reduced motion is requested
        report = canvas.inspect_motion(policy=ExportPolicy(reduced_motion=True))

        # Then: the report states the static resolution deterministically
        assert report.reduced_motion.enabled is True
        assert report.reduced_motion.mode == "static"
        assert report.reduced_motion.original_duration == 2.0
        assert report.reduced_motion.resolved_duration == 0.0
        assert "position" in report.reduced_motion.removed_features
        assert report.duration == 0.0
        assert report.slides[0].duration == 0.0
        assert report.slides[0].layers[0].events == []
        assert report.slides[0].layers[0].sample_times == [0.0]

    def test_should_report_the_exported_static_state_for_reduced_motion(self):
        # Given: motion whose final keyframe differs from the authored layer state
        canvas = Canvas(100, 100).text(
            "Motion",
            position=(0, 0),
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=1, value=(50, 0)),
                    ]
                )
            ),
        )

        # When: reduced-motion inspection resolves the export
        layer = canvas.inspect_motion(policy=ExportPolicy(reduced_motion=True)).slides[0].layers[0]

        # Then: the static sample matches the state used by static exporters
        assert layer.samples == [layer.static_state]
        assert layer.samples[0]["position"] == [0.0, 0.0]

    def test_should_apply_reduced_motion_to_html_without_mutating_the_source(self):
        # Given: a canvas with canonical motion
        canvas = Canvas(100, 100).text(
            "Motion", position=(0, 0), animation=AnimationSpec.fade(duration=1)
        )
        policy = ExportPolicy(reduced_motion=True)

        # When: normal and reduced-motion HTML are exported
        animated = canvas.to_html()
        static = canvas.to_html(policy=policy)

        # Then: only the reduced export omits motion CSS and source motion remains intact
        assert "@keyframes qt-k" in animated
        assert "@keyframes qt-k" not in static
        assert canvas.inspect_motion(target="html").slides[0].layers[0].events

    def test_should_allow_reduced_motion_html_for_backdrop_compositing(self):
        # Given: an animated layer that normally requires backdrop rasterization
        canvas = (
            Canvas(160, 90)
            .background(color="#1131AA")
            .shape("rectangle", (40, 20), 80, 50, "#FF2D55", animation=Fade(duration=0.5))
            .custom(lambda image: None)
        )

        # When: HTML is exported with reduced motion
        html = canvas.to_html(policy=ExportPolicy(reduced_motion=True))

        # Then: the static policy does not reject the otherwise unsupported animation path
        assert "@keyframes qt-k" not in html

    def test_should_apply_reduced_motion_to_pptx_without_timing_records(self):
        # Given: a canvas with a legacy PowerPoint animation
        pytest.importorskip("pptx")
        canvas = Canvas(100, 100).text("Motion", position=(0, 0), animation=Fade(duration=1))

        # When: the canvas is exported with reduced motion enabled
        normal = canvas.to_pptx()
        static = canvas.to_pptx(policy=ExportPolicy(reduced_motion=True))

        # Then: the static document has no animation timing tree
        def has_timing(data):
            with ZipFile(BytesIO(data)) as archive:
                return any(
                    "<p:timing" in archive.read(name).decode("utf-8")
                    for name in archive.namelist()
                    if name.endswith(".xml")
                )

        assert has_timing(normal) is True
        assert has_timing(static) is False

    def test_should_bound_samples_and_preserve_endpoints(self):
        # Given: a timeline much longer than the requested inspection sample cap
        canvas = Canvas(100, 100).text(
            "Motion",
            position=(0, 0),
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=100, value=(10, 20)),
                    ]
                )
            ),
        )

        # When: inspection is capped to three samples
        layer = canvas.inspect_motion(target="video", fps=60, max_samples=3).slides[0].layers[0]

        # Then: the cap is honored without losing the endpoints
        assert canvas.inspect_motion(target="video", fps=60, max_samples=3).max_samples == 3
        assert layer.sample_times == [0.0, 50.0, 100.0]
        assert layer.samples[0]["position"] == [0.0, 0.0]
        assert layer.samples[-1]["position"] == [10.0, 20.0]

    def test_should_match_exporter_deck_duration_with_transition_and_hold(self):
        # Given: two animated slides with one-second transitions
        first = Canvas(100, 100).text(
            "A", position=(0, 0), animation=AnimationSpec.fade(duration=1)
        )
        second = Canvas(100, 100).text(
            "B", position=(0, 0), animation=AnimationSpec.fade(duration=1)
        )
        deck = Deck(100, 100).slide(first, transition={"effect": "fade", "duration": 1})
        deck.slide(second, transition={"effect": "fade", "duration": 1})

        # When: the deck motion report resolves the export schedule
        report = deck.inspect_motion(target="video")

        # Then: each slide includes its transition, animation, and default hold
        assert [slide.duration for slide in report.slides] == [4.0, 4.0]
        assert report.duration == 8.0

    def test_should_report_deck_morph_matches_and_slide_indices(self):
        # Given: two slides with one uniquely keyed shared layer
        first = Canvas(100, 100).text("A", position=(0, 0), motion_key="title")
        second = Canvas(100, 100).text("B", position=(10, 10), motion_key="title")
        deck = Deck(100, 100, transition="morph").slide(first).slide(second)

        # When: the deck motion is inspected
        report = deck.inspect_motion(target="pptx")

        # Then: slide identity and match behavior are public
        assert [slide.slide_index for slide in report.slides] == [0, 1]
        assert report.slides[1].matches[0].motion_key == "title"
        assert report.slides[1].matches[0].behavior == "match"

    def test_should_report_implicit_deck_crossfades_and_zero_duration_cuts(self):
        # Given: a deck with an implicit transition and an explicit cut
        first = Canvas(100, 100).text("A", position=(0, 0))
        second = Canvas(100, 100).text("B", position=(0, 0))
        implicit_deck = Deck(100, 100).slide(first).slide(second)
        cut_deck = Deck(100, 100).slide(first).slide(second, transition="cut")

        # When: deck motion is inspected
        report = implicit_deck.inspect_motion(target="video")
        cut_report = cut_deck.inspect_motion(target="video")

        # Then: implicit and cut transition timing are represented accurately
        assert report.slides[1].transition.effect == "fade"
        assert cut_report.slides[1].transition.effect == "cut"
        assert cut_report.slides[1].transition.duration == 0.0

    def test_should_reject_empty_decks_invalid_fps_and_empty_targets(self):
        # Given: malformed inspection requests
        empty = Deck(100, 100)
        canvas = Canvas(100, 100)

        # When/Then: public validation fails before producing an ambiguous report
        with pytest.raises(RenderingError, match="empty deck"):
            empty.inspect_motion()
        with pytest.raises(ValidationError, match="fps"):
            canvas.inspect_motion(fps=0)
        with pytest.raises(ValidationError, match="must not be empty"):
            canvas.inspect_motion(target=[])
        with pytest.raises(ValidationError, match="target must be one of"):
            canvas.inspect_motion(target="flash")
        with pytest.raises(ValidationError, match="fps"):
            canvas.inspect_motion(fps=math.nan)
        with pytest.raises(ValidationError, match="fps"):
            canvas.inspect_motion(fps=True)

    def test_should_publish_inspection_models_in_the_canvas_schema(self):
        # Given: the published JSON schema
        schema = canvas_json_schema()

        # When: clients discover the public inspection contract
        definitions = schema["$defs"]

        # Then: the complete result graph is present
        assert "MotionInspection" in definitions
        assert "MotionLayerInspection" in definitions
        assert "MotionCapabilityInspection" in definitions
