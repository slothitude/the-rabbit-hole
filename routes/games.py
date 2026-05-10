from __future__ import annotations
from flask import Blueprint, render_template
import base

games_bp = Blueprint("games", __name__)

@games_bp.route("/games")
def games_home():
    games = base.get_active_games(limit=20)
    return render_template("games.html", games=games, total=len(games))
