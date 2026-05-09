from __future__ import annotations
from flask import Blueprint, render_template
import base

category_bp = Blueprint("category", __name__)


@category_bp.route("/category/<slug>")
def category_page(slug):
    entries = base.list_entries(domain="conspiracy")
    category_entries = [e for e in entries if e.get("category", "").lower().replace(" ", "-").replace("&", "and") == slug]
    category_name = slug.replace("-", " ").replace(" and ", " & ").title()
    if category_entries:
        category_name = category_entries[0].get("category", category_name)
    return render_template("category.html",
        category=category_name,
        category_slug=slug,
        entries=category_entries,
    )
