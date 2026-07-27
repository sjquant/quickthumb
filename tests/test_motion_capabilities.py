import pytest
from quickthumb import (
    AnimationSpec,
    BlurTrack,
    Canvas,
    Deck,
    ExportPolicy,
    ImagePanTrack,
    KeyframeSpec,
    PositionTrack,
    capabilities_for,
)
from quickthumb.errors import RenderingError


class TestMotionCapabilities:
    """Black-box coverage for the renderer-independent capability contract."""

    def test_should_declare_capabilities_for_each_export_family(self):
        """Raster/video, HTML, and PPTX expose an explicit feature row."""
        # given: the public capability registry
        # when: each supported target is inspected
        rows = {target: capabilities_for(target) for target in ("raster", "video", "html", "pptx")}

        # then: every row declares the same feature vocabulary
        assert set(rows["raster"]) == set(rows["video"]) == set(rows["html"]) == set(rows["pptx"])
        assert rows["raster"]["position"].support == "full"
        assert rows["video"]["audio_sync"].support == "full"
        assert rows["html"]["blur"].support == "partial"
        assert rows["pptx"]["blur"].fallback == "rasterize"

    def test_should_report_native_and_fallback_motion_without_rendering(self):
        """Validation reports target, layer, feature, support, fallback, and message."""
        # given: canonical motion that current exporters have not compiled yet
        canvas = Canvas(100, 100)
        canvas.text(
            "Motion",
            position=(0, 0),
            animation=AnimationSpec.timeline(
                PositionTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(0, 0)),
                        KeyframeSpec(time=1, value=(10, 10)),
                    ]
                ),
                BlurTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=4)]),
            ),
        )

        # when: the canvas is validated for PPTX
        diagnostics = canvas.validate_export("pptx")

        # then: the report is structured and honest about current export support
        assert [(item.feature, item.support) for item in diagnostics] == [
            ("position", "fallback"),
            ("blur", "fallback"),
        ]
        assert diagnostics[1].target == "pptx"
        assert diagnostics[1].layer_id == "layer:0"
        assert diagnostics[1].fallback == "static"
        assert "blur" in diagnostics[1].message

    def test_should_report_image_viewport_motion_as_pptx_raster_fallback(self):
        """Given image viewport motion, PPTX validation reports its composition fallback."""
        # Given: an image pan track that depends on pixel composition
        canvas = Canvas(100, 100).image(
            path="tests/fixtures/sample_image.jpg",
            position=(0, 0),
            width=100,
            height=100,
            fit="cover",
            animation=AnimationSpec.timeline(
                ImagePanTrack(
                    keyframes=[
                        KeyframeSpec(time=0, value=(-1, 0)),
                        KeyframeSpec(time=1, value=(1, 0)),
                    ]
                )
            ),
        )

        # When: the image is checked for PPTX export
        diagnostics = canvas.validate_export("pptx")

        # Then: the exporter contract requests deterministic raster fallback
        assert diagnostics[0].feature == "image_pan"
        assert diagnostics[0].support == "fallback"
        assert diagnostics[0].fallback == "static"

    def test_should_report_video_layers_as_static_raster_fallbacks_for_document_exports(self):
        """Given a video layer, document export validation describes its static fallback."""
        # Given: a public video composition that document exporters cannot animate
        canvas = Canvas(100, 100).video("clip.mp4", (0, 0), 100, 100)

        # When: the canvas is checked for HTML and PPTX export
        html = canvas.validate_export("html")
        pptx = canvas.validate_export("pptx")

        # Then: both reports identify deterministic rasterization
        assert [(item.feature, item.fallback) for item in html] == [
            ("video_layer", "rasterize")
        ]
        assert [(item.feature, item.fallback) for item in pptx] == [
            ("video_layer", "rasterize")
        ]
        assert html[0].support == "fallback"

    def test_should_resolve_error_rasterize_and_static_policies(self):
        """Unsupported motion policies resolve to distinct deterministic outcomes."""
        # given: a canvas with motion unsupported by PPTX
        canvas = Canvas(100, 100).text(
            "Motion",
            position=(0, 0),
            animation=AnimationSpec.timeline(
                BlurTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=4)])
            ),
        )

        # when: each policy is applied to the same source
        warned = canvas.validate_export("pptx", ExportPolicy(unsupported_motion="warn"))
        rasterized = canvas.validate_export("pptx", ExportPolicy(unsupported_motion="rasterize"))
        static = canvas.validate_export("pptx", ExportPolicy(unsupported_motion="static"))

        # then: each fallback is visible in the diagnostic contract
        assert warned[0].support == "fallback"
        assert warned[0].fallback == "static"
        assert rasterized[0].fallback == "rasterize"
        assert static[0].fallback == "static"
        with pytest.raises(RenderingError):
            canvas.validate_export("pptx", ExportPolicy(unsupported_motion="error"))

    def test_should_apply_layer_policy_using_shared_layer_ids(self):
        """A PPTX layer override uses the same identifier as inspection diagnostics."""
        # given: canonical motion on the first canvas layer
        canvas = Canvas(100, 100).text(
            "Motion",
            position=(0, 0),
            animation=AnimationSpec.fade(),
        )

        # when: the layer is explicitly configured for raster fallback
        diagnostics = canvas.validate_export("pptx", ExportPolicy(pptx={"layer:0": "rasterize"}))

        # then: the override is applied to the matching layer
        assert diagnostics[0].layer_id == "layer:0"
        assert diagnostics[0].fallback == "rasterize"

    def test_should_reject_native_policy_for_unsupported_motion(self):
        """A native override cannot contradict an unsupported capability."""
        # given: canonical blur motion and a contradictory native override
        canvas = Canvas(100, 100).text(
            "Motion",
            position=(0, 0),
            animation=AnimationSpec.timeline(
                BlurTrack(keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=4)])
            ),
        )

        # when/then: validation rejects the contradictory policy
        with pytest.raises(RenderingError, match="cannot use native"):
            canvas.validate_export("pptx", ExportPolicy(pptx={"layer:0": "native"}))

    def test_should_validate_deck_and_nested_layer_ids(self):
        """Deck validation traverses nested layers with stable child identifiers."""
        # given: a deck containing a nested animated child
        canvas = Canvas(100, 100).group(
            children=[{"type": "text", "content": "Motion", "animation": AnimationSpec.fade()}]
        )
        deck = Deck(100, 100).slide(canvas)

        # when: the deck is validated for PPTX
        diagnostics = deck.validate_export("pptx")

        # then: the child diagnostic uses the shared nested-layer identifier
        assert [item.layer_id for item in diagnostics] == ["layer:0:0"]
