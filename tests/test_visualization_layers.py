"""Black-box coverage for quickthumb's compact visualization layers."""

import base64
import json
import re
import zipfile
from io import BytesIO
from typing import Any, cast

import pytest
from PIL import Image, ImageChops
from quickthumb import (
    AnimationSpec,
    BarChartSpec,
    BarChartStyle,
    Canvas,
    ChartData,
    ChartLayer,
    ClipProgressTrack,
    Fade,
    GifOptions,
    KeyframeSpec,
    LineChartSpec,
    LineChartStyle,
    QRCodeLayer,
    RenderingError,
    TimingSpec,
    ValidationError,
    canvas_json_schema,
)
from quickthumb.cli import app
from typer.testing import CliRunner

from tests.test_export_snapshots import rasterize_pdf


def rendered_image(canvas: Canvas) -> Image.Image:
    """Return a decoded RGBA image from the public Canvas raster API."""
    data = base64.b64decode(canvas.to_base64())
    with Image.open(BytesIO(data)) as image:
        return image.convert("RGBA")


def rgb_pixel(image: Image.Image, x: int, y: int) -> tuple[int, int, int]:
    """Return an RGB pixel after narrowing Pillow's mode-dependent pixel type."""
    pixel = image.getpixel((x, y))
    if not isinstance(pixel, tuple) or len(pixel) < 3:
        raise AssertionError(f"expected a tuple pixel, got {pixel!r}")
    return cast(tuple[int, int, int], pixel[:3])


def embedded_png(markup: str) -> Image.Image:
    """Decode the first PNG data URI emitted by an HTML-like exporter."""
    match = re.search(r"data:image/png;base64,([^\"']+)", markup)
    if match is None:
        raise AssertionError("expected a PNG data URI")
    return Image.open(BytesIO(base64.b64decode(match.group(1)))).convert("RGBA")


class TestVisualizationValidation:
    """Test suite for public visualization model validation."""

    @pytest.mark.parametrize("values", [[], [4.0], [2.0, 2.0, 2.0], [-3.0, -1.0, 0.0]])
    def test_should_accept_defined_edge_case_data(self, values):
        """Empty, single-point, constant, and negative data are valid chart inputs."""
        # given
        canvas = Canvas(160, 100)

        # when
        canvas.chart(spec=LineChartSpec(data=values), position=(0, 0), width=80, height=40)

        # then
        layer = canvas.layers[0]
        assert isinstance(layer, ChartLayer)
        assert isinstance(layer.spec, LineChartSpec)
        assert isinstance(layer.spec.data, ChartData)
        assert layer.spec.data.values == values

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), "1"])
    def test_should_reject_non_finite_or_non_numeric_data(self, value: object):
        """Chart models reject values that cannot be rendered deterministically."""
        # given
        canvas = Canvas(160, 100)

        # when / then
        with pytest.raises(ValidationError, match="chart values"):
            canvas.chart(
                LineChartSpec(data=cast(Any, [value])), position=(0, 0), width=80, height=40
            )

    def test_should_validate_shared_chart_style_and_position(self):
        """Shared style fields use the same color, opacity, and coordinate constraints."""
        # given
        canvas = Canvas(160, 100)

        # when / then
        with pytest.raises(ValidationError, match="invalid hex color"):
            canvas.chart(
                BarChartSpec(data=[1, 2], style=BarChartStyle(color="blue")),
                position=(0, 0),
                width=80,
                height=40,
            )
        with pytest.raises(ValidationError, match="opacity"):
            canvas.chart(
                LineChartSpec(data=[1, 2], style=cast(Any, {"opacity": 2.0})),
                position=(0, 0),
                width=80,
                height=40,
            )

        with pytest.raises(ValidationError, match="opacity"):
            canvas.chart(
                LineChartSpec(data=[1, 2], style=cast(Any, {"opacity": float("nan")})),
                position=(0, 0),
                width=80,
                height=40,
            )

    def test_should_reject_extremely_large_integer_data_as_validation_error(self):
        """Huge integer samples fail through the public validation error contract."""
        # given
        canvas = Canvas(160, 100)

        # when / then
        with pytest.raises(ValidationError, match="chart values"):
            canvas.chart(
                LineChartSpec(data=cast(Any, [10**1000, 0])),
                position=(0, 0),
                width=80,
                height=40,
            )

    def test_should_render_extreme_finite_float_range_without_overflow(self):
        """Opposite extreme finite samples still map to deterministic chart pixels."""
        # given
        canvas = Canvas(160, 100).chart(
            LineChartSpec(data=[1e308, -1e308]), position=(0, 0), width=80, height=40
        )

        # when
        first = canvas.to_base64()
        second = (
            Canvas(160, 100)
            .chart(LineChartSpec(data=[1e308, -1e308]), position=(0, 0), width=80, height=40)
            .to_base64()
        )

        # then
        assert first == second

    def test_should_reject_chart_style_options_without_defined_semantics(self):
        """Chart builders reject style fields that belong to another chart type."""
        # given
        canvas = Canvas(160, 100)

        # when / then
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            canvas.chart(
                BarChartSpec(data=[1, 2], style=cast(Any, {"fill": "#FF0000"})),
                position=(0, 0),
                width=80,
                height=40,
            )
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            canvas.chart(
                LineChartSpec(data=[1, 2], style=cast(Any, {"bar_gap": 0.3})),
                position=(0, 0),
                width=80,
                height=40,
            )

    def test_should_reject_qr_code_that_cannot_preserve_all_modules(self):
        """QR rendering fails clearly when the requested square is smaller than its matrix."""
        # given
        canvas = Canvas(160, 100).qr_code("hello", position=(0, 0), size=1)

        # when / then
        with pytest.raises(RenderingError, match="too small"):
            canvas.to_base64()

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"data": "", "position": (0, 0), "size": 40},
            {"data": "hello", "position": (0,), "size": 40},
            {"data": "hello", "position": (0, 0), "size": 40, "quiet_zone": -1},
            {"data": "hello", "position": (0, 0), "size": 40, "error_correction": "X"},
        ],
    )
    def test_should_reject_invalid_qr_inputs(self, kwargs: dict[str, Any]):
        """QR data, position, quiet-zone, and correction contracts reject invalid inputs."""
        # given
        canvas = Canvas(160, 100)

        # when / then
        with pytest.raises(ValidationError):
            canvas.qr_code(**cast(Any, kwargs))


class TestVisualizationRendering:
    """Test suite for deterministic chart and QR raster behavior."""

    def test_should_render_all_visualization_types_deterministically(self):
        """All three visualization layers paint stable, repeated pixels."""

        # given
        def make_canvas() -> Canvas:
            return (
                Canvas(320, 180)
                .background(color="#FFFFFF")
                .chart(
                    BarChartSpec(
                        data=[-2, -1, 0, 3],
                        style=BarChartStyle(color="#0000FF", negative_color="#00AA00"),
                    ),
                    position=(105, 10),
                    width=80,
                    height=50,
                )
                .chart(
                    LineChartSpec(
                        data=[-1, 0, 2],
                        style=LineChartStyle(color="#7C3AED", fill="#DDD6FE"),
                    ),
                    position=(200, 10),
                    width=80,
                    height=50,
                )
                .qr_code("https://example.test", position=(10, 90), size=72)
            )

        first = make_canvas()
        second = make_canvas()

        # when
        first_png = first.to_base64()
        second_png = second.to_base64()
        image = rendered_image(first)

        # then
        assert first_png == second_png
        for box in ((105, 10, 185, 60), (200, 10, 280, 60), (10, 90, 82, 162)):
            crop = image.crop(box)
            assert any(
                rgb_pixel(crop, x, y) != (255, 255, 255)
                for x in range(crop.width)
                for y in range(crop.height)
            )

    def test_should_leave_an_empty_chart_transparent(self):
        """An empty chart has no accidental baseline, point, or fill pixels."""
        # given
        canvas = Canvas(100, 60).chart(
            LineChartSpec(data=[], style=LineChartStyle(show_points=False)),
            position=(10, 10),
            width=60,
            height=30,
        )
        expected = Image.new("RGBA", (100, 60), (0, 0, 0, 0))

        # when
        actual = rendered_image(canvas)

        # then
        assert ImageChops.difference(actual, expected).getbbox() is None

    def test_should_center_constant_line_data_and_show_bar_sign(self):
        """Constant lines center on the plot and negative bars render below zero."""
        # given
        canvas = (
            Canvas(160, 100)
            .chart(
                LineChartSpec(data=[4, 4, 4], style=LineChartStyle(color="#FF0000")),
                position=(5, 5),
                width=60,
                height=40,
            )
            .chart(
                BarChartSpec(data=[-2, 2], style=BarChartStyle(color="#0000FF")),
                position=(80, 5),
                width=60,
                height=70,
            )
        )

        # when
        image = rendered_image(canvas)

        # then
        assert rgb_pixel(image, 35, 25)[0] > 200
        assert rgb_pixel(image, 95, 55)[2] > 150
        assert rgb_pixel(image, 125, 20)[2] > 150

    def test_should_disable_line_markers_when_radius_is_zero(self):
        """A zero marker radius produces the same raster as explicitly hiding points."""
        # given
        without_points = rendered_image(
            Canvas(100, 60).chart(
                LineChartSpec(data=[0, 2], style=LineChartStyle(show_points=False)),
                position=(10, 10),
                width=60,
                height=30,
            )
        )

        # when
        zero_radius = rendered_image(
            Canvas(100, 60).chart(
                LineChartSpec(data=[0, 2], style=LineChartStyle(point_radius=0)),
                position=(10, 10),
                width=60,
                height=30,
            )
        )

        # then
        assert ImageChops.difference(without_points, zero_radius).getbbox() is None

    @pytest.mark.parametrize(
        ("animation", "spec", "time"),
        [
            (AnimationSpec.bar_grow(duration=1.0), BarChartSpec(data=[1, 3]), 0.0),
            (
                AnimationSpec.line_draw(duration=1.0),
                LineChartSpec(data=[1, 3, 2], style=LineChartStyle(show_points=False)),
                0.0,
            ),
            (
                AnimationSpec.area_reveal(duration=1.0),
                LineChartSpec(data=[1, 3, 2], style=LineChartStyle(fill="#DDEEFF")),
                0.0,
            ),
            (
                AnimationSpec.point_pop(duration=1.0),
                LineChartSpec(data=[1, 3, 2]),
                0.0,
            ),
        ],
    )
    def test_should_sample_chart_motion_without_changing_settled_pixels(
        self, animation, spec, time
    ):
        """Given a chart preset, when sampled before completion, then motion is visible and
        the settled frame matches the deterministic static renderer."""
        # given
        animated = Canvas(140, 90).chart(
            spec, position=(10, 10), width=100, height=50, animation=animation
        )
        static = Canvas(140, 90).chart(spec, position=(10, 10), width=100, height=50)

        # when
        start = animated._render_to_image(time=time)
        settled = animated._render_to_image(time=1.0)

        # then
        assert ImageChops.difference(start, settled).getbbox() is not None
        assert ImageChops.difference(settled, rendered_image(static)).getbbox() is None

    def test_should_compile_value_count_up_as_a_shared_clip_progress_track(self):
        """Given value count-up motion, when compiled, then it uses the shared timeline IR."""
        # given
        animation = AnimationSpec.value_count_up(duration=0.75)

        # when
        from quickthumb import LayerState, compile_timeline

        timeline = compile_timeline(animation)

        # then
        assert timeline.events[0].tracks[0].property == "clip_progress"
        assert timeline.sample(0, LayerState(clip_progress=0)).clip_progress == 0
        assert timeline.sample(0.75, LayerState(clip_progress=0)).clip_progress == 1

    def test_should_render_value_count_up_labels_deterministically(self):
        """Given value count-up motion, when sampled before and after completion, then labels
        change visibly and the settled labels remain deterministic."""
        # given
        canvas = Canvas(140, 90).chart(
            BarChartSpec(data=[1, 3]),
            position=(10, 10),
            width=100,
            height=50,
            animation=AnimationSpec.value_count_up(duration=1.0),
        )

        # when
        start = canvas._render_to_image(time=0.0)
        settled = canvas._render_to_image(time=1.0)
        repeated = canvas._render_to_image(time=1.0)

        # then
        assert ImageChops.difference(start, settled).getbbox() is not None
        assert settled.tobytes() == repeated.tobytes()

    def test_should_reveal_qr_modules_deterministically_over_time(self):
        """Given QR reveal motion, when sampled at the same times, then module pixels are
        deterministic and the settled frame matches static rendering."""
        # given
        animation = AnimationSpec.qr_reveal(duration=1.0)
        animated = Canvas(120, 120).qr_code(
            "motion", position=(10, 10), size=90, animation=animation
        )
        static = Canvas(120, 120).qr_code("motion", position=(10, 10), size=90)

        # when
        first = animated._render_to_image(time=0.4)
        second = animated._render_to_image(time=0.4)
        settled = animated._render_to_image(time=1.0)

        # then
        assert first.tobytes() == second.tobytes()
        assert ImageChops.difference(first.convert("RGB"), settled.convert("RGB")).getbbox()
        assert ImageChops.difference(settled, rendered_image(static)).getbbox() is None

    def test_should_reveal_qr_modules_in_row_major_progress_order(self):
        """Given QR reveal motion, when sampled partway through, then only the leading
        row-major module prefix is visible."""
        # given
        import qrcode  # ty: ignore[unresolved-import]

        animation = AnimationSpec.qr_reveal(duration=1.0)
        canvas = Canvas(120, 120).qr_code(
            "ordered", position=(10, 10), size=90, animation=animation
        )
        code = qrcode.QRCode(version=None, box_size=1, border=4)
        code.add_data("ordered", optimize=0)
        code.make(fit=True)
        matrix = code.get_matrix()
        progress = 0.25
        frame = canvas._render_to_image(time=progress)

        # when / then
        matrix_size = len(matrix)
        reveal_limit = progress * matrix_size * matrix_size
        for row, cells in enumerate(matrix):
            for column, cell in enumerate(cells):
                left = 10 + (column * 90) // matrix_size
                top = 10 + (row * 90) // matrix_size
                center = (
                    left + max(0, ((column + 1) * 90) // matrix_size - left - 1) // 2,
                    top + max(0, ((row + 1) * 90) // matrix_size - top - 1) // 2,
                )
                is_visible = rgb_pixel(frame, *center) == (0, 0, 0)
                assert is_visible == (bool(cell) and row * matrix_size + column < reveal_limit)

    def test_should_export_staggered_and_mixed_visualization_motion(self, tmp_path):
        """Given component and legacy animation entries together, when exported, then both
        timing systems remain valid and the component animation is not discarded."""
        # given
        canvas = Canvas(160, 100).chart(
            BarChartSpec(data=[1, 3, 2]),
            position=(5, 5),
            width=100,
            height=50,
            animation=[
                AnimationSpec.bar_grow(duration=0.2, stagger=0.05),
                Fade(duration=0.2),
            ],
        )
        output = tmp_path / "mixed-chart.gif"

        # when
        canvas.render(str(output), animation=GifOptions(fps=10))

        # then
        with Image.open(output) as image:
            assert getattr(cast(Any, image), "n_frames", 1) >= 2

    def test_should_honor_absolute_component_animation_start(self, tmp_path):
        """Given an absolute chart animation start, when exported, then the timeline includes
        the leading delay before the component settles."""
        # given
        canvas = Canvas(160, 100).chart(
            LineChartSpec(data=[1, 3, 2], style=LineChartStyle(show_points=False)),
            position=(5, 5),
            width=100,
            height=50,
            animation=AnimationSpec.timeline(
                ClipProgressTrack(
                    keyframes=[
                        KeyframeSpec(time=0.0, value=0.0),
                        KeyframeSpec(time=0.2, value=1.0),
                    ]
                ),
                timing=TimingSpec(start=0.4, duration=0.2),
            ),
        )
        output = tmp_path / "delayed-chart.gif"

        # when
        canvas.render(str(output), animation=GifOptions(fps=10))

        # then
        with Image.open(output) as image:
            total_duration = 0
            for frame_index in range(getattr(cast(Any, image), "n_frames", 1)):
                image.seek(frame_index)
                total_duration += image.info.get("duration", 0)
        assert total_duration >= 600

    def test_should_render_and_measure_visualization_group_children(self):
        """Groups render and inspect chart and QR children through the public APIs."""
        # given
        canvas = Canvas(220, 90).group(
            children=[
                {
                    "type": "chart",
                    "spec": {
                        "type": "bar",
                        "data": [-1, 2],
                        "style": {
                            "color": "#0000FF",
                            "negative_color": "#FF0000",
                            "bar_gap": 0.3,
                            "padding": 2,
                            "opacity": 0.8,
                        },
                    },
                    "width": 50,
                    "height": 35,
                },
                {
                    "type": "chart",
                    "spec": {"type": "line", "data": [1, 3, 2]},
                    "width": 60,
                    "height": 35,
                },
                {"type": "qr_code", "data": "group", "size": 40},
            ],
            direction="row",
            gap=8,
            position=(8, 8),
        )

        # when
        image = rendered_image(canvas)
        inspection = canvas.inspect()
        diagnostics = canvas.diagnose()

        # then
        assert image.getbbox() is not None
        assert [child.type for child in inspection.layers[0].children] == [
            "chart",
            "chart",
            "qr_code",
        ]
        assert all(child.bbox is not None for child in inspection.layers[0].children)
        for child in inspection.layers[0].children:
            assert child.bbox is not None
            bbox = child.bbox
            assert (
                image.crop((bbox.x, bbox.y, bbox.x + bbox.width, bbox.y + bbox.height)).getbbox()
                is not None
            )
        assert isinstance(diagnostics, list)

    def test_should_render_animated_chart_to_gif(self, tmp_path):
        """A chart layer participates in the existing deterministic GIF animation path."""
        # given
        canvas = Canvas(160, 100).chart(
            LineChartSpec(data=[1, 3, 2], style=LineChartStyle(color="#2563EB")),
            position=(10, 10),
            width=80,
            height=40,
            animation=Fade(duration=0.5),
        )
        output = tmp_path / "animated-chart.gif"

        # when
        canvas.render(str(output), animation=GifOptions(fps=10))

        # then
        with Image.open(output) as rendered:
            frame_count = getattr(rendered, "n_frames", 1)
            assert frame_count >= 2
            rendered.seek(0)
            first = rendered.convert("RGB").copy()
            rendered.seek(frame_count - 1)
            last = rendered.convert("RGB").copy()
        assert ImageChops.difference(first, last).getbbox() is not None


class TestVisualizationSerialization:
    """Test suite for JSON, schema, and CLI visualization support."""

    def test_should_round_trip_all_visualization_layer_discriminators(self):
        """JSON loading and serialization preserve visualization behavior fields."""
        # given
        payload = {
            "width": 240,
            "height": 160,
            "layers": [
                {
                    "type": "chart",
                    "spec": {
                        "type": "bar",
                        "data": [-1, 2],
                        "style": {
                            "color": "#0000FF",
                            "negative_color": "#FF0000",
                            "bar_gap": 0.3,
                            "padding": 2,
                            "opacity": 0.8,
                        },
                    },
                    "position": [0, 0],
                    "width": 50,
                    "height": 20,
                },
                {
                    "type": "chart",
                    "spec": {
                        "type": "line",
                        "data": [2, 3],
                        "style": {
                            "color": "#00AA00",
                            "fill": "#CCFFCC",
                            "fill_opacity": 0.4,
                            "stroke_width": 3,
                            "point_radius": 1,
                            "show_points": False,
                            "padding": 1,
                            "opacity": 0.9,
                        },
                    },
                    "position": [60, 0],
                    "width": 50,
                    "height": 20,
                },
                {
                    "type": "qr_code",
                    "data": "hello",
                    "position": [120, 0],
                    "size": 50,
                    "foreground": "#111111",
                    "background": "#EEEEEE",
                    "error_correction": "H",
                    "quiet_zone": 4,
                    "opacity": 0.75,
                },
            ],
        }

        # when
        canvas = Canvas.from_json(json.dumps(payload))
        serialized = json.loads(canvas.to_json())
        reloaded = Canvas.from_json(json.dumps(serialized))

        # then
        assert [layer["type"] for layer in serialized["layers"]] == [
            "chart",
            "chart",
            "qr_code",
        ]
        assert serialized["layers"][0]["spec"]["data"] == [-1.0, 2.0]
        assert serialized["layers"][0]["spec"]["style"]["bar_gap"] == 0.3
        assert serialized["layers"][1]["spec"]["style"]["show_points"] is False
        assert serialized["layers"][2]["data"] == "hello"
        assert serialized["layers"][2]["error_correction"] == "H"
        assert serialized["layers"][2]["foreground"] == "#111111"
        assert json.loads(reloaded.to_json()) == serialized

    def test_should_round_trip_visualization_animation(self):
        """Chart and QR animation fields survive JSON serialization and loading."""
        # given
        canvas = (
            Canvas(240, 160)
            .chart(
                LineChartSpec(data=[1, 2, 3]),
                position=(0, 0),
                width=80,
                height=40,
                animation=Fade(duration=0.25),
            )
            .qr_code("hello", position=(100, 0), size=50, animation=Fade(duration=0.4))
        )

        # when
        reloaded = Canvas.from_json(canvas.to_json())

        # then
        line = reloaded.layers[0]
        qr = reloaded.layers[1]
        assert isinstance(line, ChartLayer)
        assert isinstance(line.spec, LineChartSpec)
        assert isinstance(qr, QRCodeLayer)
        assert isinstance(line.animation, Fade)
        assert isinstance(qr.animation, Fade)
        assert line.animation.duration == 0.25
        assert qr.animation.duration == 0.4

    def test_should_round_trip_data_driven_animation_presets(self):
        """Given chart and QR component presets, when serialized, then their canonical
        animation discriminators and timing survive a JSON round-trip."""
        # given
        canvas = (
            Canvas(240, 160)
            .chart(
                BarChartSpec(data=[1, 2, 3]),
                position=(0, 0),
                width=80,
                height=40,
                animation=AnimationSpec.bar_grow(duration=0.6, stagger=0.1),
            )
            .qr_code(
                "hello",
                position=(100, 0),
                size=50,
                animation=AnimationSpec.qr_reveal(duration=0.8),
            )
        )

        # when
        reloaded = Canvas.from_json(canvas.to_json())

        # then
        assert reloaded.layers[0].animation.effect.type == "bar_grow"
        assert reloaded.layers[0].animation.stagger.delay == 0.1
        assert reloaded.layers[1].animation.effect.type == "qr_reveal"
        assert reloaded.layers[1].animation.timing.duration == 0.8

    def test_should_validate_complete_visualization_document_against_canvas_model(self):
        """The serialized visualization document satisfies the published model schema."""
        # given
        canvas = (
            Canvas(240, 160)
            .chart(LineChartSpec(data=[-2, 3]), position=(0, 0), width=80, height=40)
            .qr_code("schema", position=(100, 0), size=50)
        )
        payload = json.loads(canvas.to_json())

        # when
        from quickthumb.models import CanvasModel

        validated = CanvasModel.model_validate(payload)

        # then
        assert validated.width == 240
        assert validated.layers[0].type == "chart"
        assert validated.layers[1].type == "qr_code"
        assert "spec" in canvas_json_schema()["$defs"]["ChartLayer"]["properties"]

    def test_should_publish_visualization_schema_discriminators(self):
        """The generated schema advertises validated chart data, style, and QR contracts."""
        # given
        schema = canvas_json_schema()

        # when
        mapping = schema["properties"]["layers"]["items"]["discriminator"]["mapping"]
        definitions = schema["$defs"]

        # then
        assert set(mapping) >= {"chart", "qr_code"}
        assert "ChartData" in definitions
        assert "BarChartStyle" in definitions
        assert "LineChartStyle" in definitions
        assert definitions["QRCodeLayer"]["properties"]["error_correction"]["enum"] == [
            "L",
            "M",
            "Q",
            "H",
        ]

    def test_should_publish_chart_data_input_forms_used_by_serialization(self):
        """The chart schema accepts both numeric arrays and named ChartData objects."""
        # given
        schema = canvas_json_schema()

        # when
        bar_data = schema["$defs"]["BarChartSpec"]["properties"]["data"]
        line_data = schema["$defs"]["LineChartSpec"]["properties"]["data"]

        # then
        for data_schema in (bar_data, line_data):
            assert {"type": "array", "items": {"type": "number"}} in data_schema["anyOf"]
            assert {"$ref": "#/$defs/ChartData"} in data_schema["anyOf"]

    def test_should_render_visualization_json_through_cli(self, tmp_path):
        """The public render command accepts a visualization-only JSON document."""
        # given
        spec = tmp_path / "visualization.json"
        output = tmp_path / "visualization.png"
        spec.write_text(
            json.dumps(
                {
                    "kind": "canvas",
                    "width": 160,
                    "height": 120,
                    "layers": [
                        {
                            "type": "chart",
                            "spec": {"type": "bar", "data": [-2, 3]},
                            "position": [100, 10],
                            "width": 50,
                            "height": 40,
                        },
                        {
                            "type": "chart",
                            "spec": {"type": "line", "data": [-1, 0, 1]},
                            "position": [10, 10],
                            "width": 80,
                            "height": 40,
                        },
                        {"type": "qr_code", "data": "cli", "position": [10, 55], "size": 50},
                    ],
                }
            )
        )

        # when
        result = CliRunner().invoke(app, ["render", str(spec), "--output", str(output)])

        # then
        assert result.exit_code == 0, result.output
        assert output.exists()
        with Image.open(output) as image:
            rendered = image.convert("RGBA")
        assert rendered.size == (160, 120)
        assert rendered.crop((10, 10, 90, 50)).getbbox() is not None
        assert rendered.crop((100, 10, 150, 50)).getbbox() is not None
        assert rendered.crop((10, 55, 60, 105)).getbbox() is not None


class TestVisualizationExportFallback:
    """Test suite for document exporter behavior with raster-native visualizations."""

    def test_should_preserve_visualizations_in_svg_and_html_fallbacks(self):
        """SVG and HTML exports embed the same raster layer when no native
        chart primitive exists."""
        # given
        canvas = Canvas(160, 120).chart(
            LineChartSpec(data=[1, 3, 2]), position=(10, 10), width=80, height=40
        )

        # when
        expected = rendered_image(canvas)
        svg = canvas.to_svg()
        html = canvas.to_html()

        # then
        expected_layer = expected.crop((10, 10, 90, 50))
        assert ImageChops.difference(expected_layer, embedded_png(svg)).getbbox() is None
        assert ImageChops.difference(expected_layer, embedded_png(html)).getbbox() is None

    def test_should_preserve_qr_code_in_optional_document_exports(self):
        """PDF and PPTX exports keep QR pixels through their established picture fallback."""
        # given
        canvas = Canvas(160, 120).qr_code("document", position=(20, 20), size=70)

        # when
        expected = rendered_image(canvas)
        pptx = canvas.to_pptx()

        # then
        pdf_image = rasterize_pdf(canvas)
        pdf_crop = pdf_image.crop((20, 20, 90, 90))
        from quickthumb import assert_image_similar

        assert_image_similar(expected.crop((20, 20, 90, 90)), pdf_crop, threshold=0.95)
        with zipfile.ZipFile(BytesIO(pptx)) as archive:
            media = [name for name in archive.namelist() if name.startswith("ppt/media/")]
            assert len(media) == 1
            exported = Image.open(BytesIO(archive.read(media[0]))).convert("RGBA")
        assert ImageChops.difference(expected.crop((20, 20, 90, 90)), exported).getbbox() is None

    def test_should_emit_pptx_timing_for_animated_visualization(self):
        """PPTX export keeps animation timing when a visualization is rasterized."""
        # given
        canvas = Canvas(160, 120).chart(
            LineChartSpec(data=[1, 3, 2]),
            position=(10, 10),
            width=80,
            height=40,
            animation=Fade(duration=0.25),
        )

        # when
        presentation = canvas.to_pptx()

        # then
        with zipfile.ZipFile(BytesIO(presentation)) as archive:
            slide_xml = archive.read("ppt/slides/slide1.xml")
        assert b"<p:timing" in slide_xml
        assert b'dur="250"' in slide_xml
        assert b"<p:spTgt" in slide_xml
