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
