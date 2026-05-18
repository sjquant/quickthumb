from pathlib import Path

import pytest

pytest.importorskip("mkdocs")
mkdocs_build = pytest.importorskip("mkdocs.commands.build")
mkdocs_config = pytest.importorskip("mkdocs.config")


def test_docs_build_includes_search_engine_metadata(tmp_path):
    """Docs build exposes crawler and social metadata from the generated site."""
    # Given
    # A MkDocs documentation site built into a temporary output directory.
    project_root = Path(__file__).resolve().parents[1]
    config_file = project_root / "mkdocs.yml"
    site_dir = tmp_path / "site"
    social_preview = project_root / "assets" / "brand" / "social-preview.png"
    docs_social_preview = project_root / "docs" / "assets" / "brand" / "social-preview.png"
    docs_favicon = project_root / "docs" / "favicon.ico"

    # When
    # The documentation site is built with strict validation enabled.
    config = mkdocs_config.load_config(str(config_file), strict=True, site_dir=str(site_dir))
    mkdocs_build.build(config)

    # Then
    # The generated site exposes the SEO artifacts that crawlers and link unfurls read.
    index_html = (site_dir / "index.html").read_text(encoding="utf-8")
    enums_html = (site_dir / "api" / "enums" / "index.html").read_text(encoding="utf-8")
    assert (site_dir / "googleafa40cbb47cddae5.html").read_text(
        encoding="utf-8"
    ) == "google-site-verification: googleafa40cbb47cddae5.html\n"
    assert "Sitemap: https://sjquant.github.io/quickthumb/sitemap.xml" in (
        site_dir / "robots.txt"
    ).read_text(encoding="utf-8")
    assert '<meta property="og:title" content="quickthumb">' in index_html
    assert '<meta name="twitter:card" content="summary_large_image">' in index_html
    assert (
        '<meta property="og:image" '
        'content="https://sjquant.github.io/quickthumb/assets/brand/social-preview.png">'
        in index_html
    )
    assert (site_dir / "assets" / "brand" / "social-preview.png").read_bytes() == (
        social_preview.read_bytes()
    )
    assert docs_social_preview.read_bytes() == social_preview.read_bytes()
    assert (site_dir / "favicon.ico").read_bytes() == docs_favicon.read_bytes()
    assert '<meta property="og:title" content="Enums &amp; Gradients - quickthumb">' in enums_html
