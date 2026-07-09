import os
import tempfile

import pytest


class TestFontCache:
    def test_should_find_font_by_family_name(self):
        from quickthumb.font_cache import FontCache

        cache = FontCache.get_instance()
        roboto_path = cache.find_font("Roboto")

        assert roboto_path is not None
        assert os.path.exists(roboto_path)

    def test_should_handle_case_insensitive_lookup(self):
        from quickthumb.font_cache import FontCache

        cache = FontCache.get_instance()
        roboto_lower = cache.find_font("roboto")
        roboto_upper = cache.find_font("ROBOTO")
        roboto_mixed = cache.find_font("RoBoTo")

        assert roboto_lower is not None
        assert roboto_upper is not None
        assert roboto_mixed is not None
        assert roboto_lower == roboto_upper == roboto_mixed

    def test_should_match_regular_variant(self):
        from quickthumb.font_cache import FontCache

        cache = FontCache.get_instance()
        font_path = cache.find_font("Roboto", bold=False, italic=False)

        assert font_path is not None
        assert "Roboto-Regular.ttf" in font_path

    def test_should_match_bold_variant(self):
        from quickthumb.font_cache import FontCache

        cache = FontCache.get_instance()
        font_path = cache.find_font("Roboto", bold=True, italic=False)

        assert font_path is not None
        assert "Roboto-Bold.ttf" in font_path

    def test_should_match_italic_variant(self):
        from quickthumb.font_cache import FontCache

        cache = FontCache.get_instance()
        font_path = cache.find_font("Roboto", bold=False, italic=True)

        assert font_path is not None
        assert "Roboto-Italic.ttf" in font_path

    def test_should_match_bold_italic_variant(self):
        from quickthumb.font_cache import FontCache

        cache = FontCache.get_instance()
        font_path = cache.find_font("Roboto", bold=True, italic=True)

        assert font_path is not None
        assert "Roboto-BoldItalic.ttf" in font_path

    def test_should_return_none_for_unknown_font(self):
        from quickthumb.font_cache import FontCache

        cache = FontCache.get_instance()
        unknown_path = cache.find_font("NonExistentFont")

        assert unknown_path is None

    def test_should_return_default_font_when_env_var_is_set(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_DEFAULT_FONT", "Roboto")
        cache = FontCache()
        default_path = cache.default_font()

        assert default_path is not None
        assert os.path.exists(default_path)
        assert "Roboto" in default_path

    def test_should_return_none_when_default_font_env_var_not_set(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.delenv("QUICKTHUMB_DEFAULT_FONT", raising=False)
        cache = FontCache()
        default_path = cache.default_font()

        assert default_path is None

    def test_should_return_none_when_default_font_does_not_exist(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_DEFAULT_FONT", "NonExistentFont")
        cache = FontCache()
        default_path = cache.default_font()

        assert default_path is None


class TestFontCacheNumericWeight:
    def test_should_match_thin_weight_100(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=100, italic=False)

        assert font_path is not None
        assert "NotoSerif-Thin.ttf" in font_path

    def test_should_match_extralight_weight_200(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=200, italic=False)

        assert font_path is not None
        assert "NotoSerif-ExtraLight.ttf" in font_path

    def test_should_match_light_weight_300(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=300, italic=False)

        assert font_path is not None
        assert "NotoSerif-Light.ttf" in font_path

    def test_should_match_regular_weight_400(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=400, italic=False)

        assert font_path is not None
        assert "NotoSerif-Regular.ttf" in font_path

    def test_should_match_medium_weight_500(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=500, italic=False)

        assert font_path is not None
        assert "NotoSerif-Medium.ttf" in font_path

    def test_should_match_semibold_weight_600(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=600, italic=False)

        assert font_path is not None
        assert "NotoSerif-SemiBold.ttf" in font_path

    def test_should_match_bold_weight_700(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=700, italic=False)

        assert font_path is not None
        assert "NotoSerif-Bold.ttf" in font_path

    def test_should_match_extrabold_weight_800(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=800, italic=False)

        assert font_path is not None
        assert "NotoSerif-ExtraBold.ttf" in font_path

    def test_should_match_black_weight_900(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=900, italic=False)

        assert font_path is not None
        assert "NotoSerif-Black.ttf" in font_path

    def test_should_match_weight_with_italic(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=700, italic=True)

        assert font_path is not None
        assert "NotoSerif-BoldItalic.ttf" in font_path


class TestFontCacheNamedWeight:
    def test_should_match_named_weight_thin(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="thin", italic=False)

        assert font_path is not None
        assert "NotoSerif-Thin.ttf" in font_path

    def test_should_match_named_weight_extra_light(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="extra-light", italic=False)

        assert font_path is not None
        assert "NotoSerif-ExtraLight.ttf" in font_path

    def test_should_match_named_weight_light(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="light", italic=False)

        assert font_path is not None
        assert "NotoSerif-Light.ttf" in font_path

    def test_should_match_named_weight_normal(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="normal", italic=False)

        assert font_path is not None
        assert "NotoSerif-Regular.ttf" in font_path

    def test_should_match_named_weight_regular(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="regular", italic=False)

        assert font_path is not None
        assert "NotoSerif-Regular.ttf" in font_path

    def test_should_match_named_weight_medium(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="medium", italic=False)

        assert font_path is not None
        assert "NotoSerif-Medium.ttf" in font_path

    def test_should_match_named_weight_semi_bold(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="semi-bold", italic=False)

        assert font_path is not None
        assert "NotoSerif-SemiBold.ttf" in font_path

    def test_should_match_named_weight_bold(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="bold", italic=False)

        assert font_path is not None
        assert "NotoSerif-Bold.ttf" in font_path

    def test_should_match_named_weight_extra_bold(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="extra-bold", italic=False)

        assert font_path is not None
        assert "NotoSerif-ExtraBold.ttf" in font_path

    def test_should_match_named_weight_black(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="black", italic=False)

        assert font_path is not None
        assert "NotoSerif-Black.ttf" in font_path

    def test_should_handle_case_insensitive_named_weight(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_bold = cache.find_font("NotoSerif", weight="BOLD", italic=False)
        font_medium = cache.find_font("NotoSerif", weight="Medium", italic=False)

        assert font_bold is not None
        assert "NotoSerif-Bold.ttf" in font_bold
        assert font_medium is not None
        assert "NotoSerif-Medium.ttf" in font_medium


class TestFontCacheFallbackMechanism:
    def test_should_find_closest_weight_when_exact_not_available(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("Roboto", weight=600, italic=False)

        assert font_path is not None
        assert "Roboto" in font_path

    def test_should_prefer_heavier_weight_when_equidistant(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("Roboto", weight=600, italic=False)

        assert font_path is not None

    def test_should_fallback_to_any_weight_when_italic_not_available(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        cache = FontCache()
        font_path = cache.find_font("Roboto", weight=100, italic=True)

        assert font_path is not None
        assert "Roboto" in font_path


class TestFontEngineLoading:
    def test_should_cache_google_font_by_family_weight_and_style(self, monkeypatch):
        """Google Fonts family loading uses deterministic cached CSS and font files"""
        import hashlib
        from unittest.mock import MagicMock, patch

        from quickthumb import Canvas

        with open("assets/fonts/Roboto-Regular.ttf", "rb") as f:
            real_font_data = f.read()

        with tempfile.TemporaryDirectory() as cache_dir:
            # Given: Google Fonts CSS points at a downloadable font file
            monkeypatch.setenv("QUICKTHUMB_FONT_CACHE_DIR", cache_dir)
            css = (
                b"@font-face{font-family:'Roboto';font-style:normal;font-weight:400;"
                b"src:url(https://fonts.gstatic.com/s/roboto/v1/Roboto-Regular.ttf)"
                b" format('truetype');}"
            )
            css_response = MagicMock()
            css_response.__enter__ = lambda s: s
            css_response.__exit__ = MagicMock(return_value=False)
            css_response.read.return_value = css
            font_response = MagicMock()
            font_response.__enter__ = lambda s: s
            font_response.__exit__ = MagicMock(return_value=False)
            font_response.read.return_value = real_font_data

            # When: two separate canvases render with the same Google font family
            output_a = os.path.join(cache_dir, "a.png")
            output_b = os.path.join(cache_dir, "b.png")
            with patch("quickthumb._fonts.urlopen", side_effect=[css_response, font_response]) as u:
                Canvas(200, 100).background(color="#FFFFFF").text(
                    "Hello",
                    font="Roboto",
                    font_source="google",
                    size=24,
                    color="#000000",
                ).render(output_a)
                Canvas(200, 100).background(color="#FFFFFF").text(
                    "Hello",
                    font="Roboto",
                    font_source="google",
                    size=24,
                    color="#000000",
                ).render(output_b)

            # Then: CSS and font were fetched once, and the deterministic cache files exist
            cache_hash = hashlib.md5(b"Roboto|400|0").hexdigest()
            assert u.call_count == 2
            assert os.path.exists(os.path.join(cache_dir, f"quickthumb_google_{cache_hash}.css"))
            assert os.path.exists(os.path.join(cache_dir, f"quickthumb_google_{cache_hash}.ttf"))

    def test_should_refresh_stale_google_css_for_google_font_prefix(self, monkeypatch):
        """google: family shorthand refreshes stale CSS without a usable font URL"""
        import hashlib
        from unittest.mock import MagicMock, patch

        from quickthumb import Canvas

        with open("assets/fonts/Roboto-Regular.ttf", "rb") as f:
            real_font_data = f.read()

        with tempfile.TemporaryDirectory() as cache_dir:
            # Given: a stale cached CSS file for the google: font family shorthand
            monkeypatch.setenv("QUICKTHUMB_FONT_CACHE_DIR", cache_dir)
            cache_hash = hashlib.md5(b"Roboto|400|0").hexdigest()
            css_path = os.path.join(cache_dir, f"quickthumb_google_{cache_hash}.css")
            with open(css_path, "w", encoding="utf-8") as f:
                f.write("@font-face{src:local('Roboto');}")

            fresh_css = (
                b"@font-face{font-family:'Roboto';font-style:normal;font-weight:400;"
                b"src:url(https://fonts.gstatic.com/s/roboto/v1/Roboto-Regular.ttf)"
                b" format('truetype');}"
            )
            css_response = MagicMock()
            css_response.__enter__ = lambda s: s
            css_response.__exit__ = MagicMock(return_value=False)
            css_response.read.return_value = fresh_css
            font_response = MagicMock()
            font_response.__enter__ = lambda s: s
            font_response.__exit__ = MagicMock(return_value=False)
            font_response.read.return_value = real_font_data

            # When: rendering text with the google: prefix
            output_path = os.path.join(cache_dir, "output.png")
            with patch("quickthumb._fonts.urlopen", side_effect=[css_response, font_response]):
                Canvas(200, 100).background(color="#FFFFFF").text(
                    "Hello",
                    font="google:Roboto",
                    size=24,
                    color="#000000",
                ).render(output_path)

            # Then: stale CSS is replaced and a valid font cache entry is written
            with open(css_path, encoding="utf-8") as f:
                assert "fonts.gstatic.com" in f.read()
            assert os.path.exists(os.path.join(cache_dir, f"quickthumb_google_{cache_hash}.ttf"))

    def test_should_raise_rendering_error_when_google_font_css_fetch_fails(self, monkeypatch):
        """Google font network failures surface as RenderingError"""
        from unittest.mock import patch

        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        with tempfile.TemporaryDirectory() as cache_dir:
            # Given: Google Fonts CSS cannot be fetched
            monkeypatch.setenv("QUICKTHUMB_FONT_CACHE_DIR", cache_dir)
            canvas = (
                Canvas(200, 100)
                .background(color="#FFFFFF")
                .text("Hello", font="Roboto", font_source="google", size=24, color="#000000")
            )

            # When: rendering the text
            with (
                patch("quickthumb._fonts.urlopen", side_effect=OSError("offline")),
                pytest.raises(RenderingError, match="Failed to fetch Google font"),
            ):
                # Then: a clear RenderingError is raised
                canvas.render(os.path.join(cache_dir, "output.png"))

    def test_should_raise_rendering_error_when_google_font_payload_is_invalid(self, monkeypatch):
        """Google font downloads validate that cached payloads are font files"""
        from unittest.mock import MagicMock, patch

        from quickthumb import Canvas
        from quickthumb.errors import RenderingError

        with tempfile.TemporaryDirectory() as cache_dir:
            # Given: Google Fonts CSS resolves to non-font bytes
            monkeypatch.setenv("QUICKTHUMB_FONT_CACHE_DIR", cache_dir)
            css = (
                b"@font-face{font-family:'Roboto';font-style:normal;font-weight:400;"
                b"src:url(https://fonts.gstatic.com/s/roboto/v1/Roboto-Regular.ttf)"
                b" format('truetype');}"
            )
            css_response = MagicMock()
            css_response.__enter__ = lambda s: s
            css_response.__exit__ = MagicMock(return_value=False)
            css_response.read.return_value = css
            font_response = MagicMock()
            font_response.__enter__ = lambda s: s
            font_response.__exit__ = MagicMock(return_value=False)
            font_response.read.return_value = b"<html>not a font</html>"

            # When: rendering the text
            canvas = (
                Canvas(200, 100)
                .background(color="#FFFFFF")
                .text("Hello", font="Roboto", font_source="google", size=24, color="#000000")
            )
            with (
                patch("quickthumb._fonts.urlopen", side_effect=[css_response, font_response]),
                pytest.raises(RenderingError, match="not a valid font"),
            ):
                # Then: invalid font bytes are rejected
                canvas.render(os.path.join(cache_dir, "output.png"))

    def test_should_cache_webfont_url_with_query_string_and_warn_for_style_flags(self, monkeypatch):
        """Webfont URL loading strips query strings for extension and ignores style flags"""
        import hashlib
        from unittest.mock import MagicMock, patch

        from quickthumb import Canvas

        with open("assets/fonts/Roboto-Regular.ttf", "rb") as f:
            real_font_data = f.read()

        with tempfile.TemporaryDirectory() as cache_dir:
            # Given: a styled text layer points at a direct webfont URL with query params
            monkeypatch.setenv("QUICKTHUMB_FONT_CACHE_DIR", cache_dir)
            mock_response = MagicMock()
            mock_response.__enter__ = lambda s: s
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_response.read.return_value = real_font_data
            font_url = "https://example.com/Roboto.ttf?v=1"
            canvas = (
                Canvas(200, 100)
                .background(color="#FFFFFF")
                .text("Hello", font=font_url, bold=True, size=24, color="#000000")
            )

            # When: rendering with style flags that URL fonts cannot honor
            with (
                patch("quickthumb._fonts.urlopen", return_value=mock_response),
                pytest.warns(UserWarning, match="ignored for webfont URLs"),
            ):
                canvas.render(os.path.join(cache_dir, "output.png"))

            # Then: the URL cache uses a stable hash and the real font extension
            url_hash = hashlib.md5(font_url.encode()).hexdigest()
            cached_file = os.path.join(cache_dir, f"quickthumb_font_{url_hash}.ttf")
            assert os.path.exists(cached_file)

    def test_should_warn_and_render_when_variation_axis_is_not_available(self, tmp_path):
        """Static fonts ignore unsupported variation axes with a clear fallback warning"""
        from quickthumb import Canvas

        # Given: a static repo font with an explicit variation request
        canvas = (
            Canvas(220, 100)
            .background(color="#FFFFFF")
            .text(
                "Axis",
                font="Roboto",
                font_variations={"wdth": 75},
                size=36,
                color="#000000",
                position=(20, 30),
            )
        )

        # When: rendering the text
        output = tmp_path / "axis.png"
        with pytest.warns(UserWarning, match="font_variations"):
            canvas.render(str(output))

        # Then: the static font fallback still renders output
        assert output.exists()
        assert output.stat().st_size > 0
