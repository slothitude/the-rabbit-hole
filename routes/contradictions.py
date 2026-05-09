from __future__ import annotations
from flask import Blueprint, render_template
import base

contradictions_bp = Blueprint("contradictions", __name__)


@contradictions_bp.route("/contradictions")
def contradictions_home():
    rows = base.get_contradictions_sql()

    # Build contradiction pairs from SQL results
    pairs = []
    for r in rows:
        pairs.append({
            "article_slug": r["slug"],
            "article_title": r["title"],
            "article_date": r.get("created", ""),
            "claim_now": r.get("claim_now", ""),
            "claim_then": r.get("claim_then", ""),
            "significance": r.get("significance", "medium"),
            "explanation": r.get("explanation", ""),
            "source_slug": r.get("source_slug", ""),
        })

    # Sort by significance
    sig_order = {"high": 0, "medium": 1, "low": 2}
    pairs.sort(key=lambda p: sig_order.get(p["significance"], 1))

    return render_template("contradictions.html",
        pairs=pairs,
        total=len(pairs),
    )
