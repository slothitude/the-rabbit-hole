from __future__ import annotations
from flask import Blueprint, render_template, request
import base

search_bp = Blueprint("search", __name__)


@search_bp.route("/search")
def search_page():
    q = request.args.get("q", "")
    results = base.search(q) if q else []
    return render_template("search_results.html", query=q, results=results)
