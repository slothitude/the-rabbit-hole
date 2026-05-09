from __future__ import annotations
from flask import Blueprint, redirect, url_for

tomorrow_bp = Blueprint("tomorrow", __name__)


@tomorrow_bp.route("/tomorrow")
def tomorrow_home():
    return redirect(url_for("paper.paper_home") + "?tab=tomorrow")
