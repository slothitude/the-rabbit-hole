from __future__ import annotations
from flask import Blueprint, render_template
import base

cascades_bp = Blueprint("cascades", __name__)

@cascades_bp.route("/cascades")
def cascades_home():
    cascades = base.get_cascade_articles(limit=30)
    return render_template("cascades.html", cascades=cascades, total=len(cascades))
