from __future__ import annotations
from flask import Blueprint, redirect, url_for

day_after_bp = Blueprint("day_after", __name__)


@day_after_bp.route("/day-after-tomorrow")
def day_after_home():
    return redirect(url_for("paper.paper_home") + "?tab=day2")
