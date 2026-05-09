"""Backfill articles.db from existing .md article files."""
import os
import sqlite3
import yaml

DATA_DIR = os.environ.get("DATA_DIR", "/data")
ENTRIES_DIR = os.path.join(DATA_DIR, "entries")
ARTICLES_DB = os.path.join(DATA_DIR, "articles.db")


def get_db():
    db = sqlite3.connect(ARTICLES_DB)
    db.execute("PRAGMA journal_mode=WAL")
    db.row_factory = sqlite3.Row
    return db


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].strip()
    return meta, body


def backfill():
    db = get_db()

    # Count existing in DB
    existing = db.execute("SELECT COUNT(*) as c FROM articles").fetchone()["c"]
    print(f"Existing articles in DB: {existing}")

    if not os.path.isdir(ENTRIES_DIR):
        print("No entries directory found.")
        return

    art_files = sorted(f for f in os.listdir(ENTRIES_DIR) if f.startswith("art-") and f.endswith(".md"))
    print(f"Found {len(art_files)} article files to process")

    inserted = 0
    updated = 0
    skipped = 0

    for fname in art_files:
        slug = fname[:-3]
        path = os.path.join(ENTRIES_DIR, fname)

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        fm, body = parse_frontmatter(text)
        if not fm:
            print(f"  SKIP (no frontmatter): {slug}")
            skipped += 1
            continue

        # Check if already in DB with energy data
        row = db.execute("SELECT narrative_energy FROM articles WHERE slug = ?", (slug,)).fetchone()
        if row and row["narrative_energy"] and row["narrative_energy"] > 0:
            skipped += 1
            continue

        # Extract all fields from frontmatter
        title = fm.get("title", slug)
        source = fm.get("source", "")
        original_url = fm.get("original_url", "")
        game_type = fm.get("game_type", "")
        bias_type = fm.get("bias_type", "")
        controlled = 1 if fm.get("controlled_narrative") else 0
        actionability = fm.get("actionability", "low")
        narrative_arc = fm.get("narrative_arc", "")
        timeline_position = fm.get("timeline_position", "")
        forecast = fm.get("forecast", "")
        created = str(fm.get("created", "")) if fm.get("created") else ""
        updated_ts = str(fm.get("updated", "")) if fm.get("updated") else ""
        report_slug = ""
        seealso = fm.get("seealso", [])
        if seealso:
            for s in seealso:
                if s.startswith("report-"):
                    report_slug = s
                    break
        domain = fm.get("domain", "conspiracy")
        hitchhiker = fm.get("hitchhiker_summary", "")

        # New fields (may or may not exist in older articles)
        narrative_energy = fm.get("narrative_energy", 0.5)
        raw_events = fm.get("raw_events")
        elite_framing = fm.get("elite_framing")
        energy_drivers = fm.get("energy_drivers")
        regime_response = fm.get("regime_response")
        equilibrium_shift = fm.get("equilibrium_shift", "none")
        pressure_vector = fm.get("pressure_vector")
        stabilization_vector = fm.get("stabilization_vector")
        pressure_score = fm.get("pressure_score", 0.0)
        stabilization_score = fm.get("stabilization_score", 0.0)
        counterforce_actors = fm.get("counterforce_actors")
        offramps = fm.get("offramps")
        escalation_triggers = fm.get("escalation_triggers")
        phase_shift_risk = fm.get("phase_shift_risk")
        half_life = fm.get("half_life", "")
        meme_portability = fm.get("meme_portability", 0.0)
        elite_utility = fm.get("elite_utility", 0.0)
        symbolic_density = fm.get("symbolic_density", 0.0)
        visual_anchors = fm.get("visual_anchors", 0.0)
        enemy_coherence = fm.get("enemy_coherence", 0.0)
        liquidity_score = fm.get("liquidity_score", 0.0)
        cheap_narrative = fm.get("cheap_narrative")
        expensive_narrative = fm.get("expensive_narrative")
        reflexivity_risk = fm.get("reflexivity_risk", 0.0)

        # Derive default energy from existing fields if not set
        if narrative_energy == 0.5 and not fm.get("narrative_energy"):
            # Heuristic: controlled narratives with high actionability get higher energy
            base = 0.3
            if controlled:
                base += 0.2
            if actionability in ("high", "medium"):
                base += 0.15
            if game_type and game_type != "none apparent":
                base += 0.1
            if narrative_arc in ("escalation", "revelation", "cover-up"):
                base += 0.1
            narrative_energy = min(base, 1.0)

        # Upsert
        db.execute("""
            INSERT INTO articles (slug, title, source, original_url, game_type, bias_type,
                controlled_narrative, actionability, narrative_arc, timeline_position, forecast,
                created, updated, report_slug, domain, narrative_energy, narrative_liquidity,
                raw_events, elite_framing, energy_drivers, regime_response, equilibrium_shift,
                pressure_vector, stabilization_vector, pressure_score, stabilization_score,
                counterforce_actors, offramps, escalation_triggers, phase_shift_risk,
                half_life, meme_portability, elite_utility, symbolic_density, visual_anchors,
                enemy_coherence, liquidity_score, cheap_narrative, expensive_narrative,
                reflexivity_risk, hitchhiker_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                title=excluded.title, source=excluded.source, original_url=excluded.original_url,
                game_type=excluded.game_type, bias_type=excluded.bias_type,
                controlled_narrative=excluded.controlled_narrative, actionability=excluded.actionability,
                narrative_arc=excluded.narrative_arc, timeline_position=excluded.timeline_position,
                forecast=excluded.forecast, updated=excluded.updated, report_slug=excluded.report_slug,
                narrative_energy=excluded.narrative_energy,
                raw_events=excluded.raw_events, elite_framing=excluded.elite_framing,
                energy_drivers=excluded.energy_drivers, regime_response=excluded.regime_response,
                equilibrium_shift=excluded.equilibrium_shift,
                pressure_vector=excluded.pressure_vector, stabilization_vector=excluded.stabilization_vector,
                pressure_score=excluded.pressure_score, stabilization_score=excluded.stabilization_score,
                counterforce_actors=excluded.counterforce_actors, offramps=excluded.offramps,
                escalation_triggers=excluded.escalation_triggers, phase_shift_risk=excluded.phase_shift_risk,
                half_life=excluded.half_life, meme_portability=excluded.meme_portability,
                elite_utility=excluded.elite_utility, symbolic_density=excluded.symbolic_density,
                visual_anchors=excluded.visual_anchors, enemy_coherence=excluded.enemy_coherence,
                liquidity_score=excluded.liquidity_score, cheap_narrative=excluded.cheap_narrative,
                expensive_narrative=excluded.expensive_narrative,
                reflexivity_risk=excluded.reflexivity_risk, hitchhiker_summary=excluded.hitchhiker_summary
        """, (
            slug, title, source, original_url, game_type, bias_type,
            controlled, actionability, narrative_arc, timeline_position, forecast,
            created, updated_ts, report_slug, domain, narrative_energy, 0.5,
            raw_events, elite_framing, energy_drivers, regime_response, equilibrium_shift,
            pressure_vector, stabilization_vector, pressure_score, stabilization_score,
            counterforce_actors, offramps, escalation_triggers, phase_shift_risk,
            half_life, meme_portability, elite_utility, symbolic_density, visual_anchors,
            enemy_coherence, liquidity_score, cheap_narrative, expensive_narrative,
            reflexivity_risk, hitchhiker,
        ))

        # Actors
        db.execute("DELETE FROM article_actors WHERE article_slug = ?", (slug,))
        for actor in fm.get("actors", []):
            if actor and actor.strip():
                db.execute("INSERT INTO article_actors (article_slug, actor) VALUES (?, ?)",
                           (slug, actor.strip()))

        # Claims
        db.execute("DELETE FROM article_claims WHERE article_slug = ?", (slug,))
        for claim in fm.get("claims", []):
            if claim and "(batch parse failed)" not in claim and "(analysis failed)" not in claim:
                db.execute("INSERT INTO article_claims (article_slug, claim) VALUES (?, ?)",
                           (slug, str(claim)))

        # Contradictions
        db.execute("DELETE FROM article_contradictions WHERE article_slug = ?", (slug,))
        for c in fm.get("contradictions", []):
            if isinstance(c, dict):
                db.execute("""INSERT INTO article_contradictions
                    (article_slug, claim_now, claim_then, significance, explanation, source_slug)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (slug, c.get("claim_now", ""), c.get("claim_then", ""),
                     c.get("significance", "medium"), c.get("explanation", ""),
                     c.get("source_slug", "")))

        # Mythology
        db.execute("DELETE FROM article_mythology WHERE article_slug = ?", (slug,))
        myth_signals = fm.get("mythology_signals", [])
        for signal in myth_signals:
            if isinstance(signal, dict):
                db.execute("""INSERT INTO article_mythology
                    (article_slug, archetype, signals, cultural_function, power_function)
                    VALUES (?, ?, ?, ?, ?)""",
                    (slug, signal.get("archetype", ""), signal.get("signals", ""),
                     signal.get("cultural_function", ""), signal.get("power_function", "")))

        if row:
            updated += 1
        else:
            inserted += 1

    db.commit()

    # Stats
    total = db.execute("SELECT COUNT(*) as c FROM articles").fetchone()["c"]
    actors = db.execute("SELECT COUNT(DISTINCT actor) as c FROM article_actors").fetchone()["c"]
    contradictions = db.execute("SELECT COUNT(*) as c FROM article_contradictions").fetchone()["c"]
    myths = db.execute("SELECT COUNT(*) as c FROM article_mythology").fetchone()["c"]

    print(f"\nBackfill complete:")
    print(f"  Inserted: {inserted}")
    print(f"  Updated: {updated}")
    print(f"  Skipped (already had energy): {skipped}")
    print(f"  Total articles in DB: {total}")
    print(f"  Unique actors: {actors}")
    print(f"  Contradictions: {contradictions}")
    print(f"  Mythology signals: {myths}")

    db.close()


if __name__ == "__main__":
    backfill()
