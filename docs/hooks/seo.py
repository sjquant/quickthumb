"""Describe documentation pages and their existing preview images for search and sharing."""

import json
import re
import tomllib
from datetime import date
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from PIL import Image, UnidentifiedImageError

PROJECT = tomllib.loads((Path(__file__).parents[2] / "pyproject.toml").read_text())["project"]


def on_page_context(context, page, config, **kwargs):
    """Supply social images and a linked graph of the site, software, and document."""
    if getattr(page.file, "locale", "en") != getattr(page.file, "locale_alternate_of", "en"):
        raise ValueError(f"Missing translation: {page.file.src_uri}")
    context["copyright_year"] = date.today().year
    name = _page_name(page)
    if "i18n_config" in context:
        config.extra["alternate"] = [
            {
                "name": language.name,
                "lang": "zh-CN" if language.locale == "zh" else language.locale,
                "link": urljoin(config.site_url, page.file.alternates[language.locale].url),
            }
            for language in context["i18n_config"].languages
            if language.locale in page.file.alternates
        ]
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
    source = getattr(page.file, "norm_src_uri", page.file.src_uri)
    if not src and (source.startswith("cookbook/") or source == "getting-started.md"):
        parser = _FirstImage()
        parser.feed(page.content)
        src, alt = parser.src, parser.alt

    if src:
        url = urljoin(page.canonical_url, src)
        alt = alt or _page_name(page)
    else:
        url = urljoin(config.site_url, config.extra["social_image_url"])
        alt = config.extra.get(
            "social_image_alt",
            "quickthumb: Endless thumbnails, from code. Two example thumbnail cards.",
        )

    image = {"url": url, "alt": alt}
    if page.meta.get("image_width") and page.meta.get("image_height"):
        image["width"] = page.meta["image_width"]
        image["height"] = page.meta["image_height"]
        return image

    site = urlsplit(config.site_url)
    asset = urlsplit(url)
    site_path = site.path.rstrip("/") + "/"
    if asset.netloc == site.netloc and asset.path.startswith(site_path):
        docs = Path(config.docs_dir).resolve()
        path = (docs / unquote(asset.path[len(site_path) :])).resolve()
        if path.is_relative_to(docs) and path.is_file():
            try:
                with Image.open(path) as local_image:
                    image["width"], image["height"] = local_image.size
            except UnidentifiedImageError:
                pass  # Keep unsupported overrides, such as SVG, without inferred dimensions.
    return image


def _structured_data(page, config, image):
    """Link canonical pages to the documented Python package and its source repository."""
    site_url = config.site_url.rstrip("/") + "/"
    locale = getattr(page.file, "locale_alternate_of", "en")
    language = "zh-CN" if locale == "zh" else locale
    locale_url = urljoin(site_url, locale + "/") if locale != "en" else site_url
    source = getattr(page.file, "norm_src_uri", page.file.src_uri)
    is_homepage = source == "index.md"
    url = page.canonical_url
    description = page.meta.get("description") or config.site_description
    author = {"@id": site_url + "#author"}
    software = {"@id": site_url + "#software"}
    website = {"@id": locale_url + "#website"}
    preview = {"@type": "ImageObject", "url": image["url"], "caption": image["alt"]}
    for dimension in ("width", "height"):
        if dimension in image:
            preview[dimension] = image[dimension]

    graph = [
        {
            "@type": "WebSite",
            **website,
            "url": locale_url,
            "name": config.site_name,
            "description": config.site_description,
            "inLanguage": language,
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
            "@type": "CollectionPage" if page.is_index and not is_homepage else "WebPage",
            "@id": url + "#webpage",
            "url": url,
            "name": _page_name(page),
            "description": description,
            "inLanguage": language,
            "isPartOf": website,
            "about": software,
            "primaryImageOfPage": preview,
            "mainEntity": software if is_homepage else {"@id": url + "#document"},
        },
    ]
    if not is_homepage:
        webpage = graph[-1]
        breadcrumbs = _breadcrumbs(page, locale_url, config.site_name)
        webpage["breadcrumb"] = {"@id": url + "#breadcrumbs"}
        graph.append(
            {
                "@type": "BreadcrumbList",
                "@id": url + "#breadcrumbs",
                "itemListElement": [
                    {"@type": "ListItem", "position": index, "name": name, "item": item_url}
                    for index, (name, item_url) in enumerate(breadcrumbs, start=1)
                ],
            }
        )
        if source == "faq.md":
            webpage["@type"] = "FAQPage"
            webpage["mainEntity"] = []
            for anchor, name, content in _rendered_sections(page, 3):
                question_id = url + "#" + anchor
                webpage["mainEntity"].append({"@id": question_id})
                graph.append(
                    {
                        "@type": "Question",
                        "@id": question_id,
                        "url": question_id,
                        "name": name,
                        "acceptedAnswer": {
                            "@type": "Answer",
                            "@id": question_id + "-answer",
                            "text": content,
                        },
                    }
                )
        else:
            is_howto = source == "getting-started.md"
            document = {
                "@type": "HowTo" if is_howto else "TechArticle",
                "@id": url + "#document",
                "url": url,
                "name" if is_howto else "headline": _page_name(page),
                "description": description,
                "inLanguage": language,
                "mainEntityOfPage": {"@id": url + "#webpage"},
                "isPartOf": website,
                "about": software,
                "author": author,
            }
            if is_howto:
                document["step"] = [
                    {
                        "@type": "HowToStep",
                        "@id": url + "#" + anchor,
                        "url": url + "#" + anchor,
                        "name": name,
                        "text": content,
                    }
                    for anchor, name, content in _rendered_sections(page, 2)[:3]
                ]
            graph.append(document)
    return {"@context": "https://schema.org", "@graph": graph}


def _rendered_sections(page, level):
    """Keep each existing question or numbered step with its complete rendered content."""
    # These two documents use MkDocs' standard headings; code examples are already escaped.
    headings = list(re.finditer(r'<h([1-6]) id="([^"]+)">(.*?)</h\1>', page.content, re.DOTALL))
    sections = []
    for index, heading in enumerate(headings):
        if int(heading[1]) != level:
            continue
        end = next(
            (item.start() for item in headings[index + 1 :] if int(item[1]) <= level),
            len(page.content),
        )
        name = unescape(re.sub(r"<[^>]+>", "", heading[3]))
        content = _absolute_links(page.content[heading.end() : end].strip(), page.canonical_url)
        sections.append((heading[2], name, content))
    return sections


def _absolute_links(content, url):
    """Keep rendered links usable within structured answers and instructions."""
    return re.sub(
        r'href="([^"]*)"',
        lambda match: 'href="' + escape(urljoin(url, unescape(match[1])), quote=True) + '"',
        content,
    )


def _breadcrumbs(page, site_url, site_name):
    """Use existing navigation landing pages without inventing section URLs."""
    items = [(site_name, site_url)]
    for section in reversed(page.ancestors):
        landing = section.children[0]
        if (
            landing.is_page
            and landing != page
            and (
                landing.is_index
                or getattr(landing.file, "norm_src_uri", landing.file.src_uri) == "changelog.md"
            )
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
