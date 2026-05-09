from __future__ import annotations
from flask import Blueprint, render_template
import base

forecast_bp = Blueprint("forecast", __name__)


@forecast_bp.route("/forecast")
def forecast_home():
    # Pressure field data
    pressure_field = base.get_pressure_field(limit=20)

    # Forecasts sorted by pressure
    forecasts = base.get_narrative_forecasts_sql(limit=50)

    # Group by narrative arc
    arc_groups = {}
    for art in forecasts:
        arc = art.get("narrative_arc", "unclassified")
        arc_groups.setdefault(arc, []).append(art)

    return render_template("forecast.html",
        forecasts=forecasts,
        arc_groups=arc_groups,
        pressure_field=pressure_field,
        total=len(forecasts),
    )
