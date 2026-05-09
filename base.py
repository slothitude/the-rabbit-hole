"""Shared data access — reads from the same data directory as the-guide."""
from __future__ import annotations
import os
import re
import sqlite3
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import config


# --- Entry model ---

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_slug(slug: str) -> str:
    slug = slug.strip().lower()
    if not SLUG_RE.match(slug):
        raise ValueError(f"Invalid slug: {slug!r}")
    return slug


@dataclass
class Entry:
    slug: str
    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    seealso: list[str] = field(default_factory=list)
    image: Optional[str] = None
    triples: list[dict] = field(default_factory=list)
    created: Optional[str] = None
    updated: Optional[str] = None
    domain: str = "conspiracy"
    tier: Optional[int] = None
    category: Optional[str] = None
    evidence: Optional[str] = None
    news_connections: list[str] = field(default_factory=list)
    hitchhiker_summary: Optional[str] = None

    def __post_init__(self):
        self.slug = validate_slug(self.slug)


# --- Frontmatter parsing ---

def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    for key in ("created", "updated"):
        if key in meta and meta[key] is not None:
            meta[key] = str(meta[key])
    body = parts[2].strip()
    return meta, body


def _entry_path(slug: str) -> str:
    return os.path.join(config.ENTRIES_DIR, f"{slug}.md")


def get_entry(slug: str) -> Optional[Entry]:
    path = _entry_path(slug)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    meta, body = _parse_frontmatter(text)
    return Entry(
        slug=meta.get("slug", slug),
        title=meta.get("title", slug),
        body=body,
        tags=meta.get("tags", []),
        seealso=meta.get("seealso", []),
        image=meta.get("image"),
        triples=meta.get("triples", []),
        created=meta.get("created"),
        updated=meta.get("updated"),
        domain=meta.get("domain", "encyclopedia"),
        tier=meta.get("tier"),
        category=meta.get("category"),
        evidence=meta.get("evidence"),
        news_connections=meta.get("news_connections", []),
        hitchhiker_summary=meta.get("hitchhiker_summary"),
    )


def list_entries(domain: str = "conspiracy") -> list[dict]:
    entries = []
    if not os.path.isdir(config.ENTRIES_DIR):
        return entries
    for fname in sorted(os.listdir(config.ENTRIES_DIR)):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(config.ENTRIES_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        meta, _ = _parse_frontmatter(text)
        if meta.get("domain", "encyclopedia") != domain:
            continue
        entries.append({
            "slug": meta.get("slug", fname[:-3]),
            "title": meta.get("title", fname[:-3]),
            "tags": meta.get("tags", []),
            "image": meta.get("image"),
            "created": meta.get("created"),
            "updated": meta.get("updated"),
            "domain": meta.get("domain", "encyclopedia"),
            "tier": meta.get("tier"),
            "category": meta.get("category"),
            "evidence": meta.get("evidence"),
        })
    return entries


def entry_exists(slug: str) -> bool:
    return os.path.isfile(_entry_path(slug))


def list_reports() -> list[dict]:
    """List report entries (category=News Report), sorted by created desc."""
    entries = []
    if not os.path.isdir(config.ENTRIES_DIR):
        return entries
    for fname in sorted(os.listdir(config.ENTRIES_DIR), reverse=True):
        if not fname.startswith("report-") or not fname.endswith(".md"):
            continue
        path = os.path.join(config.ENTRIES_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        meta, _ = _parse_frontmatter(text)
        if meta.get("category") != "News Report":
            continue
        entries.append({
            "slug": meta.get("slug", fname[:-3]),
            "title": meta.get("title", fname[:-3]),
            "tags": meta.get("tags", []),
            "created": meta.get("created"),
            "updated": meta.get("updated"),
            "hitchhiker_summary": meta.get("hitchhiker_summary", ""),
            "game_theory_highlights": meta.get("game_theory_highlights", []),
            "news_connections": meta.get("news_connections", []),
        })
    return entries


def get_latest_report() -> Optional[dict]:
    reports = list_reports()
    return reports[0] if reports else None


def list_articles(actor: str = None, game_type: str = None, narrative_arc: str = None) -> list[dict]:
    """List article entries (category=News Article), sorted by created desc."""
    entries = []
    if not os.path.isdir(config.ENTRIES_DIR):
        return entries
    for fname in sorted(os.listdir(config.ENTRIES_DIR), reverse=True):
        if not fname.startswith("art-") or not fname.endswith(".md"):
            continue
        path = os.path.join(config.ENTRIES_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        meta, _ = _parse_frontmatter(text)
        if meta.get("category") != "News Article":
            continue
        if actor:
            actors = meta.get("actors", [])
            if actor.lower() not in [a.lower() for a in actors]:
                continue
        if game_type and meta.get("game_type", "").lower() != game_type.lower():
            continue
        if narrative_arc and meta.get("narrative_arc", "").lower() != narrative_arc.lower():
            continue
        entries.append({
            "slug": meta.get("slug", fname[:-3]),
            "title": meta.get("title", fname[:-3]),
            "tags": meta.get("tags", []),
            "created": meta.get("created"),
            "updated": meta.get("updated"),
            "source": meta.get("source", ""),
            "original_url": meta.get("original_url", ""),
            "game_type": meta.get("game_type", ""),
            "bias_type": meta.get("bias_type", ""),
            "controlled_narrative": meta.get("controlled_narrative", False),
            "actionability": meta.get("actionability", "low"),
            "actors": meta.get("actors", []),
            "claims": meta.get("claims", []),
            "contradictions": meta.get("contradictions", []),
            "narrative_arc": meta.get("narrative_arc", ""),
            "timeline_position": meta.get("timeline_position", ""),
            "mythology_signals": meta.get("mythology_signals", []),
            "forecast": meta.get("forecast", ""),
            "hitchhiker_summary": meta.get("hitchhiker_summary", ""),
            "seealso": meta.get("seealso", []),
        })
    return entries


def get_all_actors() -> list[dict]:
    """Get all unique actors across articles with article counts."""
    actor_counts = {}
    for art in list_articles():
        for actor in art.get("actors", []):
            key = actor.strip()
            if key:
                actor_counts[key] = actor_counts.get(key, 0) + 1
    return [{"name": k, "count": v} for k, v in sorted(actor_counts.items(), key=lambda x: -x[1])]


def get_actor_articles(actor: str) -> list[dict]:
    """Get all articles for a specific actor."""
    return list_articles(actor=actor)


def get_contradictions() -> list[dict]:
    """Get all articles with contradictions detected."""
    results = []
    for art in list_articles():
        if art.get("contradictions"):
            results.append(art)
    return results


def get_narrative_forecasts() -> list[dict]:
    """Get all articles with forecasts."""
    results = []
    for art in list_articles():
        if art.get("forecast"):
            results.append(art)
    return results


def get_mythology_signals() -> list[dict]:
    """Get all articles with mythology signals."""
    results = []
    for art in list_articles():
        if art.get("mythology_signals"):
            results.append(art)
    return results


# --- Triple store (read-only) ---

@dataclass
class Triple:
    id: int
    subject: str
    predicate: str
    object: str
    context: Optional[str] = None

    def to_dict(self):
        return {"id": self.id, "subject": self.subject, "predicate": self.predicate, "object": self.object, "context": self.context}


def _get_triple_db() -> sqlite3.Connection:
    db = sqlite3.connect(config.DB_PATH)
    db.execute("PRAGMA journal_mode=WAL")
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = _get_triple_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS triples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            context TEXT
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_subject ON triples(subject)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_object ON triples(object)")
    db.commit()
    db.close()


def get_triples_for(slug: str) -> tuple[list[Triple], list[Triple]]:
    db = _get_triple_db()
    outgoing = db.execute("SELECT * FROM triples WHERE subject = ?", (slug,)).fetchall()
    incoming = db.execute("SELECT * FROM triples WHERE object = ?", (slug,)).fetchall()
    db.close()
    return (
        [Triple(id=r["id"], subject=r["subject"], predicate=r["predicate"], object=r["object"], context=r["context"]) for r in outgoing],
        [Triple(id=r["id"], subject=r["subject"], predicate=r["predicate"], object=r["object"], context=r["context"]) for r in incoming],
    )


# --- FTS5 search ---

def _get_search_db() -> sqlite3.Connection:
    db = sqlite3.connect(config.SEARCH_INDEX_DB)
    db.execute("PRAGMA journal_mode=WAL")
    return db


def init_search_db():
    db = _get_search_db()
    db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
            slug, title, body, tags,
            tokenize='porter unicode61'
        )
    """)
    db.commit()
    db.close()


def reindex():
    init_search_db()
    db = _get_search_db()
    db.execute("DELETE FROM entries_fts")
    for meta in list_entries():
        entry = get_entry(meta["slug"])
        if not entry:
            continue
        db.execute(
            "INSERT INTO entries_fts (slug, title, body, tags) VALUES (?, ?, ?, ?)",
            (entry.slug, entry.title, entry.body, " ".join(entry.tags)),
        )
    db.commit()
    db.close()


def search(query: str, limit: int = 20) -> list[dict]:
    db = _get_search_db()
    try:
        cursor = db.execute(
            """SELECT slug, title, tags, rank
               FROM entries_fts
               WHERE entries_fts MATCH ?
               ORDER BY rank
               LIMIT ?""",
            (query, limit),
        )
        results = []
        for row in cursor:
            results.append({"slug": row[0], "title": row[1], "tags": row[2].split() if row[2] else [], "rank": row[3]})
        return results
    except sqlite3.OperationalError:
        return []
    finally:
        db.close()


# --- Articles metadata database (Phase 0) ---

def _get_articles_db() -> sqlite3.Connection:
    db = sqlite3.connect(config.ARTICLES_DB)
    db.execute("PRAGMA journal_mode=WAL")
    db.row_factory = sqlite3.Row
    return db


def init_articles_db():
    db = _get_articles_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            slug TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source TEXT,
            original_url TEXT,
            game_type TEXT,
            bias_type TEXT,
            controlled_narrative INTEGER DEFAULT 0,
            actionability TEXT,
            narrative_arc TEXT,
            timeline_position TEXT,
            forecast TEXT,
            created TEXT,
            updated TEXT,
            report_slug TEXT,
            domain TEXT DEFAULT 'conspiracy',
            event_type TEXT,
            narrative_energy REAL DEFAULT 0.5,
            narrative_liquidity REAL DEFAULT 0.5,
            memetic_half_life TEXT,
            reflexivity_risk REAL DEFAULT 0.0,
            raw_events TEXT,
            elite_framing TEXT,
            energy_drivers TEXT,
            regime_response TEXT,
            equilibrium_shift TEXT DEFAULT 'none',
            pressure_vector TEXT,
            stabilization_vector TEXT,
            pressure_score REAL DEFAULT 0.0,
            stabilization_score REAL DEFAULT 0.0,
            counterforce_actors TEXT,
            offramps TEXT,
            escalation_triggers TEXT,
            phase_shift_risk TEXT,
            half_life TEXT,
            meme_portability REAL DEFAULT 0.0,
            elite_utility REAL DEFAULT 0.0,
            symbolic_density REAL DEFAULT 0.0,
            visual_anchors REAL DEFAULT 0.0,
            enemy_coherence REAL DEFAULT 0.0,
            liquidity_score REAL DEFAULT 0.0,
            cheap_narrative TEXT,
            expensive_narrative TEXT,
            hitchhiker_summary TEXT
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_articles_game_type ON articles(game_type)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_articles_arc ON articles(narrative_arc)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_articles_created ON articles(created)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_articles_energy ON articles(narrative_energy)")
    db.execute("""
        CREATE TABLE IF NOT EXISTS article_actors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_slug TEXT NOT NULL,
            actor TEXT NOT NULL,
            FOREIGN KEY (article_slug) REFERENCES articles(slug)
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_aa_actor ON article_actors(actor)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_aa_slug ON article_actors(article_slug)")
    db.execute("""
        CREATE TABLE IF NOT EXISTS article_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_slug TEXT NOT NULL,
            claim TEXT NOT NULL,
            claim_type TEXT DEFAULT 'event',
            FOREIGN KEY (article_slug) REFERENCES articles(slug)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS article_contradictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_slug TEXT NOT NULL,
            claim_now TEXT,
            claim_then TEXT,
            significance TEXT DEFAULT 'medium',
            explanation TEXT,
            source_slug TEXT,
            FOREIGN KEY (article_slug) REFERENCES articles(slug)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS article_mythology (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_slug TEXT NOT NULL,
            archetype TEXT,
            signals TEXT,
            cultural_function TEXT,
            power_function TEXT,
            FOREIGN KEY (article_slug) REFERENCES articles(slug)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS entity_aliases (
            canonical TEXT NOT NULL,
            alias TEXT NOT NULL UNIQUE,
            PRIMARY KEY (canonical, alias)
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_ea_alias ON entity_aliases(alias)")
    db.commit()
    db.close()


def upsert_article(meta: dict) -> None:
    """Insert/update article metadata from structured dict."""
    db = _get_articles_db()
    try:
        slug = meta["slug"]
        # Upsert main article row
        db.execute("""
            INSERT INTO articles (slug, title, source, original_url, game_type, bias_type,
                controlled_narrative, actionability, narrative_arc, timeline_position, forecast,
                created, updated, report_slug, domain, event_type, narrative_energy,
                narrative_liquidity, memetic_half_life, reflexivity_risk,
                raw_events, elite_framing, energy_drivers, regime_response, equilibrium_shift,
                pressure_vector, stabilization_vector, pressure_score, stabilization_score,
                counterforce_actors, offramps, escalation_triggers, phase_shift_risk,
                half_life, meme_portability, elite_utility, symbolic_density, visual_anchors,
                enemy_coherence, liquidity_score, cheap_narrative, expensive_narrative,
                hitchhiker_summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                title=excluded.title, source=excluded.source, original_url=excluded.original_url,
                game_type=excluded.game_type, bias_type=excluded.bias_type,
                controlled_narrative=excluded.controlled_narrative, actionability=excluded.actionability,
                narrative_arc=excluded.narrative_arc, timeline_position=excluded.timeline_position,
                forecast=excluded.forecast, updated=excluded.updated, report_slug=excluded.report_slug,
                event_type=excluded.event_type, narrative_energy=excluded.narrative_energy,
                narrative_liquidity=excluded.narrative_liquidity, memetic_half_life=excluded.memetic_half_life,
                reflexivity_risk=excluded.reflexivity_risk,
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
                hitchhiker_summary=excluded.hitchhiker_summary
        """, (
            slug, meta.get("title", ""), meta.get("source", ""), meta.get("original_url", ""),
            meta.get("game_type", ""), meta.get("bias_type", ""),
            1 if meta.get("controlled_narrative") else 0,
            meta.get("actionability", "low"), meta.get("narrative_arc", ""),
            meta.get("timeline_position", ""), meta.get("forecast", ""),
            meta.get("created", ""), meta.get("updated", ""), meta.get("report_slug", ""),
            meta.get("domain", "conspiracy"), meta.get("event_type", ""),
            meta.get("narrative_energy", 0.5), meta.get("narrative_liquidity", 0.5),
            meta.get("memetic_half_life", ""), meta.get("reflexivity_risk", 0.0),
            meta.get("raw_events"), meta.get("elite_framing"),
            meta.get("energy_drivers"), meta.get("regime_response"),
            meta.get("equilibrium_shift", "none"),
            meta.get("pressure_vector"), meta.get("stabilization_vector"),
            meta.get("pressure_score", 0.0), meta.get("stabilization_score", 0.0),
            meta.get("counterforce_actors"), meta.get("offramps"),
            meta.get("escalation_triggers"), meta.get("phase_shift_risk"),
            meta.get("half_life", ""), meta.get("meme_portability", 0.0),
            meta.get("elite_utility", 0.0), meta.get("symbolic_density", 0.0),
            meta.get("visual_anchors", 0.0), meta.get("enemy_coherence", 0.0),
            meta.get("liquidity_score", 0.0), meta.get("cheap_narrative"),
            meta.get("expensive_narrative"), meta.get("hitchhiker_summary", ""),
        ))

        # Clear + re-insert actors
        db.execute("DELETE FROM article_actors WHERE article_slug = ?", (slug,))
        for actor in meta.get("actors", []):
            resolved = resolve_entity(actor, db)
            db.execute("INSERT INTO article_actors (article_slug, actor) VALUES (?, ?)", (slug, resolved))

        # Clear + re-insert claims
        db.execute("DELETE FROM article_claims WHERE article_slug = ?", (slug,))
        for claim in meta.get("claims", []):
            if claim and "(batch parse failed)" not in claim and "(analysis failed)" not in claim:
                db.execute("INSERT INTO article_claims (article_slug, claim) VALUES (?, ?)", (slug, claim))

        # Clear + re-insert contradictions
        db.execute("DELETE FROM article_contradictions WHERE article_slug = ?", (slug,))
        for c in meta.get("contradictions", []):
            if isinstance(c, dict):
                db.execute("""INSERT INTO article_contradictions
                    (article_slug, claim_now, claim_then, significance, explanation, source_slug)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (slug, c.get("claim_now", ""), c.get("claim_then", ""),
                     c.get("significance", "medium"), c.get("explanation", ""),
                     c.get("source_slug", "")))

        # Clear + re-insert mythology
        db.execute("DELETE FROM article_mythology WHERE article_slug = ?", (slug,))
        myth = meta.get("mythology")
        if isinstance(myth, dict):
            db.execute("""INSERT INTO article_mythology
                (article_slug, archetype, signals, cultural_function, power_function)
                VALUES (?, ?, ?, ?, ?)""",
                (slug, myth.get("archetype", ""), myth.get("signals", ""),
                 myth.get("cultural_function", ""), myth.get("power_function", "")))

        db.commit()
    finally:
        db.close()


def resolve_entity(name: str, db: sqlite3.Connection = None) -> str:
    """Resolve entity alias to canonical name via entity_aliases table."""
    close = False
    if db is None:
        db = _get_articles_db()
        close = True
    try:
        row = db.execute("SELECT canonical FROM entity_aliases WHERE alias = ?", (name,)).fetchone()
        return row["canonical"] if row else name
    finally:
        if close:
            db.close()


def get_actors_for(slug: str) -> list[str]:
    """Get resolved actor names for an article."""
    db = _get_articles_db()
    try:
        rows = db.execute("SELECT actor FROM article_actors WHERE article_slug = ?", (slug,)).fetchall()
        return [r["actor"] for r in rows]
    finally:
        db.close()


def list_articles_sql(actor=None, game_type=None, arc=None, after=None, before=None,
                      energy_min=None, limit=50, offset=0) -> list[dict]:
    """SQL-powered article listing with all filters."""
    db = _get_articles_db()
    try:
        query = "SELECT * FROM articles WHERE 1=1"
        params = []

        if actor:
            query += " AND slug IN (SELECT article_slug FROM article_actors WHERE actor = ?)"
            params.append(actor)
        if game_type:
            query += " AND game_type = ?"
            params.append(game_type)
        if arc:
            query += " AND narrative_arc = ?"
            params.append(arc)
        if after:
            query += " AND created >= ?"
            params.append(after)
        if before:
            query += " AND created <= ?"
            params.append(before)
        if energy_min is not None:
            query += " AND narrative_energy >= ?"
            params.append(energy_min)

        query += " ORDER BY created DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = db.execute(query, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["actors"] = get_actors_for(d["slug"])
            results.append(d)
        return results
    finally:
        db.close()


def count_articles_sql(actor=None, game_type=None, arc=None, energy_min=None) -> int:
    """Count articles matching filters."""
    db = _get_articles_db()
    try:
        query = "SELECT COUNT(*) as cnt FROM articles WHERE 1=1"
        params = []
        if actor:
            query += " AND slug IN (SELECT article_slug FROM article_actors WHERE actor = ?)"
            params.append(actor)
        if game_type:
            query += " AND game_type = ?"
            params.append(game_type)
        if arc:
            query += " AND narrative_arc = ?"
            params.append(arc)
        if energy_min is not None:
            query += " AND narrative_energy >= ?"
            params.append(energy_min)
        row = db.execute(query, params).fetchone()
        return row["cnt"] if row else 0
    finally:
        db.close()


def get_all_actors_sql() -> list[dict]:
    """Get all unique actors with article counts (SQL-powered)."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT actor, COUNT(*) as cnt FROM article_actors
            GROUP BY actor ORDER BY cnt DESC
        """).fetchall()
        return [{"name": r["actor"], "count": r["cnt"]} for r in rows]
    finally:
        db.close()


def get_game_types_sql() -> list[str]:
    """Get distinct game types from articles."""
    db = _get_articles_db()
    try:
        rows = db.execute("SELECT DISTINCT game_type FROM articles WHERE game_type != '' ORDER BY game_type").fetchall()
        return [r["game_type"] for r in rows]
    finally:
        db.close()


def get_arcs_sql() -> list[str]:
    """Get distinct narrative arcs from articles."""
    db = _get_articles_db()
    try:
        rows = db.execute("SELECT DISTINCT narrative_arc FROM articles WHERE narrative_arc != '' ORDER BY narrative_arc").fetchall()
        return [r["narrative_arc"] for r in rows]
    finally:
        db.close()


def get_contradictions_sql() -> list[dict]:
    """Get all articles with contradictions (SQL-powered)."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT a.slug, a.title, a.source, a.created, a.game_type, a.narrative_arc,
                   c.claim_now, c.claim_then, c.significance, c.explanation
            FROM article_contradictions c
            JOIN articles a ON c.article_slug = a.slug
            ORDER BY c.significance DESC, a.created DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_narrative_forecasts_sql(limit=50) -> list[dict]:
    """Get articles with forecasts, highest pressure first."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT * FROM articles
            WHERE forecast IS NOT NULL AND forecast != ''
            ORDER BY pressure_score DESC, created DESC
            LIMIT ?
        """, (limit,)).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["actors"] = get_actors_for(d["slug"])
            results.append(d)
        return results
    finally:
        db.close()


def get_mythology_signals_sql() -> list[dict]:
    """Get all articles with mythology signals (SQL-powered)."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT a.slug, a.title, a.source, a.created, a.narrative_arc,
                   m.archetype, m.signals, m.cultural_function, m.power_function
            FROM article_mythology m
            JOIN articles a ON m.article_slug = a.slug
            ORDER BY a.created DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_actor_articles_sql(actor: str, limit=50) -> list[dict]:
    """Get all articles for a specific actor (SQL-powered)."""
    resolved = resolve_entity(actor)
    return list_articles_sql(actor=resolved, limit=limit)


def get_high_energy_articles(threshold=0.7, limit=10) -> list[dict]:
    """Get articles above narrative energy threshold."""
    db = _get_articles_db()
    try:
        rows = db.execute(
            "SELECT * FROM articles WHERE narrative_energy >= ? ORDER BY narrative_energy DESC, created DESC LIMIT ?",
            (threshold, limit)
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["actors"] = get_actors_for(d["slug"])
            results.append(d)
        return results
    finally:
        db.close()


def get_pressure_field(limit=10) -> list[dict]:
    """Get articles with pressure/stabilization vectors."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT slug, title, game_type, narrative_energy, pressure_score, stabilization_score,
                   pressure_vector, stabilization_vector, phase_shift_risk, created
            FROM articles
            WHERE pressure_score > 0
            ORDER BY (pressure_score - stabilization_score) DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_expiring_narratives(limit=10) -> list[dict]:
    """Get articles sorted by half-life (shortest first)."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT slug, title, half_life, narrative_energy, liquidity_score,
                   meme_portability, elite_utility, symbolic_density, created
            FROM articles
            WHERE half_life IS NOT NULL AND half_life != ''
            ORDER BY
                CASE
                    WHEN half_life LIKE '%h' THEN CAST(REPLACE(half_life, 'h', '') AS REAL)
                    WHEN half_life LIKE '%d' THEN CAST(REPLACE(half_life, 'd', '') AS REAL) * 24
                    WHEN half_life LIKE '%w' THEN CAST(REPLACE(half_life, 'w', '') AS REAL) * 168
                    ELSE 999
                END ASC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_liquid_narratives(limit=10) -> list[dict]:
    """Get articles sorted by narrative liquidity (highest first)."""
    db = _get_articles_db()
    try:
        rows = db.execute(
            "SELECT slug, title, liquidity_score, cheap_narrative, expensive_narrative, created FROM articles WHERE liquidity_score > 0 ORDER BY liquidity_score DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


_REGION_CASE = """CASE source
    WHEN 'Google News Cairns' THEN 'local'
    WHEN 'Google News FNQ' THEN 'local'
    WHEN 'Cairns News' THEN 'local'
    WHEN 'Google News Queensland' THEN 'regional'
    WHEN 'Guardian Queensland' THEN 'regional'
    WHEN 'Brisbane Times' THEN 'regional'
    WHEN 'ABC News (AU)' THEN 'australia'
    WHEN 'ABC Just In' THEN 'australia'
    WHEN 'Guardian Australia' THEN 'australia'
    WHEN 'SBS News' THEN 'australia'
    ELSE 'international'
END"""


def get_tomorrows_paper(limit=20, region=None) -> list[dict]:
    """Get articles sorted by composite importance score for the newspaper view."""
    db = _get_articles_db()
    try:
        query = f"""
            SELECT *,
                {_REGION_CASE} AS region,
                (narrative_energy * 0.4) +
                ((pressure_score - stabilization_score + 1.0) / 2.0 * 0.3) +
                (CASE phase_shift_risk
                    WHEN 'high' THEN 1.0
                    WHEN 'medium' THEN 0.6
                    WHEN 'low' THEN 0.3
                    ELSE 0.0 END * 0.2) +
                (liquidity_score * 0.1) AS importance
            FROM articles
            WHERE created >= datetime('now', '-24 hours')
        """
        params = []
        if region:
            # Subquery filter using the same CASE logic
            query += f" AND {_REGION_CASE} = ?"
            params.append(region)
        query += " ORDER BY importance DESC LIMIT ?"
        params.append(limit)

        rows = db.execute(query, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["actors"] = get_actors_for(d["slug"])
            results.append(d)
        return results
    finally:
        db.close()


def get_tomorrows_paper_sections(limit_per_section=8) -> dict[str, list[dict]]:
    """Get articles grouped by region for the multi-page newspaper."""
    return {
        "local": get_tomorrows_paper(limit=limit_per_section, region="local"),
        "regional": get_tomorrows_paper(limit=limit_per_section, region="regional"),
        "australia": get_tomorrows_paper(limit=limit_per_section, region="australia"),
        "international": get_tomorrows_paper(limit=limit_per_section, region="international"),
    }


def get_day_after_predictions(limit=20) -> list[dict]:
    """Get articles ranked by composite prediction_score for 48h forecast."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT *,
                (pressure_score * 0.30) +
                ((1.0 - stabilization_score) * 0.15) +
                (CASE phase_shift_risk
                    WHEN 'high' THEN 1.0
                    WHEN 'medium' THEN 0.6
                    WHEN 'low' THEN 0.3
                    ELSE 0.0 END * 0.25) +
                (narrative_energy * 0.20) +
                (reflexivity_risk * 0.10) AS prediction_score
            FROM articles
            WHERE created >= datetime('now', '-48 hours')
            ORDER BY prediction_score DESC
            LIMIT ?
        """, (limit,)).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["actors"] = get_actors_for(d["slug"])
            results.append(d)
        return results
    finally:
        db.close()


def get_pressure_map(limit=20) -> list[dict]:
    """Get articles by net pressure (pressure - stabilization), 48h window."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT *, (pressure_score - stabilization_score) AS net_pressure
            FROM articles
            WHERE created >= datetime('now', '-48 hours')
                AND (pressure_score > 0 OR stabilization_score > 0)
            ORDER BY net_pressure DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_polymarket_articles(limit=15) -> list[dict]:
    """Get Polymarket prediction market articles."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT * FROM articles
            WHERE source LIKE 'Polymarket%'
            ORDER BY created DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_wild_cards(limit=8) -> list[dict]:
    """Get articles with high reflexivity_risk AND escalation triggers present."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT * FROM articles
            WHERE reflexivity_risk >= 0.6
                AND escalation_triggers IS NOT NULL AND escalation_triggers != ''
            ORDER BY reflexivity_risk DESC, narrative_energy DESC
            LIMIT ?
        """, (limit,)).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["actors"] = get_actors_for(d["slug"])
            results.append(d)
        return results
    finally:
        db.close()


def get_cheap_vs_expensive(limit=10) -> list[dict]:
    """Get articles with both cheap and expensive narratives."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT * FROM articles
            WHERE cheap_narrative IS NOT NULL AND cheap_narrative != ''
                AND expensive_narrative IS NOT NULL AND expensive_narrative != ''
            ORDER BY liquidity_score DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_future_forecasts(limit=20) -> list[dict]:
    """Get articles ranked by future_score for >72h to 6-month horizon.

    future_score weights persistence (half_life), phase shift risk,
    elite utility, meme portability, symbolic density, and reflexivity.
    """
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT *,
                (CASE
                    WHEN half_life LIKE '%w' THEN CAST(REPLACE(half_life, 'w', '') AS REAL)
                    WHEN half_life LIKE '%d' THEN CAST(REPLACE(half_life, 'd', '') AS REAL) / 7.0
                    WHEN half_life LIKE '%h' THEN CAST(REPLACE(half_life, 'h', '') AS REAL) / 168.0
                    ELSE 0.0 END * 0.25) +
                (CASE phase_shift_risk
                    WHEN 'high' THEN 1.0
                    WHEN 'medium' THEN 0.6
                    WHEN 'low' THEN 0.3
                    ELSE 0.0 END * 0.20) +
                (elite_utility * 0.20) +
                (meme_portability * 0.15) +
                (symbolic_density * 0.10) +
                (reflexivity_risk * 0.10) AS future_score
            FROM articles
            WHERE created >= datetime('now', '-7 days')
            ORDER BY future_score DESC
            LIMIT ?
        """, (limit,)).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["actors"] = get_actors_for(d["slug"])
            results.append(d)
        return results
    finally:
        db.close()


def get_phase_shifts(limit=15) -> list[dict]:
    """Get articles with equilibrium shifts or high phase_shift_risk."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT * FROM articles
            WHERE (equilibrium_shift IS NOT NULL AND equilibrium_shift != 'none')
                OR phase_shift_risk = 'high'
            ORDER BY
                CASE equilibrium_shift WHEN 'major' THEN 3 WHEN 'moderate' THEN 2 ELSE 1 END DESC,
                narrative_energy DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_half_life_ranked(limit=15) -> list[dict]:
    """Get articles with longest half-lives (most persistent narratives)."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT slug, title, half_life, narrative_energy, liquidity_score,
                   meme_portability, elite_utility, symbolic_density,
                   game_type, created
            FROM articles
            WHERE half_life IS NOT NULL AND half_life != ''
            ORDER BY
                CASE
                    WHEN half_life LIKE '%w' THEN CAST(REPLACE(half_life, 'w', '') AS REAL)
                    WHEN half_life LIKE '%d' THEN CAST(REPLACE(half_life, 'd', '') AS REAL) / 7.0
                    WHEN half_life LIKE '%h' THEN CAST(REPLACE(half_life, 'h', '') AS REAL) / 168.0
                    ELSE 0
                END DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_mythology_forecasts(limit=15) -> list[dict]:
    """Get articles with mythology signals for long-term cultural forecasting."""
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT a.slug, a.title, a.narrative_energy, a.narrative_arc,
                   a.symbolic_density, a.elite_utility, a.created,
                   m.archetype, m.signals, m.cultural_function, m.power_function
            FROM article_mythology m
            JOIN articles a ON m.article_slug = a.slug
            ORDER BY a.symbolic_density DESC, a.narrative_energy DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


def get_game_type_distribution() -> list[dict]:
    """Get article counts by game type."""
    db = _get_articles_db()
    try:
        rows = db.execute(
            "SELECT game_type, COUNT(*) as cnt FROM articles WHERE game_type != '' GROUP BY game_type ORDER BY cnt DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


# --- Predictions (Tomorrow's Paper generated articles) ---

def init_predictions_db():
    """Create predictions table if not exists."""
    db = _get_articles_db()
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_slug TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT,
                predicted_claims TEXT,
                confidence TEXT DEFAULT 'medium',
                region TEXT,
                generated_at TEXT NOT NULL,
                target_cycle TEXT,
                importance REAL DEFAULT 0.5,
                game_type TEXT,
                actors TEXT,
                source_title TEXT,
                source_forecast TEXT,
                scored INTEGER DEFAULT 0,
                accuracy_score REAL,
                accuracy_detail TEXT,
                matching_slugs TEXT,
                scored_at TEXT
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_pred_scored ON predictions(scored)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_pred_cycle ON predictions(target_cycle)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_pred_region ON predictions(region)")
        db.commit()
    finally:
        db.close()


def upsert_prediction(data: dict) -> int:
    """Insert a prediction. Returns the row id."""
    import json as _json
    db = _get_articles_db()
    try:
        predicted_claims = data.get("predicted_claims", [])
        if isinstance(predicted_claims, list):
            predicted_claims = _json.dumps(predicted_claims)
        actors = data.get("actors", [])
        if isinstance(actors, list):
            actors = _json.dumps(actors)

        cursor = db.execute("""
            INSERT INTO predictions (source_slug, title, body, predicted_claims, confidence,
                region, generated_at, target_cycle, importance, game_type, actors,
                source_title, source_forecast)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["source_slug"], data["title"], data.get("body", ""),
            predicted_claims, data.get("confidence", "medium"),
            data.get("region"), data["generated_at"], data.get("target_cycle"),
            data.get("importance", 0.5), data.get("game_type"),
            actors, data.get("source_title", ""), data.get("source_forecast", ""),
        ))
        db.commit()
        return cursor.lastrowid
    finally:
        db.close()


def update_prediction_score(pred_id: int, score: float, detail: str,
                            matching_slugs: list, scored_at: str):
    """Update accuracy scoring for a prediction."""
    import json as _json
    db = _get_articles_db()
    try:
        db.execute("""
            UPDATE predictions SET scored = 1, accuracy_score = ?,
                accuracy_detail = ?, matching_slugs = ?, scored_at = ?
            WHERE id = ?
        """, (score, detail, _json.dumps(matching_slugs), scored_at, pred_id))
        db.commit()
    finally:
        db.close()


def get_predictions(limit=20, region=None, cycle=None) -> list[dict]:
    """Get generated predictions for display, enriched as article-like dicts."""
    import json as _json
    db = _get_articles_db()
    try:
        query = "SELECT * FROM predictions WHERE 1=1"
        params = []
        if region:
            query += " AND region = ?"
            params.append(region)
        if cycle:
            query += " AND target_cycle = ?"
            params.append(cycle)
        query += " ORDER BY importance DESC, generated_at DESC LIMIT ?"
        params.append(limit)

        rows = db.execute(query, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            # Parse JSON fields
            actors_raw = d.get("actors", "[]")
            d["actors"] = _json.loads(actors_raw) if isinstance(actors_raw, str) else actors_raw
            claims_raw = d.get("predicted_claims", "[]")
            d["predicted_claims"] = _json.loads(claims_raw) if isinstance(claims_raw, str) else claims_raw

            # Enrich to look like articles for the template macro
            d["slug"] = f"pred-{d['id']}"
            d["hitchhiker_summary"] = (d.get("body") or "")[:300]
            d["source"] = d.get("region", "international")
            d["created"] = d.get("generated_at", "")
            d["forecast"] = d.get("source_forecast", "")
            d["narrative_energy"] = d.get("importance", 0.5)
            d["pressure_score"] = 0.0
            d["stabilization_score"] = 0.0
            d["liquidity_score"] = 0.0
            d["phase_shift_risk"] = ""
            d["is_prediction"] = True

            # Parse accuracy_detail if scored
            if d.get("scored") and d.get("accuracy_detail"):
                try:
                    d["accuracy_detail"] = _json.loads(d["accuracy_detail"])
                except (ValueError, TypeError):
                    pass
            if d.get("matching_slugs"):
                try:
                    d["matching_slugs"] = _json.loads(d["matching_slugs"])
                except (ValueError, TypeError):
                    pass

            results.append(d)
        return results
    finally:
        db.close()


def get_predictions_by_section(cycle=None, limit_per_section=8) -> dict[str, list[dict]]:
    """Get predictions grouped by region."""
    return {
        "local": get_predictions(limit=limit_per_section, region="local", cycle=cycle),
        "regional": get_predictions(limit=limit_per_section, region="regional", cycle=cycle),
        "australia": get_predictions(limit=limit_per_section, region="australia", cycle=cycle),
        "international": get_predictions(limit=limit_per_section, region="international", cycle=cycle),
    }


def get_unscored_predictions(limit=50) -> list[dict]:
    """Get predictions that haven't been accuracy-scored yet."""
    import json as _json
    db = _get_articles_db()
    try:
        rows = db.execute("""
            SELECT * FROM predictions WHERE scored = 0
            ORDER BY generated_at ASC LIMIT ?
        """, (limit,)).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            claims_raw = d.get("predicted_claims", "[]")
            d["predicted_claims"] = _json.loads(claims_raw) if isinstance(claims_raw, str) else claims_raw
            actors_raw = d.get("actors", "[]")
            d["actors"] = _json.loads(actors_raw) if isinstance(actors_raw, str) else actors_raw
            results.append(d)
        return results
    finally:
        db.close()


def get_prediction_accuracy_stats() -> dict:
    """Aggregate accuracy stats for the Track Record sidebar."""
    db = _get_articles_db()
    try:
        total = db.execute("SELECT COUNT(*) as cnt FROM predictions").fetchone()["cnt"]
        scored = db.execute("SELECT COUNT(*) as cnt FROM predictions WHERE scored = 1").fetchone()["cnt"]

        avg_score = 0.0
        if scored > 0:
            row = db.execute("SELECT AVG(accuracy_score) as avg FROM predictions WHERE scored = 1").fetchone()
            avg_score = round(row["avg"], 2) if row["avg"] else 0.0

        # Recent scored predictions
        recent_rows = db.execute("""
            SELECT title, accuracy_score, generated_at, confidence
            FROM predictions WHERE scored = 1
            ORDER BY scored_at DESC LIMIT 10
        """).fetchall()
        recent = [dict(r) for r in recent_rows]

        return {
            "total": total,
            "scored": scored,
            "avg_score": avg_score,
            "recent": recent,
        }
    finally:
        db.close()
