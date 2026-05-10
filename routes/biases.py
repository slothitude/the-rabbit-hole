from __future__ import annotations
from flask import Blueprint, render_template
import base

biases_bp = Blueprint("biases", __name__)

@biases_bp.route("/biases")
def biases_home():
    heatmap = base.get_bias_heatmap()
    articles = base.get_biased_articles(limit=30)
    return render_template("biases.html", heatmap=heatmap, articles=articles, total=len(articles))
