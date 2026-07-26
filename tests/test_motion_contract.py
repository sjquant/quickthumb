import json
import math

import pytest
from jsonschema import ValidationError as JsonSchemaValidationError  # ty: ignore[unresolved-import]
from jsonschema import validate  # ty: ignore[unresolved-import]
from quickthumb import (
    AnimationSpec,
    BlurTrack,
    Canvas,
    ClipProgressTrack,
    ColorTrack,
    ExportPolicy,
    KeyframeSpec,
    MotionProfile,
    OpacityTrack,
    PositionTrack,
    ScaleTrack,
    ValidationError,
    canvas_json_schema,
)


class TestMotionContract:
    """Black-box coverage for the public motion contract."""

    def test_should_build_and_serialize_a_preset_animation(self):
        """A semantic preset serializes with the canonical animation discriminator."""
        # given: a preset with semantic options and relative timing
        animation = AnimationSpec.rise(from_="bottom", distance=48, duration=0.45, stagger=0.04)

        # when: the model is serialized as canonical JSON
        payload = animation.model_dump(mode="json", by_alias=True)

        # then: the effect branch and its options are explicit
        assert payload["type"] == "animation"
        assert payload["effect"] == {
            "type": "rise",
            "from": "bottom",
            "distance": 48.0,
            "feel": None,
            "easing": None,
        }
        assert payload["stagger"]["delay"] == 0.04

    def test_should_build_and_round_trip_a_timeline_animation_on_a_canvas(self):
        """Typed tracks survive Canvas JSON serialization and parsing."""
        # given: a canvas with position and opacity tracks
        animation = AnimationSpec.timeline(
            PositionTrack(
                keyframes=[
                    KeyframeSpec(time=0, value=(10, 20)),
                    KeyframeSpec(time=0.5, value=(30, 40)),
                ]
            ),
            OpacityTrack(
                keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=0.5, value=1)]
            ),
        )
        canvas = Canvas(100, 100).text("Motion", position=(0, 0), animation=animation)

        # when: the canvas is serialized and loaded through the public API
        restored = Canvas.from_json(canvas.to_json())
        restored_payload = json.loads(restored.to_json())

        # then: the advanced form remains typed and canonical
        restored_animation = restored_payload["layers"][0]["animation"]
        assert restored_animation["type"] == "animation"
        assert [track["type"] for track in restored_animation["tracks"]] == ["position", "opacity"]
        assert restored_animation["tracks"][0]["keyframes"][1]["value"] == [30, 40]

    def test_should_reject_preset_and_timeline_composition(self):
        """An animation cannot silently choose precedence between effect and tracks."""
        # given: both mutually exclusive branches are supplied
        # when: the public model validates the payload
        with pytest.raises(ValidationError, match="exactly one of effect or tracks"):
            AnimationSpec.model_validate(
                {
                    "effect": {"type": "fade"},
                    "tracks": [{"type": "opacity", "keyframes": [{"time": 0, "value": 1}]}],
                }
            )

        # then: the validation error names the composition rule

    def test_should_reject_invalid_property_values_and_timing(self):
        """Invalid properties, keyframes, durations, and timing modes fail clearly."""
        # given: malformed timeline and conflicting timing payloads
        # when: each payload is validated
        with pytest.raises(ValidationError, match="valid discriminator|type"):
            AnimationSpec.model_validate(
                {
                    "type": "animation",
                    "tracks": [{"type": "bogus_position_tag", "keyframes": []}],
                }
            )
        with pytest.raises(ValidationError, match="strictly increasing"):
            PositionTrack(
                keyframes=[KeyframeSpec(time=0, value=(0, 0)), KeyframeSpec(time=0, value=(1, 1))]
            )
        with pytest.raises(ValidationError, match="greater than 0"):
            AnimationSpec.model_validate({"effect": {"type": "fade"}, "timing": {"duration": 0}})
        with pytest.raises(ValidationError, match="relative trigger/delay or absolute start"):
            AnimationSpec.model_validate(
                {
                    "effect": {"type": "fade"},
                    "timing": {"start": 1.0, "trigger": "after_previous"},
                }
            )

        # then: all invalid inputs are rejected before exporter execution

    @pytest.mark.parametrize(
        ("track_type", "value", "message"),
        [
            (OpacityTrack, 1.1, "opacity"),
            (ClipProgressTrack, -0.1, "clip_progress"),
            (BlurTrack, -1, "blur"),
            (ColorTrack, "red", "invalid hex color"),
            (ScaleTrack, math.inf, "numbers"),
        ],
    )
    def test_should_reject_invalid_values_for_every_supported_track(
        self, track_type, value, message
    ):
        """Every typed track enforces its property-specific value contract."""
        # given: one malformed value for a supported track
        keyframe = KeyframeSpec(time=0, value=value)

        # when: the track validates its keyframes
        with pytest.raises(ValidationError, match=message):
            track_type(keyframes=[keyframe])

        # then: malformed values cannot enter the timeline

    def test_should_reject_unknown_motion_fields_and_empty_timeline_branches(self):
        """Strict motion models reject misspellings and incomplete compositions."""
        # given: unknown fields and missing mutually exclusive branches
        # when: the public models validate them
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            AnimationSpec.model_validate({"effect": {"type": "fade"}, "duration": 0.5})
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            PositionTrack.model_validate(
                {
                    "type": "position",
                    "keyframes": [{"time": 0, "value": [0, 0]}],
                    "unknown_field_name": "position",
                }
            )
        with pytest.raises(ValidationError, match="exactly one of effect or tracks"):
            AnimationSpec()
        with pytest.raises(ValidationError, match="at least one track"):
            AnimationSpec(tracks=[])

        # then: invalid contract shapes fail before serialization

    def test_should_reject_non_finite_timing_and_keyframe_values(self):
        """Motion timing rejects infinity and NaN even when signs are valid."""
        # given: non-finite values in timing and keyframe positions
        # when: each value is validated
        with pytest.raises(ValidationError, match="finite number"):
            AnimationSpec.model_validate(
                {"effect": {"type": "fade"}, "timing": {"duration": math.inf}}
            )
        with pytest.raises(ValidationError, match="finite number"):
            AnimationSpec.model_validate(
                {"effect": {"type": "fade"}, "timing": {"start": math.nan}}
            )
        with pytest.raises(ValidationError, match="finite number"):
            KeyframeSpec(time=math.inf, value=1)

        # then: exporters never receive unbounded timeline values

    def test_should_publish_motion_discriminators_and_xor_schema(self):
        """The generated canvas schema exposes motion types and composition rules."""
        # given: the published canvas schema
        # when: motion definitions are inspected
        schema = canvas_json_schema()
        animation = schema["$defs"]["AnimationSpec"]
        track_items = animation["properties"]["tracks"]["anyOf"][0]["items"]

        # then: canonical discriminators and effect/timeline XOR are present
        assert animation["properties"]["type"]["const"] == "animation"
        assert animation["oneOf"][0]["required"] == ["effect"]
        assert animation["oneOf"][1]["required"] == ["tracks"]
        assert track_items["discriminator"]["propertyName"] == "type"
        assert set(track_items["discriminator"]["mapping"]) == {
            "position",
            "scale",
            "rotation",
            "opacity",
            "clip_progress",
            "blur",
            "color",
        }
        assert animation["additionalProperties"] is False
        assert animation["required"] == ["type"]
        assert schema["$defs"]["AnimationEffect"]["required"] == ["type"]
        assert schema["$defs"]["PositionTrack"]["additionalProperties"] is False
        assert schema["$defs"]["PositionTrack"]["required"] == ["type", "keyframes"]
        assert {"MotionProfile", "ExportPolicy", "ExportDiagnostic"} <= set(schema["$defs"])

    def test_should_validate_canonical_documents_against_published_schema(self):
        """Published schema accepts valid motion and rejects malformed discriminators."""
        # given: a valid Canvas document carrying a canonical preset animation
        canvas = Canvas(100, 100).text(
            "Motion", position=(0, 0), animation=AnimationSpec.rise(target="words")
        )
        schema = canvas_json_schema()
        document = json.loads(canvas.to_json())

        # when: the document is checked against the published JSON Schema
        validate(document, schema)
        missing_discriminator = json.loads(json.dumps(document))
        del missing_discriminator["layers"][0]["animation"]["type"]
        conflicting_branches = json.loads(json.dumps(document))
        conflicting_branches["layers"][0]["animation"]["tracks"] = []

        # then: malformed canonical documents are rejected by schema validation
        with pytest.raises(JsonSchemaValidationError):
            validate(missing_discriminator, schema)
        with pytest.raises(JsonSchemaValidationError):
            validate(conflicting_branches, schema)

    def test_should_validate_profile_and_export_policy_models(self):
        """Profile and exporter policy models expose constrained public options."""
        # given: a deck profile and a PPTX fallback policy
        profile = MotionProfile(name="presentation", feel="soft")
        policy = ExportPolicy(pptx={"line-chart": "rasterize"}, unsupported_motion="warn")

        # when: the models are serialized
        profile_payload = profile.model_dump(mode="json")
        policy_payload = policy.model_dump(mode="json")

        # then: the policy remains explicit and JSON-compatible
        assert profile_payload["speed"] == 1.0
        assert policy_payload["pptx"] == {"line-chart": "rasterize"}

        # given: invalid profile and exporter policy values
        # when: the constrained models validate them
        with pytest.raises(ValidationError, match="Input should be 'presentation'"):
            MotionProfile.model_validate({"name": "fast"})
        with pytest.raises(ValidationError, match="Input should be 'native'"):
            ExportPolicy.model_validate({"pptx": {"line-chart": "ignore"}})

        # then: unsupported configuration values are rejected clearly

    def test_should_export_new_motion_specs_through_html(self):
        """Canonical motion is compiled into the public HTML timeline."""
        # given: a layer using the canonical motion model
        canvas = Canvas(100, 100).text("Motion", position=(0, 0), animation=AnimationSpec.fade())

        # when: the HTML exporter is requested
        document = canvas.to_html()

        # then: the normalized animation timeline is present in the document
        assert "data-qt-timeline" in document
        assert "@keyframes" in document

    def test_should_preserve_legacy_animation_json(self):
        """Existing effect animation JSON remains unchanged after the contract addition."""
        # given: the established legacy layer animation payload
        raw = {
            "kind": "canvas",
            "width": 100,
            "height": 100,
            "layers": [
                {
                    "type": "text",
                    "content": "Legacy",
                    "position": [0, 0],
                    "animation": {"effect": "fade", "duration": 0.25},
                }
            ],
        }

        # when: the legacy document is parsed and serialized
        canvas = Canvas.from_json(json.dumps(raw))
        payload = json.loads(canvas.to_json())

        # then: the old effect discriminator and fields remain intact
        assert payload["layers"][0]["animation"] == {
            "animate": "entrance",
            "duration": 0.25,
            "delay": 0.0,
            "trigger": "on_click",
            "effect": "fade",
        }
