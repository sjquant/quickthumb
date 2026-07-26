import pytest
from quickthumb import (
    AnimationSpec,
    BlurTrack,
    Canvas,
    ExportPolicy,
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
        assert rows["raster"]["blur"].support == "full"
        assert rows["html"]["blur"].support == "partial"
        assert rows["pptx"]["blur"].fallback == "rasterize"

    def test_should_report_native_and_fallback_motion_without_rendering(self):
        """Validation reports target, layer, feature, support, fallback, and message."""
        # given: one native PPTX transform and one unsupported PPTX blur track
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
                BlurTrack(
                    keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=4)]
                ),
            ),
        )

        # when: the canvas is validated for PPTX
        diagnostics = canvas.validate_export("pptx")

        # then: the report is structured and deterministic
        assert [(item.feature, item.support) for item in diagnostics] == [
            ("position", "native"),
            ("blur", "fallback"),
        ]
        assert diagnostics[1].target == "pptx"
        assert diagnostics[1].layer_id == "slide-0-layer-0"
        assert diagnostics[1].fallback == "rasterize"
        assert "blur" in diagnostics[1].message

    def test_should_resolve_error_rasterize_and_static_policies(self):
        """Unsupported motion policies resolve to distinct deterministic outcomes."""
        # given: a canvas with motion unsupported by PPTX
        canvas = Canvas(100, 100).text(
            "Motion",
            position=(0, 0),
            animation=AnimationSpec.timeline(
                BlurTrack(
                    keyframes=[KeyframeSpec(time=0, value=0), KeyframeSpec(time=1, value=4)]
                )
            ),
        )

        # when: each policy is applied to the same source
        rasterized = canvas.validate_export(
            "pptx", ExportPolicy(unsupported_motion="rasterize")
        )
        static = canvas.validate_export("pptx", ExportPolicy(unsupported_motion="static"))

        # then: each fallback is visible in the diagnostic contract
        assert rasterized[0].fallback == "rasterize"
        assert static[0].fallback == "static"
        with pytest.raises(RenderingError):
            canvas.validate_export("pptx", ExportPolicy(unsupported_motion="error"))
