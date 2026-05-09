from __future__ import annotations
from flask import Blueprint, render_template
import base

energy_bp = Blueprint("narrative_energy", __name__)


@energy_bp.route("/energy")
def energy_home():
    # Top narratives by energy score
    high_energy = base.get_high_energy_articles(threshold=0.0, limit=50)

    # Group by energy range
    energy_bands = {"critical": [], "high": [], "moderate": [], "low": []}
    for art in high_energy:
        e = art.get("narrative_energy", 0) or 0
        if e >= 0.8:
            energy_bands["critical"].append(art)
        elif e >= 0.6:
            energy_bands["high"].append(art)
        elif e >= 0.4:
            energy_bands["moderate"].append(art)
        else:
            energy_bands["low"].append(art)

    # Game type distribution for context
    game_dist = base.get_game_type_distribution()

    return render_template("narrative_energy.html",
        high_energy=high_energy,
        energy_bands=energy_bands,
        game_dist=game_dist,
        total=len(high_energy),
    )
