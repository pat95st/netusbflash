"""Allow-list HTML sanitiser for email templates written in the web editor.

Keeps the formatting the editor produces (paragraphs, headings, lists, links,
bold/italic/underline, colours, alignment) and drops everything else:
scripts, event handlers, external resources and unknown tags. Quill's layout
classes are turned into inline styles, because mail clients do not have the
editor's CSS.
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "u", "s", "a", "ul", "ol", "li",
    "h1", "h2", "h3", "h4", "blockquote", "pre", "code", "span", "div",
    "hr", "sub", "sup", "table", "thead", "tbody", "tr", "th", "td",
}
VOID_TAGS = {"br", "hr"}
DROP_CONTENT = {"script", "style", "iframe", "object", "embed", "noscript", "template", "svg", "math", "head", "title"}
ALLOWED_STYLES = {
    "color", "background-color", "text-align", "font-weight", "font-style",
    "text-decoration", "padding-left", "margin-left",
}
SAFE_URL = re.compile(r"^(https?:|mailto:|\{\{)", re.IGNORECASE)
STYLE_VALUE = re.compile(r"^[#a-zA-Z0-9 .,%()\-]+$")
QUILL_CLASS_STYLES = {
    "ql-align-center": "text-align: center",
    "ql-align-right": "text-align: right",
    "ql-align-justify": "text-align: justify",
}


def _clean_style(value: str) -> str:
    kept = []
    for part in value.split(";"):
        if ":" not in part:
            continue
        name, val = (x.strip() for x in part.split(":", 1))
        if name.lower() in ALLOWED_STYLES and STYLE_VALUE.match(val) and "url" not in val.lower():
            kept.append(f"{name.lower()}: {val}")
    return "; ".join(kept)


class _Sanitiser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.stack: list[str] = []
        self.drop_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in DROP_CONTENT:
            self.drop_depth += 1
            return
        if self.drop_depth or tag not in ALLOWED_TAGS:
            return
        styles = []
        kept_attrs = []
        for name, value in attrs:
            name = name.lower()
            value = value or ""
            if name == "href" and tag == "a" and SAFE_URL.match(value.strip()):
                kept_attrs.append(f'href="{html.escape(value.strip(), quote=True)}"')
            elif name == "style":
                cleaned = _clean_style(value)
                if cleaned:
                    styles.append(cleaned)
            elif name == "class":
                for cls in value.split():
                    if cls in QUILL_CLASS_STYLES:
                        styles.append(QUILL_CLASS_STYLES[cls])
                    elif cls.startswith("ql-indent-") and cls[10:].isdigit():
                        styles.append(f"padding-left: {3 * int(cls[10:])}em")
            elif name in ("colspan", "rowspan") and value.isdigit():
                kept_attrs.append(f'{name}="{value}"')
        if styles:
            kept_attrs.append(f'style="{html.escape("; ".join(styles), quote=True)}"')
        if tag == "a":
            kept_attrs.append('rel="noopener"')
        attr_text = (" " + " ".join(kept_attrs)) if kept_attrs else ""
        self.out.append(f"<{tag}{attr_text}>")
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID_TAGS and self.stack and self.stack[-1] == tag.lower():
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in DROP_CONTENT:
            self.drop_depth = max(0, self.drop_depth - 1)
            return
        if self.drop_depth or tag not in ALLOWED_TAGS or tag in VOID_TAGS:
            return
        if tag in self.stack:
            while self.stack:
                open_tag = self.stack.pop()
                self.out.append(f"</{open_tag}>")
                if open_tag == tag:
                    break

    def handle_data(self, data: str) -> None:
        if not self.drop_depth:
            self.out.append(html.escape(data, quote=False))

    def result(self) -> str:
        while self.stack:
            self.out.append(f"</{self.stack.pop()}>")
        return "".join(self.out)


def sanitise(fragment: str) -> str:
    parser = _Sanitiser()
    parser.feed(fragment or "")
    parser.close()
    return parser.result()


_BLOCK_END = re.compile(r"</(p|div|h[1-6]|li|tr|blockquote|pre)>", re.IGNORECASE)


def to_text(fragment: str) -> str:
    """Plain-text version of an HTML fragment for the text/plain mail part."""
    text = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "• ", text, flags=re.IGNORECASE)
    text = re.sub(r"<a [^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", r"\2 (\1)", text, flags=re.IGNORECASE | re.DOTALL)
    text = _BLOCK_END.sub("\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()
