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


def test_korean_recipe_uses_shared_image_and_locale_graph(authoring_page, site_config):
    """A Korean recipe keeps its localized page identity and measures the shared preview asset."""
    # Given: a translated recipe with a relative preview and a Korean image description
    authoring_page.file = SimpleNamespace(
        src_uri="cookbook/podcast-promo.ko.md",
        norm_src_uri="cookbook/podcast-promo.md",
        locale="ko",
        locale_alternate_of="ko",
    )
    authoring_page.title = "팟캐스트 홍보"
    authoring_page.canonical_url = "https://docs.example.test/ko/cookbook/podcast-promo/"
    authoring_page.content = (
        '<p><img src="../../../assets/examples/podcast_interview_promo.png" '
        'alt="팟캐스트 인터뷰 홍보 이미지"></p>'
    )

    # When: the localized page's public metadata hook runs
    context = ON_PAGE_CONTEXT({}, authoring_page, site_config)
    nodes = {node["@id"]: node for node in json.loads(context["seo_json_ld"])["@graph"]}

    # Then: the preview keeps its actual dimensions and the graph shares the product identity
    assert context["social_image"] == {
        "url": "https://docs.example.test/assets/examples/podcast_interview_promo.png",
        "alt": "팟캐스트 인터뷰 홍보 이미지",
        "width": 1280,
        "height": 720,
    }
    webpage = nodes[authoring_page.canonical_url + "#webpage"]
    assert webpage["inLanguage"] == "ko"
    assert webpage["isPartOf"] == {"@id": "https://docs.example.test/ko/#website"}
    assert webpage["about"] == {"@id": "https://docs.example.test/#software"}
    assert nodes[authoring_page.canonical_url + "#document"]["inLanguage"] == "ko"
    assert nodes[authoring_page.canonical_url + "#breadcrumbs"]["itemListElement"][0]["item"] == (
        "https://docs.example.test/ko/"
    )
    assert context["seo_title"] == "quickthumb - 팟캐스트 홍보"


def test_untranslated_page_fails_the_localized_build(authoring_page, site_config):
    """A missing Korean translation fails the build instead of publishing an English duplicate."""
    # Given: the plugin selected an English source for the Korean build
    authoring_page.file.locale = "en"
    authoring_page.file.locale_alternate_of = "ko"

    # When / Then: the build rejects the missing translation before rendering its page
    with pytest.raises(ValueError, match="Missing translation: new-page.md"):
        ON_PAGE_CONTEXT({}, authoring_page, site_config)
