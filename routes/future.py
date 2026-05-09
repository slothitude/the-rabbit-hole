from __future__ import annotations
from flask import Blueprint, redirect, url_for

future_bp = Blueprint("future", __name__)


@future_bp.route("/future")
def future_home():
    return redirect(url_for("paper.paper_home") + "?tab=future")
