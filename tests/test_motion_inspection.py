import json

import pytest
from quickthumb import (
    AnimationSpec,
    BlurTrack,
    Canvas,
    Deck,
    ExportPolicy,
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

    def test_should_publish_inspection_models_in_the_canvas_schema(self):
        # Given: the published JSON schema
        schema = canvas_json_schema()

        # When: clients discover the public inspection contract
        definitions = schema["$defs"]

        # Then: the complete result graph is present
        assert "MotionInspection" in definitions
        assert "MotionLayerInspection" in definitions
        assert "MotionCapabilityInspection" in definitions
