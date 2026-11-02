"""Describe documentation pages and their existing preview images for search and sharing."""

import json
import tomllib
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from PIL import Image

PROJECT = tomllib.loads((Path(__file__).parents[2] / "pyproject.toml").read_text())["project"]


def on_page_context(context, page, config, **kwargs):
    """Supply social images and a linked graph of the site, software, and document."""
    name = _page_name(page)
    brand = config.site_name
    context["seo_title"] = (
        name
        if name.casefold() == brand.casefold() or name.casefold().startswith(brand.casefold() + " ")
        else f"{brand} - {name}"
    )
    image = _social_image(page, config)
    context["social_image"] = image
    context["seo_json_ld"] = json.dumps(
        _structured_data(page, config, image), ensure_ascii=False
    ).replace("<", "\\u003c")
    return context


def _social_image(page, config):
    """Prefer authored previews, then recipe outputs, then the branded site image."""
    src = page.meta.get("image")
    alt = page.meta.get("image_alt", "")
    if not src and (
        page.file.src_uri.startswith("cookbook/") or page.file.src_uri == "getting-started.md"
    ):
        parser = _FirstImage()
        parser.feed(page.content)
        src, alt = parser.src, parser.alt

    if src:
        url = urljoin(page.canonical_url, src)
        alt = alt or _page_name(page)
    else:
        url = urljoin(config.site_url, config.extra["social_image_url"])
        alt = "quickthumb: Endless thumbnails, from code. Two example thumbnail cards."

    image = {"url": url, "alt": alt}
    site = urlsplit(config.site_url)
    asset = urlsplit(url)
    site_path = site.path.rstrip("/") + "/"
    if asset.netloc == site.netloc and asset.path.startswith(site_path):
        docs = Path(config.docs_dir).resolve()
        path = (docs / unquote(asset.path[len(site_path) :])).resolve()
        if path.is_relative_to(docs) and path.is_file():
            with Image.open(path) as local_image:
                image["width"], image["height"] = local_image.size
    elif page.meta.get("image_width") and page.meta.get("image_height"):
        image["width"] = page.meta["image_width"]
        image["height"] = page.meta["image_height"]
    return image


def _structured_data(page, config, image):
    """Link canonical pages to the documented Python package and its source repository."""
    site_url = config.site_url.rstrip("/") + "/"
    url = page.canonical_url
    author = {"@id": site_url + "#author"}
    software = {"@id": site_url + "#software"}
    website = {"@id": site_url + "#website"}
    preview = {"@type": "ImageObject", "url": image["url"], "caption": image["alt"]}
    for dimension in ("width", "height"):
        if dimension in image:
            preview[dimension] = image[dimension]

    graph = [
        {
            "@type": "WebSite",
            **website,
            "url": site_url,
            "name": config.site_name,
            "description": config.site_description,
            "inLanguage": "en",
            "publisher": author,
            "about": software,
        },
        {"@type": "Person", **author, "name": config.site_author},
        {
            "@type": "SoftwareApplication",
            **software,
            "name": PROJECT["name"],
            "url": site_url,
            "description": config.site_description,
            "applicationCategory": "MultimediaApplication",
            "softwareVersion": PROJECT["version"],
            "softwareRequirements": "Python " + PROJECT["requires-python"],
            "license": config.repo_url + "/blob/main/LICENSE",
            "author": author,
            "sameAs": [config.repo_url, "https://pypi.org/project/quickthumb/"],
        },
        {
            "@type": "SoftwareSourceCode",
            "@id": site_url + "#source",
            "name": PROJECT["name"],
            "codeRepository": config.repo_url,
            "programmingLanguage": "Python",
            "runtimePlatform": "Python " + PROJECT["requires-python"],
            "targetProduct": software,
            "author": author,
            "license": config.repo_url + "/blob/main/LICENSE",
        },
        {
            "@type": "CollectionPage" if page.is_index and not page.is_homepage else "WebPage",
            "@id": url + "#webpage",
            "url": url,
            "name": _page_name(page),
            "description": page.meta["description"],
            "inLanguage": "en",
            "isPartOf": website,
            "about": software,
            "primaryImageOfPage": preview,
            "mainEntity": software if page.is_homepage else {"@id": url + "#document"},
        },
    ]
    if not page.is_homepage:
        breadcrumbs = _breadcrumbs(page, site_url, config.site_name)
        graph[-1]["breadcrumb"] = {"@id": url + "#breadcrumbs"}
        graph.extend(
            [
                {
                    "@type": "BreadcrumbList",
                    "@id": url + "#breadcrumbs",
                    "itemListElement": [
                        {"@type": "ListItem", "position": index, "name": name, "item": item_url}
                        for index, (name, item_url) in enumerate(breadcrumbs, start=1)
                    ],
                },
                {
                    "@type": "TechArticle",
                    "@id": url + "#document",
                    "url": url,
                    "headline": _page_name(page),
                    "description": page.meta["description"],
                    "inLanguage": "en",
                    "mainEntityOfPage": {"@id": url + "#webpage"},
                    "isPartOf": website,
                    "about": software,
                    "author": author,
                },
            ]
        )
    return {"@context": "https://schema.org", "@graph": graph}


def _breadcrumbs(page, site_url, site_name):
    """Use existing navigation landing pages without inventing section URLs."""
    items = [(site_name, site_url)]
    for section in reversed(page.ancestors):
        landing = section.children[0]
        if (
            landing.is_page
            and landing != page
            and (landing.is_index or landing.file.src_uri == "changelog.md")
        ):
            items.append((section.title, landing.canonical_url))
    items.append((_page_name(page), page.canonical_url))
    return items


def _page_name(page):
    """Use the existing page title as plain text."""
    return unescape(page.meta.get("title") or page.title)


class _FirstImage(HTMLParser):
    """Read a recipe's first existing output image and its authored alternative text."""

    src = ""
    alt = ""

    def handle_starttag(self, tag, attrs):
        if tag == "img" and not self.src:
            attributes = dict(attrs)
            self.src = attributes.get("src", "")
            self.alt = attributes.get("alt", "")
