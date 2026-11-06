"""Authoring contracts for the documentation metadata hook."""

import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
ON_PAGE_CONTEXT = runpy.run_path(str(ROOT / "docs/hooks/seo.py"))["on_page_context"]


@pytest.fixture
def authoring_page():
    """Provide a new documentation page outside the existing navigation."""
    return SimpleNamespace(
        meta={},
        title="New page",
        canonical_url="https://docs.example.test/new-page/",
        file=SimpleNamespace(src_uri="new-page.md"),
        is_homepage=False,
        is_index=False,
        ancestors=[],
    )


@pytest.fixture
def site_config():
    """Provide site defaults and the repository's actual documentation assets."""
    return SimpleNamespace(
        site_name="quickthumb",
        site_url="https://docs.example.test/",
        site_description="Site fallback description.",
        site_author="Seonu Jang",
        repo_url="https://github.com/sjquant/quickthumb",
        docs_dir=str(ROOT / "docs"),
        extra={"social_image_url": "https://docs.example.test/assets/brand/social-preview.png"},
    )


@pytest.mark.parametrize("metadata", [{}, {"description": ""}])
def test_page_without_description_uses_site_default(authoring_page, site_config, metadata):
    """A page without a nonempty description uses the site default in both graph entities."""
    # Given: an ordinary new page with no custom description
    authoring_page.meta = metadata

    # When: MkDocs requests its metadata context
    context = ON_PAGE_CONTEXT({}, authoring_page, site_config)
    nodes = {node["@id"]: node for node in json.loads(context["seo_json_ld"])["@graph"]}

    # Then: the page and its document share the existing site-description fallback
    assert nodes[authoring_page.canonical_url + "#webpage"]["description"] == (
        site_config.site_description
    )
    assert nodes[authoring_page.canonical_url + "#document"]["description"] == (
        site_config.site_description
    )


@pytest.mark.parametrize(
    ("metadata", "dimensions"),
    [
        ({}, {}),
        ({"image_width": 192, "image_height": 192}, {"width": 192, "height": 192}),
    ],
)
def test_svg_override_preserves_authored_image(authoring_page, site_config, metadata, dimensions):
    """The existing SVG icon remains selected with explicit dimensions or no guessed dimensions."""
    # Given: a manual override pointing to the repository's existing SVG icon
    authoring_page.meta = {
        "image": "/assets/brand/quickthumb-icon.svg",
        "image_alt": "Selected quickthumb icon",
        **metadata,
    }
    url = "https://docs.example.test/assets/brand/quickthumb-icon.svg"

    # When: MkDocs requests its social image and structured metadata
    context = ON_PAGE_CONTEXT({}, authoring_page, site_config)
    nodes = {node["@id"]: node for node in json.loads(context["seo_json_ld"])["@graph"]}

    # Then: the manual URL and alt survive without requiring a raster decoder
    assert context["social_image"] == {
        "url": url,
        "alt": "Selected quickthumb icon",
        **dimensions,
    }
    assert nodes[authoring_page.canonical_url + "#webpage"]["primaryImageOfPage"] == {
        "@type": "ImageObject",
        "url": url,
        "caption": "Selected quickthumb icon",
        **dimensions,
    }


@pytest.mark.parametrize(
    ("locale", "language", "title", "alt"),
    [
        ("ko", "ko", "팟캐스트 홍보", "팟캐스트 인터뷰 홍보 이미지"),
        ("ja", "ja", "ポッドキャストの宣伝", "ポッドキャストのインタビュー告知画像"),
        ("zh", "zh-CN", "播客宣传图", "播客访谈宣传图"),
    ],
)
def test_localized_recipe_uses_shared_image_and_locale_graph(
    authoring_page, site_config, locale, language, title, alt
):
    """A translated recipe keeps its localized identity and measures the shared preview asset."""
    # Given: a translated recipe with a relative preview and a localized image description
    authoring_page.file = SimpleNamespace(
        src_uri=f"cookbook/podcast-promo.{locale}.md",
        norm_src_uri="cookbook/podcast-promo.md",
        locale=locale,
        locale_alternate_of=locale,
    )
    authoring_page.title = title
    authoring_page.canonical_url = f"https://docs.example.test/{locale}/cookbook/podcast-promo/"
    authoring_page.content = (
        f'<p><img src="../../../assets/examples/podcast_interview_promo.png" alt="{alt}"></p>'
    )

    # When: the localized page's public metadata hook runs
    context = ON_PAGE_CONTEXT({}, authoring_page, site_config)
    nodes = {node["@id"]: node for node in json.loads(context["seo_json_ld"])["@graph"]}

    # Then: the preview keeps its actual dimensions and the graph shares the product identity
    assert context["social_image"] == {
        "url": "https://docs.example.test/assets/examples/podcast_interview_promo.png",
        "alt": alt,
        "width": 1280,
        "height": 720,
    }
    webpage = nodes[authoring_page.canonical_url + "#webpage"]
    assert webpage["inLanguage"] == language
    assert webpage["isPartOf"] == {"@id": f"https://docs.example.test/{locale}/#website"}
    assert webpage["about"] == {"@id": "https://docs.example.test/#software"}
    assert nodes[authoring_page.canonical_url + "#document"]["inLanguage"] == language
    assert nodes[authoring_page.canonical_url + "#breadcrumbs"]["itemListElement"][0]["item"] == (
        f"https://docs.example.test/{locale}/"
    )
    assert context["seo_title"] == f"quickthumb - {title}"


@pytest.mark.parametrize("locale", ["ko", "ja", "zh"])
def test_untranslated_page_fails_the_localized_build(authoring_page, site_config, locale):
    """Missing translations fail localized builds rather than publishing English duplicates."""
    # Given: the plugin selected an English source for a localized build
    authoring_page.file.locale = "en"
    authoring_page.file.locale_alternate_of = locale

    # When / Then: the build rejects the missing translation before rendering its page
    with pytest.raises(ValueError, match="Missing translation: new-page.md"):
        ON_PAGE_CONTEXT({}, authoring_page, site_config)
