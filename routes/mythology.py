from __future__ import annotations
from flask import Blueprint, render_template
import base

mythology_bp = Blueprint("mythology", __name__)


@mythology_bp.route("/mythology")
def mythology_home():
    rows = base.get_mythology_signals_sql()

    # Group by archetype
    myth_groups = {}
    for r in rows:
        archetype = r.get("archetype", "Unknown") or "Unknown"
        myth_groups.setdefault(archetype, []).append(r)

    return render_template("mythology.html",
        myth_groups=myth_groups,
        total=len(rows),
    )
