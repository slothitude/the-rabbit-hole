from __future__ import annotations
from flask import Blueprint, render_template
import base

tier_bp = Blueprint("tier", __name__)

TIER_NAMES = {
    1: "The Prison",
    2: "Hidden History",
    3: "The Hidden Reality",
    4: "Control Systems",
    5: "The Exit/Upgrade",
}

TIER_COLORS = {
    1: "#ff3333",
    2: "#ff8c00",
    3: "#ffd500",
    4: "#00e676",
    5: "#b388ff",
}

TIER_DESCRIPTIONS = {
    1: "The deepest level — global control systems, hidden power structures, and the machinery that keeps the wheels turning. Best not to think about it too hard, or at all.",
    2: "Ancient secrets buried beneath the sands of time, or possibly just sand. The sort of history that didn't make it into textbooks, mostly because it's quite difficult to verify.",
    3: "The bits they don't want you to know about — mainly because 'they' probably don't know about them either. UFOs, aliens, and technology that may or may not work.",
    4: "Systems of control so elaborate they'd make a Vogon bureaucracy look like a lemonade stand. Weather manipulation, population engineering, and number games.",
    5: "The light at the end of the tunnel, assuming the tunnel isn't just another construct. Consciousness expansion, ascension, and the distinct possibility that everything is going to be fine. Maybe.",
}


@tier_bp.route("/tier/<int:tier>")
def tier_page(tier):
    if tier < 1 or tier > 5:
        tier = 1
    entries = base.list_entries(domain="conspiracy")
    tier_entries = [e for e in entries if e.get("tier") == tier]
    return render_template("tier.html",
        tier=tier,
        tier_name=TIER_NAMES.get(tier, f"Tier {tier}"),
        tier_color=TIER_COLORS.get(tier, "#c8ff00"),
        tier_description=TIER_DESCRIPTIONS.get(tier, ""),
        entries=tier_entries,
    )
