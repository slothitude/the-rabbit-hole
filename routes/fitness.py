from __future__ import annotations
from flask import Blueprint, render_template
import base

fitness_bp = Blueprint("fitness", __name__)

@fitness_bp.route("/fitness")
def fitness_home():
    strategies = base.get_narrative_fitness(limit=20)
    distribution = base.get_strategy_distribution()
    return render_template("fitness.html", strategies=strategies,
        distribution=distribution, total=len(strategies))
