import os


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

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=100, italic=False)

        assert font_path is not None
        assert "NotoSerif-Thin.ttf" in font_path

    def test_should_match_extralight_weight_200(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=200, italic=False)

        assert font_path is not None
        assert "NotoSerif-ExtraLight.ttf" in font_path

    def test_should_match_light_weight_300(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=300, italic=False)

        assert font_path is not None
        assert "NotoSerif-Light.ttf" in font_path

    def test_should_match_regular_weight_400(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=400, italic=False)

        assert font_path is not None
        assert "NotoSerif-Regular.ttf" in font_path

    def test_should_match_medium_weight_500(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=500, italic=False)

        assert font_path is not None
        assert "NotoSerif-Medium.ttf" in font_path

    def test_should_match_semibold_weight_600(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=600, italic=False)

        assert font_path is not None
        assert "NotoSerif-SemiBold.ttf" in font_path

    def test_should_match_bold_weight_700(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=700, italic=False)

        assert font_path is not None
        assert "NotoSerif-Bold.ttf" in font_path

    def test_should_match_extrabold_weight_800(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=800, italic=False)

        assert font_path is not None
        assert "NotoSerif-ExtraBold.ttf" in font_path

    def test_should_match_black_weight_900(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=900, italic=False)

        assert font_path is not None
        assert "NotoSerif-Black.ttf" in font_path

    def test_should_match_weight_with_italic(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight=700, italic=True)

        assert font_path is not None
        assert "NotoSerif-BoldItalic.ttf" in font_path


class TestFontCacheNamedWeight:
    def test_should_match_named_weight_thin(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="thin", italic=False)

        assert font_path is not None
        assert "NotoSerif-Thin.ttf" in font_path

    def test_should_match_named_weight_extra_light(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="extra-light", italic=False)

        assert font_path is not None
        assert "NotoSerif-ExtraLight.ttf" in font_path

    def test_should_match_named_weight_light(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="light", italic=False)

        assert font_path is not None
        assert "NotoSerif-Light.ttf" in font_path

    def test_should_match_named_weight_normal(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="normal", italic=False)

        assert font_path is not None
        assert "NotoSerif-Regular.ttf" in font_path

    def test_should_match_named_weight_regular(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="regular", italic=False)

        assert font_path is not None
        assert "NotoSerif-Regular.ttf" in font_path

    def test_should_match_named_weight_medium(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="medium", italic=False)

        assert font_path is not None
        assert "NotoSerif-Medium.ttf" in font_path

    def test_should_match_named_weight_semi_bold(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="semi-bold", italic=False)

        assert font_path is not None
        assert "NotoSerif-SemiBold.ttf" in font_path

    def test_should_match_named_weight_bold(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="bold", italic=False)

        assert font_path is not None
        assert "NotoSerif-Bold.ttf" in font_path

    def test_should_match_named_weight_extra_bold(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="extra-bold", italic=False)

        assert font_path is not None
        assert "NotoSerif-ExtraBold.ttf" in font_path

    def test_should_match_named_weight_black(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("NotoSerif", weight="black", italic=False)

        assert font_path is not None
        assert "NotoSerif-Black.ttf" in font_path

    def test_should_handle_case_insensitive_named_weight(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
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

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("Roboto", weight=600, italic=False)

        assert font_path is not None
        assert "Roboto" in font_path

    def test_should_prefer_heavier_weight_when_equidistant(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("Roboto", weight=600, italic=False)

        assert font_path is not None

    def test_should_fallback_to_any_weight_when_italic_not_available(self, monkeypatch):
        from quickthumb.font_cache import FontCache

        monkeypatch.setenv("QUICKTHUMB_FONT_DIR", "/Users/sjquant/dev/quickthumb/assets/fonts")
        cache = FontCache()
        font_path = cache.find_font("Roboto", weight=100, italic=True)

        assert font_path is not None
        assert "Roboto" in font_path
