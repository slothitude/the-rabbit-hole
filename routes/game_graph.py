from __future__ import annotations
from flask import Blueprint, render_template
import base

game_graph_bp = Blueprint("game_graph", __name__)

@game_graph_bp.route("/game-graph")
def game_graph_home():
    graph = base.get_game_graph()
    return render_template("game_graph.html",
        nodes=graph["nodes"], edges=graph["edges"],
        total_nodes=len(graph["nodes"]), total_edges=len(graph["edges"]))
