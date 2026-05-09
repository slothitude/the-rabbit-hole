from __future__ import annotations
from flask import Blueprint, render_template, request
import base

timeline_bp = Blueprint("timeline", __name__)


@timeline_bp.route("/timeline")
def timeline_home():
    actor = request.args.get("actor")
    game_type = request.args.get("game_type")
    narrative_arc = request.args.get("arc")

    articles = base.list_articles_sql(actor=actor, game_type=game_type, arc=narrative_arc, limit=500)

    # Build timeline buckets by date
    buckets = {}
    for art in articles:
        created = art.get("created", "")
        if created:
            date_key = created[:10]
        else:
            date_key = "unknown"
        buckets.setdefault(date_key, []).append(art)

    # Sort buckets chronologically (newest first)
    sorted_buckets = sorted(buckets.items(), reverse=True)

    # Collect filter options
    game_types = base.get_game_types_sql()
    arcs = base.get_arcs_sql()
    actors = base.get_all_actors_sql()[:20]

    return render_template("timeline.html",
        buckets=sorted_buckets,
        total=len(articles),
        actor=actor,
        game_type=game_type,
        narrative_arc=narrative_arc,
        game_types=game_types,
        arcs=arcs,
        actors=actors,
    )
