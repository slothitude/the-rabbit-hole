"""Markdown -> HTML with [[wikilink]] resolution."""
from __future__ import annotations
import os
import re
import markdown
import config


def _entry_exists(slug: str) -> bool:
    return os.path.isfile(os.path.join(config.ENTRIES_DIR, f"{slug}.md"))


def _resolve_wikilinks(text: str, prefix: str = "") -> str:
    def replace_link(match):
        slug = match.group(1).strip().lower().replace(" ", "-")
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        display = match.group(1).strip()
        if _entry_exists(slug):
            return f'<a href="{prefix}/entry/{slug}" class="wikilink">{display}</a>'
        else:
            return f'<a href="{prefix}/entry/{slug}" class="wikilink wikilink-broken">{display}</a>'
    return re.sub(r"\[\[([^\]]+)\]\]", replace_link, text)


def render_markdown(text: str, prefix: str = "") -> str:
    text = _resolve_wikilinks(text, prefix)
    md = markdown.Markdown(extensions=["fenced_code", "tables", "smarty"])
    return md.convert(text)
