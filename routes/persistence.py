from __future__ import annotations
from flask import Blueprint, render_template
import base

persistence_bp = Blueprint("persistence", __name__)


@persistence_bp.route("/persistence")
def persistence_home():
    # Expiring narratives (shortest half-life first)
    expiring = base.get_expiring_narratives(limit=30)

    # Most liquid narratives
    liquid = base.get_liquid_narratives(limit=20)

    return render_template("persistence.html",
        expiring=expiring,
        liquid=liquid,
        total_expiring=len(expiring),
        total_liquid=len(liquid),
    )
