from __future__ import annotations
from flask import Blueprint, render_template, abort
import base

actors_bp = Blueprint("actors", __name__)


@actors_bp.route("/actors")
def actors_home():
    all_actors = base.get_all_actors_sql()
    return render_template("actors.html", actors=all_actors, total=len(all_actors))


@actors_bp.route("/actors/<path:name>")
def actor_profile(name):
    articles = base.get_actor_articles_sql(name, limit=100)
    if not articles:
        abort(404)

    # Build actor stats
    game_types = {}
    controlled_count = 0
    arc_counts = {}
    for art in articles:
        gt = art.get("game_type", "")
        if gt:
            game_types[gt] = game_types.get(gt, 0) + 1
        if art.get("controlled_narrative"):
            controlled_count += 1
        arc = art.get("narrative_arc", "")
        if arc:
            arc_counts[arc] = arc_counts.get(arc, 0) + 1

    # Find co-actors (other actors in same articles)
    co_actors = {}
    for art in articles:
        for actor in art.get("actors", []):
            if actor.lower() != name.lower():
                co_actors[actor] = co_actors.get(actor, 0) + 1
    co_actors = sorted(co_actors.items(), key=lambda x: -x[1])[:10]

    credibility = round(1.0 - (controlled_count / max(len(articles), 1)), 2)

    return render_template("actor_profile.html",
        name=name,
        articles=articles,
        total=len(articles),
        game_types=game_types,
        controlled_count=controlled_count,
        arc_counts=arc_counts,
        co_actors=co_actors,
        credibility=credibility,
    )
