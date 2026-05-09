from __future__ import annotations
from flask import Blueprint, render_template
import base

reflexivity_bp = Blueprint("reflexivity", __name__)


@reflexivity_bp.route("/reflexivity")
def reflexivity_home():
    # Articles with highest reflexivity risk
    db = base._get_articles_db()
    try:
        rows = db.execute("""
            SELECT slug, title, reflexivity_risk, narrative_energy, game_type,
                   regime_response, equilibrium_shift, created
            FROM articles
            WHERE reflexivity_risk > 0
            ORDER BY reflexivity_risk DESC
            LIMIT 30
        """).fetchall()
        high_reflexivity = [dict(r) for r in rows]
    finally:
        db.close()

    # Stats
    total_articles = base.count_articles_sql()
    total_with_risk = len(high_reflexivity)

    return render_template("reflexivity.html",
        high_reflexivity=high_reflexivity,
        total_articles=total_articles,
        total_with_risk=total_with_risk,
    )
