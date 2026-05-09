from __future__ import annotations
from flask import Blueprint, redirect, url_for

today_bp = Blueprint("today", __name__)


@today_bp.route("/today")
def today_home():
    return redirect(url_for("paper.paper_home") + "?tab=today")
