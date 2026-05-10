from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for
import base
import game_primitives
from datetime import datetime, timedelta, timezone

paper_bp = Blueprint("paper", __name__)

AEST = timezone(timedelta(hours=10))


@paper_bp.route("/paper")
def paper_home():
    now = datetime.now(AEST)
    edition = now.hour // 6 + 1

    # ── Time helpers ──
    next_cycle_hour = ((now.hour // 6) + 1) * 6
    if next_cycle_hour >= 24:
        next_cycle_hour = 0
    next_edition = now.replace(hour=next_cycle_hour, minute=0, second=0, microsecond=0)
    if next_edition <= now:
        next_edition += timedelta(hours=24)
    hours_until = round((next_edition - now).total_seconds() / 3600, 1)

    # ── Cycle strings ──
    today_cycle = f"{now.strftime('%Y-%m-%d')}-ed1"
    current_cycle = f"{now.strftime('%Y-%m-%d')}-ed{edition}"
    tomorrow = now + timedelta(days=1)
    next_day_cycle = f"{tomorrow.strftime('%Y-%m-%d')}-ed1"
    future_day = now + timedelta(days=2)
    future_cycle = f"{future_day.strftime('%Y-%m-%d')}-ed1"

    # ── TODAY: real articles ──
    today_articles = base.get_tomorrows_paper(limit=20)
    today_sections = base.get_tomorrows_paper_sections(limit_per_section=8)
    today_section_counts = {name: len(arts) for name, arts in today_sections.items()}

    # ── TOMORROW: 24h predictions ──
    tomorrow_preds = base.get_predictions(limit=20, cycle=today_cycle)
    tomorrow_sections = base.get_predictions_by_section(cycle=today_cycle, limit_per_section=8)
    tomorrow_section_counts = {name: len(arts) for name, arts in tomorrow_sections.items()}

    # ── DAY+2: 48h predictions ──
    dayafter_preds = base.get_predictions(limit=20, cycle=next_day_cycle)
    has_dayafter = len(dayafter_preds) > 0
    pressure_map = base.get_pressure_map(limit=20)
    polymarket = base.get_polymarket_articles(limit=15)
    wild_cards = base.get_wild_cards(limit=8)
    cheap_expensive = base.get_cheap_vs_expensive(limit=10)

    # Escalation count
    real_preds = base.get_day_after_predictions(limit=20)
    escalation_count = sum(
        1 for p in real_preds
        if p.get("escalation_triggers") and p["escalation_triggers"].strip()
    )

    # ── FUTURE: 72h+ predictions ──
    future_preds = base.get_predictions(limit=20, cycle=future_cycle)
    has_future = len(future_preds) > 0
    if not has_future:
        future_preds = base.get_future_forecasts(limit=20)
    phase_shifts = base.get_phase_shifts(limit=15)
    half_lives = base.get_half_life_ranked(limit=15)
    mythology = base.get_mythology_forecasts(limit=15)
    phase_count = len(phase_shifts)

    # ── Shared sidebars ──
    contradictions = base.get_contradictions_sql()[:5]
    expiring = base.get_expiring_narratives(limit=5)
    game_dist = base.get_game_type_distribution()
    accuracy_stats = base.get_prediction_accuracy_stats()

    # Enrich game_dist with game_primitives
    for g in game_dist:
        model = game_primitives.get_game_model(g["game_type"])
        if model:
            g["equilibrium"] = model["equilibrium"]
            g["escalation_pattern"] = model["escalation_pattern"]
            g["wildcard_type"] = model["wildcard_type"]
        else:
            g["equilibrium"] = ""
            g["escalation_pattern"] = ""
            g["wildcard_type"] = ""

    # Check hash for initial tab
    initial_tab = request.args.get("tab", "today")

    return render_template("paper.html",
        # Time
        edition=edition,
        today_date=now,
        tomorrow_date=now + timedelta(hours=24),
        future_date=now + timedelta(hours=48),
        six_months=now + timedelta(days=180),
        hours_until=hours_until,
        initial_tab=initial_tab,
        # Today
        today_articles=today_articles,
        today_sections=today_sections,
        today_section_counts=today_section_counts,
        today_total=len(today_articles),
        # Tomorrow
        tomorrow_preds=tomorrow_preds,
        tomorrow_sections=tomorrow_sections,
        tomorrow_section_counts=tomorrow_section_counts,
        tomorrow_total=len(tomorrow_preds),
        # Day+2
        dayafter_preds=dayafter_preds,
        has_dayafter=has_dayafter,
        pressure_map=pressure_map,
        polymarket=polymarket,
        wild_cards=wild_cards,
        cheap_expensive=cheap_expensive,
        escalation_count=escalation_count,
        dayafter_total=len(dayafter_preds),
        # Future
        future_preds=future_preds,
        has_future=has_future,
        phase_shifts=phase_shifts,
        half_lives=half_lives,
        mythology=mythology,
        phase_count=phase_count,
        future_total=len(future_preds),
        # Shared
        contradictions=contradictions,
        expiring=expiring,
        game_dist=game_dist,
        accuracy_stats=accuracy_stats,
    )
