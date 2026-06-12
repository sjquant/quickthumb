"""Tests for HTML export (Canvas.to_html and rendering to .html files)"""

from quickthumb import Canvas


class TestHtmlExport:
    """Test suite for standalone HTML document export"""

    def test_should_emit_standalone_html_with_inline_svg(self):
        """to_html() wraps the SVG render in a complete HTML document"""
        # given
        canvas = Canvas(640, 360).background(color="#112233")

        # when
        html = canvas.to_html()

        # then
        assert html.startswith("<!DOCTYPE html>")
        assert '<svg xmlns="http://www.w3.org/2000/svg"' in html
        assert 'width="640" height="360"' in html
        assert "</html>" in html

    def test_should_escape_custom_title(self):
        """The document title is HTML-escaped"""
        # given
        canvas = Canvas(100, 100).background(color="#000000")

        # when
        html = canvas.to_html(title="A <thumb> & more")

        # then
        assert "<title>A &lt;thumb&gt; &amp; more</title>" in html

    def test_should_embed_fonts_by_default(self):
        """HTML output inlines fonts so the file is self-contained"""
        # given
        canvas = Canvas(400, 200).text(
            content="hello", font="Roboto", size=30, color="#FFFFFF", position=(20, 20)
        )

        # when
        html = canvas.to_html()

        # then
        assert "@font-face" in html
        assert "data:font/ttf;base64," in html

    def test_should_render_html_file_from_extension(self, tmp_path):
        """render() writes an HTML document when the output path ends in .html"""
        # given
        canvas = Canvas(200, 100).background(color="#FF0000")
        output = tmp_path / "out.html"

        # when
        canvas.render(str(output))

        # then
        assert output.read_text().startswith("<!DOCTYPE html>")
