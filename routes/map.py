from __future__ import annotations
from flask import Blueprint, render_template, request
import base

map_bp = Blueprint("map", __name__)

TIER_COLORS = {
    1: "#ff3333",
    2: "#ff8c00",
    3: "#ffd500",
    4: "#00e676",
    5: "#b388ff",
}

TIER_NAMES = {
    1: "The Prison",
    2: "Hidden History",
    3: "The Hidden Reality",
    4: "Control Systems",
    5: "The Exit/Upgrade",
}


@map_bp.route("/map")
def conspiracy_map():
    # Filter params
    actor_filter = request.args.get("actor")
    game_type_filter = request.args.get("game_type")
    after = request.args.get("after")
    energy = request.args.get("energy")  # 'high', 'medium', 'all'
    hide_articles = request.args.get("hide_articles") == "1"

    entries = base.list_entries(domain="conspiracy")

    # Article nodes from SQL
    energy_min = None
    if energy == "high":
        energy_min = 0.7
    elif energy == "medium":
        energy_min = 0.4

    articles = base.list_articles_sql(
        actor=actor_filter, game_type=game_type_filter,
        after=after, energy_min=energy_min, limit=500,
    )

    nodes = []
    node_set = set()
    for e in entries:
        slug = e["slug"]
        if slug.startswith("art-"):
            continue
        if slug not in node_set:
            nodes.append({
                "id": slug,
                "title": e["title"],
                "tier": e.get("tier", 0),
                "category": e.get("category", ""),
                "is_article": False,
            })
            node_set.add(slug)

    if not hide_articles:
        for a in articles:
            slug = a["slug"]
            if slug not in node_set:
                nodes.append({
                    "id": slug,
                    "title": a["title"],
                    "tier": 1,
                    "category": "News Article",
                    "is_article": True,
                    "game_type": a.get("game_type", ""),
                    "narrative_energy": a.get("narrative_energy", 0.5),
                })
                node_set.add(slug)

    # Build edges from triples
    edges = []
    seen_edges = set()
    for node in nodes:
        slug = node["id"]
        outgoing, incoming = base.get_triples_for(slug)
        for t in outgoing:
            edge_key = (t.subject, t.object, t.predicate)
            if edge_key not in seen_edges and t.object in node_set:
                edges.append({"source": t.subject, "target": t.object, "predicate": t.predicate})
                seen_edges.add(edge_key)
        for t in incoming:
            edge_key = (t.subject, t.object, t.predicate)
            if edge_key not in seen_edges and t.subject in node_set:
                edges.append({"source": t.subject, "target": t.object, "predicate": t.predicate})
                seen_edges.add(edge_key)

    # Add article-to-article edges via shared actors (from SQL)
    if not hide_articles and articles:
        actor_articles = {}
        for a in articles:
            for actor in a.get("actors", []):
                actor_articles.setdefault(actor, []).append(a["slug"])
        for actor, slugs in actor_articles.items():
            # Connect articles sharing an actor
            for i in range(len(slugs)):
                for j in range(i + 1, len(slugs)):
                    if slugs[i] in node_set and slugs[j] in node_set:
                        edge_key = (slugs[i], slugs[j], "shared_actor")
                        rev_key = (slugs[j], slugs[i], "shared_actor")
                        if edge_key not in seen_edges and rev_key not in seen_edges:
                            edges.append({"source": slugs[i], "target": slugs[j], "predicate": f"shared: {actor}"})
                            seen_edges.add(edge_key)

    graph_data = {"nodes": nodes, "edges": edges}

    # Filter options
    game_types = base.get_game_types_sql()
    actors = base.get_all_actors_sql()[:20]

    return render_template("map.html",
        graph_data=graph_data,
        total=len(nodes),
        tier_colors=TIER_COLORS,
        tier_names=TIER_NAMES,
        game_types=game_types,
        actors=actors,
        actor_filter=actor_filter,
        game_type_filter=game_type_filter,
        energy=energy,
        hide_articles=hide_articles,
    )
