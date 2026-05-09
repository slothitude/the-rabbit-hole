from __future__ import annotations
import random
from flask import Blueprint, render_template, redirect, url_for
import base

home_bp = Blueprint("home", __name__)

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

QUOTES = [
    "The Guide is definitive. Reality is frequently inaccurate.",
    "Don't Panic. Unless panicking would help. It usually doesn't.",
    "In the beginning the Universe was created. This has made a lot of people very angry and been widely regarded as a bad move.",
    "The answer to the ultimate question of life, the universe, and everything is 42. The question itself remains inconveniently classified.",
    "Anyone who is capable of getting themselves made President should on no account be allowed to do the job.",
    "There is a theory which states that if ever anyone discovers exactly what the Universe is for and why it is here, it will instantly disappear and be replaced by something even more bizarrely inexplicable.",
    "The ships hung in the sky in much the same way that bricks don't.",
    "Time is an illusion. Lunchtime doubly so.",
    "For a moment, nothing happened. Then, after a second or so, nothing continued to happen.",
    "It is a mistake to think you can solve any major problems just with potatoes.",
]


@home_bp.route("/")
def title_page():
    return render_template("title_page.html")


@home_bp.route("/home")
def home():
    # Traditional tier data
    entries = base.list_entries(domain="conspiracy")
    tier_counts = {i: 0 for i in range(1, 6)}
    category_map: dict[int, list[dict]] = {i: [] for i in range(1, 6)}
    for e in entries:
        t = e.get("tier")
        if t and 1 <= t <= 5:
            tier_counts[t] += 1
            category_map[t].append(e)

    # Narrative OS dashboard data
    total_articles = base.count_articles_sql()
    high_energy = base.get_high_energy_articles(threshold=0.7, limit=5)
    pressure_field = base.get_pressure_field(limit=5)
    expiring = base.get_expiring_narratives(limit=5)
    liquid = base.get_liquid_narratives(limit=5)
    contradictions = base.get_contradictions_sql()[:5]
    game_dist = base.get_game_type_distribution()

    return render_template("home.html",
        total=len(entries),
        tier_counts=tier_counts,
        category_map=category_map,
        tier_names=TIER_NAMES,
        tier_colors=TIER_COLORS,
        tier_descriptions=TIER_DESCRIPTIONS,
        quote=random.choice(QUOTES),
        # Narrative OS data
        total_articles=total_articles,
        high_energy=high_energy,
        pressure_field=pressure_field,
        expiring=expiring,
        liquid=liquid,
        contradictions=contradictions,
        game_dist=game_dist,
    )


@home_bp.route("/random")
def random_entry():
    entries = base.list_entries(domain="conspiracy")
    if not entries:
        return redirect(url_for("home.title_page"))
    pick = random.choice(entries)
    return redirect(url_for("entry.entry_page", slug=pick["slug"]))
