from __future__ import annotations
import os
import re
import json
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, request, jsonify, abort
import base
import config

reports_bp = Blueprint("reports", __name__)


def _write_report_entry(slug: str, markdown: str) -> str:
    """Write report markdown to entries directory."""
    path = os.path.join(config.ENTRIES_DIR, f"{slug}.md")
    os.makedirs(config.ENTRIES_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown)
    return path


def _reindex_report(slug: str):
    """Add report to FTS5 search index."""
    import sqlite3
    entry = base.get_entry(slug)
    if not entry:
        return
    db = sqlite3.connect(config.SEARCH_INDEX_DB)
    try:
        db.execute("DELETE FROM entries_fts WHERE slug = ?", (slug,))
        db.execute(
            "INSERT INTO entries_fts (slug, title, body, tags) VALUES (?, ?, ?, ?)",
            (entry.slug, entry.title, entry.body, " ".join(entry.tags)),
        )
        db.commit()
    finally:
        db.close()


def _index_article_metadata(metadata: dict):
    """Index article metadata into articles.db."""
    try:
        base.upsert_article(metadata)
    except Exception as e:
        print(f"  [WARN] Metadata indexing failed for {metadata.get('slug', '?')}: {e}")


@reports_bp.route("/reports")
def reports_home():
    reports = base.list_reports()
    page = request.args.get("page", 1, type=int)
    per_page = config.REPORTS_PER_PAGE
    offset = (page - 1) * per_page

    total = len(reports)
    page_reports = reports[offset:offset + per_page]

    # Count game types across reports
    game_type_counts = {}
    for r in page_reports:
        for gt in r.get("game_theory_highlights", []):
            gt_name = gt.get("game_type", "unknown") if isinstance(gt, dict) else "unknown"
            game_type_counts[gt_name] = game_type_counts.get(gt_name, 0) + 1

    return render_template("reports.html",
        reports=page_reports,
        total=total,
        page=page,
        per_page=per_page,
        game_type_counts=game_type_counts,
        book_mode=False,
    )


@reports_bp.route("/reports/book")
def reports_book():
    reports = base.list_reports()
    # Reverse for chronological order (oldest first = book order)
    reports.reverse()
    return render_template("reports.html",
        reports=reports,
        total=len(reports),
        page=1,
        per_page=len(reports),
        game_type_counts={},
        book_mode=True,
    )


@reports_bp.route("/reports/latest")
def reports_latest():
    latest = base.get_latest_report()
    if not latest:
        return redirect(url_for("reports.reports_home"))
    return redirect(url_for("entry.entry_page", slug=latest["slug"]))


@reports_bp.route("/api/ingest-report", methods=["POST"])
def ingest_report():
    # Auth check
    ingest_key = request.headers.get("X-Ingest-Key", "")
    if ingest_key != config.RABBIT_INGEST_KEY:
        abort(403, description="Invalid ingest key")

    data = request.get_json()
    if not data or "slug" not in data or "markdown" not in data:
        abort(400, description="Missing slug or markdown")

    slug = data["slug"]
    markdown = data["markdown"]

    # Write entry file
    path = _write_report_entry(slug, markdown)

    # Reindex FTS5
    _reindex_report(slug)

    # NEW: If structured metadata provided, index it
    if "metadata" in data:
        _index_article_metadata(data["metadata"])

    return jsonify({"status": "ok", "slug": slug, "path": path})


@reports_bp.route("/api/ingest-prediction", methods=["POST"])
def ingest_prediction():
    """Ingest a prediction from the tomorrow_generator script."""
    ingest_key = request.headers.get("X-Ingest-Key", "")
    if ingest_key != config.RABBIT_INGEST_KEY:
        abort(403, description="Invalid ingest key")

    data = request.get_json()
    if not data or "source_slug" not in data or "title" not in data:
        abort(400, description="Missing source_slug or title")

    pred_id = base.upsert_prediction(data)
    return jsonify({"status": "ok", "id": pred_id})


@reports_bp.route("/api/score-prediction", methods=["POST"])
def score_prediction():
    """Update accuracy scoring for a prediction."""
    ingest_key = request.headers.get("X-Ingest-Key", "")
    if ingest_key != config.RABBIT_INGEST_KEY:
        abort(403, description="Invalid ingest key")

    data = request.get_json()
    if not data or "id" not in data or "accuracy_score" not in data:
        abort(400, description="Missing id or accuracy_score")

    base.update_prediction_score(
        pred_id=data["id"],
        score=data["accuracy_score"],
        detail=data.get("accuracy_detail", ""),
        matching_slugs=data.get("matching_slugs", []),
        scored_at=data.get("scored_at", datetime.now(timezone.utc).isoformat()),
    )
    return jsonify({"status": "ok"})


@reports_bp.route("/api/articles-with-forecasts")
def articles_with_forecasts():
    """Return articles with forecast data for the tomorrow generator."""
    ingest_key = request.headers.get("X-Ingest-Key", "")
    if ingest_key != config.RABBIT_INGEST_KEY:
        abort(403, description="Invalid ingest key")

    limit = request.args.get("limit", 30, type=int)
    db = base._get_articles_db()
    try:
        rows = db.execute("""
            SELECT a.slug, a.title, a.source, a.game_type, a.forecast, a.created,
                   a.narrative_energy, a.pressure_score, a.stabilization_score,
                   a.phase_shift_risk, a.pressure_vector, a.stabilization_vector,
                   a.liquidity_score, a.cheap_narrative, a.expensive_narrative,
                   a.hitchhiker_summary,
                   a.signal_type, a.signal_credibility, a.deception_probability,
                   a.game_family, a.move_type, a.strategy_detected, a.cooperation_level,
                   a.cascade_risk, a.independent_sources, a.reversal_risk,
                   a.strategy_type, a.strategy_fitness, a.predicted_next_cycle,
                   a.cognitive_bias_score
            FROM articles a
            WHERE a.forecast IS NOT NULL AND a.forecast != ''
              AND a.created >= datetime('now', '-12 hours')
            ORDER BY a.narrative_energy DESC
            LIMIT ?
        """, (limit,)).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            d["actors"] = base.get_actors_for(d["slug"])
            results.append(d)
        return jsonify({"articles": results})
    finally:
        db.close()


@reports_bp.route("/api/existing-predictions")
def existing_predictions():
    """Return prediction source_slugs for a given cycle (dedup check)."""
    ingest_key = request.headers.get("X-Ingest-Key", "")
    if ingest_key != config.RABBIT_INGEST_KEY:
        abort(403, description="Invalid ingest key")

    cycle = request.args.get("cycle", "")
    db = base._get_articles_db()
    try:
        rows = db.execute(
            "SELECT source_slug FROM predictions WHERE target_cycle = ?",
            (cycle,)
        ).fetchall()
        return jsonify({"slugs": [r["source_slug"] for r in rows]})
    finally:
        db.close()


@reports_bp.route("/api/unscored-predictions")
def unscored_predictions():
    """Return unscored predictions for accuracy scoring."""
    ingest_key = request.headers.get("X-Ingest-Key", "")
    if ingest_key != config.RABBIT_INGEST_KEY:
        abort(403, description="Invalid ingest key")

    limit = request.args.get("limit", 20, type=int)
    preds = base.get_unscored_predictions(limit=limit)
    return jsonify({"predictions": preds})
def conspiracy_slugs():
    """Return all conspiracy entry slugs + titles for matching."""
    entries = base.list_entries(domain="conspiracy")
    return jsonify({"entries": [{"slug": e["slug"], "title": e["title"]} for e in entries]})
