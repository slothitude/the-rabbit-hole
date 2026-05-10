from __future__ import annotations
from flask import Blueprint, render_template
import base

beliefs_bp = Blueprint("beliefs", __name__)

@beliefs_bp.route("/beliefs")
def beliefs_home():
    beliefs = base.get_belief_updates(limit=50)
    return render_template("beliefs.html", beliefs=beliefs, total=len(beliefs))
