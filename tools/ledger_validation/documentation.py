# SPDX-License-Identifier: AGPL-3.0-or-later
# Commercial license available
# © Concepts 1996–2026 Miroslav Šotek. All rights reserved.
# © Code 2020–2026 Miroslav Šotek. All rights reserved.
# ORCID: 0009-0009-3560-0851
# Contact: www.anulum.li | protoscience@anulum.li
# EXPERIMENT-LEDGER — repository identity and validation foundation

"""Check public Markdown links and the actual strict documentation projection."""

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import markdown

from .inputs import CheckFailure, read_bytes
from .processes import execute
from .provenance import maintained_sources


class Document(HTMLParser):
    """Collect rendered link targets, anchors and visible text without executing HTML.

    Attributes
    ----------
    links : list[str]
        Original rendered href and src values.
    anchors : set[str]
        Rendered element identities available to local fragments.
    text : list[str]
        Text nodes; HTML comments are deliberately absent.
    """

    def __init__(self, html: str) -> None:
        """Parse one complete rendered document.

        Parameters
        ----------
        html : str
            Actual rendered Unicode HTML.
        """
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.anchors: set[str] = set()
        self.text: list[str] = []
        self.feed(html)
        self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Retain actual link and fragment attributes.

        Parameters
        ----------
        tag : str
            HTML element name.
        attrs : list[tuple[str, str or None]]
            Original parsed attribute names and optional values.
        """
        for key, value in attrs:
            if value is not None:
                if key in ("href", "src"):
                    self.links.append(value)
                if key == "id":
                    self.anchors.add(value)

    def handle_data(self, data: str) -> None:
        """Retain visible text nodes for public projection checks.

        Parameters
        ----------
        data : str
            Decoded HTML text node.
        """
        self.text.append(data)


def _markdown(root: Path, name: str) -> Document:
    try:
        text = read_bytes(root, name, 1048576).decode("utf-8")
    except UnicodeError as error:
        raise CheckFailure("documentation_text_invalid", name) from error
    return Document(
        markdown.markdown(text, extensions=["toc", "tables", "fenced_code", "attr_list"])
    )


def _projection(document: Document, name: str) -> None:
    text = " ".join(document.text)
    if re.search(
        "SPDX-" + r"License-Identifier:|\.coordination/|docs/internal/|"
        r"\b(?:Codex|OpenAI|ChatGPT|Claude|Gemini|Grok|Kimi)\b",
        text,
        re.IGNORECASE,
    ):
        raise CheckFailure("documentation_private_projection", name)
    for link in document.links:
        if (
            "doi.org/" in link
            or "/badge.svg" in link
            or "img.shields.io" in link
            and not link.startswith(
                (
                    "https://img.shields.io/badge/Buy%20Me%20a%20Coffee-",
                    "https://img.shields.io/badge/GitHub%20Sponsors-",
                )
            )
        ):
            raise CheckFailure("documentation_unearned_service", name)
    if re.search(
        r"\bpip\s+install\s+(?:experiment[-_]ledger)\b|\bfrom experiment_ledger import\b", text
    ):
        raise CheckFailure("documentation_unavailable_api", name)


def verify(root: Path) -> None:
    """Validate real local links and build the complete maintained documentation.

    Parameters
    ----------
    root : Path
        Repository supplying public Markdown, assets and MkDocs configuration.

    Raises
    ------
    CheckFailure
        For missing, oversized or invalid documents, broken local targets or
        fragments, private or unearned public content, renderer unavailability
        or failure, escaped output paths or private rendered pages.

    Notes
    -----
    External links are classified without network requests. Strict MkDocs
    renders the actual configured Python API and validates its own link graph.
    Generated HTML is inspected in an ignored repository-local cache. No
    documentation is published and no domain API or release is qualified.
    """
    root = root.resolve()
    names = maintained_sources(root)
    documents = {name: _markdown(root, name) for name in names if name.endswith(".md")}
    for name, document in documents.items():
        _projection(document, name)
        for link in document.links:
            try:
                parsed = urlsplit(link)
            except ValueError as error:
                raise CheckFailure("documentation_link_invalid", name) from error
            if parsed.scheme or parsed.netloc:
                continue
            target = (root / name).parent / unquote(parsed.path) if parsed.path else root / name
            target = target.resolve()
            if not target.is_relative_to(root) or not target.is_file():
                raise CheckFailure("documentation_link_missing", name)
            relative = target.relative_to(root).as_posix()
            if relative.startswith("docs/internal/") or relative not in names:
                raise CheckFailure("documentation_link_private", name)
            if parsed.fragment:
                destination = documents.get(relative)
                if destination is None or unquote(parsed.fragment) not in destination.anchors:
                    raise CheckFailure("documentation_anchor_missing", name)
    output = root / ".tool-cache/documentation"
    if not output.resolve().is_relative_to(root):
        raise CheckFailure("documentation_output_escape", ".tool-cache/documentation")
    process = execute(
        [sys.executable, "-m", "mkdocs", "build", "--strict", "--site-dir", str(output)],
        root=root,
        location="mkdocs.yml",
    )
    if process.returncode:
        raise CheckFailure("documentation_renderer_failed", "mkdocs.yml")
    pages = tuple(output.rglob("*.html"))
    if not (output / "index.html").is_file():
        raise CheckFailure("documentation_render_missing", "mkdocs.yml", unavailable=True)
    for page in pages:
        relative = page.relative_to(output).as_posix()
        if "internal" in page.relative_to(output).parts:
            raise CheckFailure("documentation_render_private", "mkdocs.yml")
        _projection(Document(page.read_text(encoding="utf-8")), "rendered/" + relative)
