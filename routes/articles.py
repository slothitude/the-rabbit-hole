from __future__ import annotations
from flask import Blueprint, render_template, request
import base

articles_bp = Blueprint("articles", __name__)


@articles_bp.route("/articles")
def articles_home():
    actor = request.args.get("actor")
    game_type = request.args.get("game_type")
    narrative_arc = request.args.get("arc")
    page = request.args.get("page", 1, type=int)
    per_page = 50

    # Use SQL-powered queries
    total = base.count_articles_sql(actor=actor, game_type=game_type, arc=narrative_arc)
    articles = base.list_articles_sql(
        actor=actor, game_type=game_type, arc=narrative_arc,
        limit=per_page, offset=(page - 1) * per_page,
    )

    # Collect filter options from SQL
    game_types = base.get_game_types_sql()
    arcs = base.get_arcs_sql()
    actors = base.get_all_actors_sql()[:20]

    return render_template("articles.html",
        articles=articles,
        total=total,
        page=page,
        per_page=per_page,
        actor=actor,
        game_type=game_type,
        narrative_arc=narrative_arc,
        game_types=game_types,
        arcs=arcs,
        actors=actors,
    )
