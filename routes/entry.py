from __future__ import annotations
from flask import Blueprint, render_template
import base
from markdown_render import render_markdown

entry_bp = Blueprint("entry", __name__)

TIER_NAMES = {
    1: "The Prison",
    2: "Hidden History",
    3: "The Hidden Reality",
    4: "Control Systems",
    5: "The Exit/Upgrade",
}


@entry_bp.route("/entry/<slug>")
def entry_page(slug):
    entry = base.get_entry(slug)
    if not entry:
        return render_template("404.html", slug=slug), 404
    html_body = render_markdown(entry.body)
    outgoing, incoming = base.get_triples_for(slug)
    tier_name = TIER_NAMES.get(entry.tier) if entry.tier else None
    return render_template("entry.html",
        entry=entry,
        html_body=html_body,
        outgoing=outgoing,
        incoming=incoming,
        tier_name=tier_name,
    )
