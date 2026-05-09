from __future__ import annotations
import os
import re
import sqlite3
import json
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify
import base
import config

news_bp = Blueprint("news", __name__)

RSSHUB_URL = os.environ.get("RSSHUB_URL", "http://192.168.0.33:1200")

DEFAULT_FEEDS = [
    "/rsshub/topics/popular",
    "/bbc/world",
    "/reuters/world",
    "/theintercept/articles",
]


def _get_news_db() -> sqlite3.Connection:
    db_path = os.path.join(config.DATA_DIR, "news.db")
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA journal_mode=WAL")
    db.row_factory = sqlite3.Row
    return db


def init_news_db():
    db = _get_news_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source TEXT,
            url TEXT,
            description TEXT,
            fetched_at TEXT NOT NULL,
            matched_conspiracies TEXT DEFAULT '[]',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_news_fetched ON articles(fetched_at)")
    db.commit()
    db.close()


def _match_conspiracies(title: str, description: str = "") -> list[str]:
    text = f"{title} {description}".lower()
    entries = base.list_entries(domain="conspiracy")
    matched = []
    for e in entries:
        title_lower = e["title"].lower()
        if title_lower in text:
            matched.append(e["slug"])
            continue
        words = re.findall(r"[a-z]{3,}", title_lower)
        significant = [w for w in words if w not in ("the", "and", "for", "that", "with", "from", "this", "are", "was", "has", "not", "but", "its", "all", "can", "who", "out")]
        if len(significant) >= 2:
            overlap = sum(1 for w in significant if w in text)
            if overlap >= min(3, len(significant)):
                matched.append(e["slug"])
    return matched[:5]


def fetch_feeds():
    import httpx
    init_news_db()
    db = _get_news_db()

    feeds_str = os.environ.get("NEWS_FEEDS", "")
    feeds = [f.strip() for f in feeds_str.split(",") if f.strip()] if feeds_str else DEFAULT_FEEDS

    total_new = 0
    for feed_path in feeds:
        url = f"{RSSHUB_URL}{feed_path}"
        try:
            resp = httpx.get(url, timeout=15, follow_redirects=True)
            if resp.status_code != 200:
                continue
            content_type = resp.headers.get("content-type", "")
            if "json" in content_type or feed_path.endswith("?format=json"):
                data = resp.json()
                items = data.get("items", data.get("data", []))
                for item in items:
                    title = item.get("title", "")
                    link = item.get("url", item.get("link", ""))
                    desc = item.get("description", item.get("summary", ""))
                    source = item.get("author", item.get("source", ""))
                    if not title:
                        continue
                    existing = db.execute("SELECT id FROM articles WHERE url = ?", (link,)).fetchone()
                    if existing:
                        continue
                    matched = _match_conspiracies(title, desc)
                    now = datetime.now(timezone.utc).isoformat()
                    db.execute(
                        "INSERT INTO articles (title, source, url, description, fetched_at, matched_conspiracies) VALUES (?, ?, ?, ?, ?, ?)",
                        (title, source, link, desc, now, json.dumps(matched)),
                    )
                    total_new += 1
            else:
                items = re.findall(r"<item>(.*?)</item>", resp.text, re.DOTALL)
                for item_xml in items:
                    title_m = re.search(r"<title>(?:<![CDATA[)?(.*?)(?:]]>)?</title>", item_xml)
                    link_m = re.search(r"<link>(?:<![CDATA[)?(.*?)(?:]]>)?</link>", item_xml)
                    desc_m = re.search(r"<description>(?:<![CDATA[)?(.*?)(?:]]>)?</description>", item_xml, re.DOTALL)
                    if not title_m:
                        continue
                    title = title_m.group(1).strip()
                    link = link_m.group(1).strip() if link_m else ""
                    desc = desc_m.group(1).strip() if desc_m else ""
                    if not title:
                        continue
                    existing = db.execute("SELECT id FROM articles WHERE url = ?", (link,)).fetchone()
                    if existing:
                        continue
                    matched = _match_conspiracies(title, desc)
                    now = datetime.now(timezone.utc).isoformat()
                    db.execute(
                        "INSERT INTO articles (title, source, url, description, fetched_at, matched_conspiracies) VALUES (?, ?, ?, ?, ?, ?)",
                        (title, "", link, desc, now, json.dumps(matched)),
                    )
                    total_new += 1
        except Exception:
            continue

    db.commit()
    db.close()
    return total_new


@news_bp.route("/news")
def news_home():
    init_news_db()
    db = _get_news_db()

    conspiracy_filter = request.args.get("conspiracy")
    page = request.args.get("page", 1, type=int)
    per_page = 30
    offset = (page - 1) * per_page

    if conspiracy_filter:
        rows = db.execute(
            "SELECT * FROM articles WHERE matched_conspiracies LIKE ? ORDER BY fetched_at DESC LIMIT ? OFFSET ?",
            (f'%"{conspiracy_filter}"%', per_page, offset),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM articles ORDER BY fetched_at DESC LIMIT ? OFFSET ?",
            (per_page, offset),
        ).fetchall()

    articles = []
    for r in rows:
        articles.append({
            "id": r["id"],
            "title": r["title"],
            "source": r["source"],
            "url": r["url"],
            "description": r["description"],
            "fetched_at": r["fetched_at"],
            "matched_conspiracies": json.loads(r["matched_conspiracies"]),
        })

    db.close()

    conspiracy_entries = base.list_entries(domain="conspiracy")
    matched_slugs = set()
    for a in articles:
        matched_slugs.update(a["matched_conspiracies"])

    return render_template("news.html",
        articles=articles,
        conspiracy_entries=conspiracy_entries,
        matched_slugs=matched_slugs,
        conspiracy_filter=conspiracy_filter,
        page=page,
    )


@news_bp.route("/news/refresh")
def news_refresh():
    total = fetch_feeds()
    return jsonify({"new_articles": total})
