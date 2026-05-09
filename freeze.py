"""Snapshot the live Rabbit Hole site into static HTML for GitHub Pages."""
from __future__ import annotations
import os
import sys
import time
from pathlib import Path
import requests

BASE = os.environ.get("RABBIT_URL", "http://192.168.0.33:5421")
OUT = Path(os.environ.get("FREEZE_DIR", "_site"))

# Routes to snapshot
ROUTES: list[str] = [
    "/",
    "/paper",
    "/articles",
    "/timeline",
    "/actors",
    "/contradictions",
    "/forecast",
    "/mythology",
    "/energy",
    "/persistence",
    "/reflexivity",
    "/reports",
    "/reports/book",
    "/map",
    "/search",
    "/today",
    "/tomorrow",
    "/day-after-tomorrow",
    "/future",
]

# Tab variants for /paper
PAPER_TABS = ["today", "tomorrow", "day2", "future"]


def fetch(route: str, params: dict | None = None) -> str:
    url = BASE + route
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.text


def save(route: str, html: str):
    # Map routes to file paths
    if route == "/" or route == "":
        path = OUT / "index.html"
    elif route.endswith("/"):
        path = OUT / route.strip("/") / "index.html"
    else:
        # Save as .html file
        path = OUT / (route.strip("/") + ".html")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    print(f"  saved {path.relative_to(OUT)}")


def snapshot_entries():
    """Fetch entry pages from the API or sitemap."""
    try:
        r = requests.get(f"{BASE}/map", timeout=30)
        if r.status_code == 200:
            # Parse entry slugs from the map page
            import re
            slugs = re.findall(r'href="([^"]*?/entry/([^"]+))"', r.text)
            seen = set()
            for href, slug in slugs:
                if slug not in seen:
                    seen.add(slug)
                    try:
                        html = fetch(f"/entry/{slug}")
                        save(f"/entry/{slug}", html)
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"  skip entry/{slug}: {e}")
            print(f"  entries: {len(seen)} slugs")
    except Exception as e:
        print(f"  entries failed: {e}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Snapshotting {BASE} -> {OUT}")

    # Main routes
    for route in ROUTES:
        try:
            html = fetch(route)
            save(route, html)
        except Exception as e:
            print(f"  FAIL {route}: {e}")

    # Paper tab variants
    for tab in PAPER_TABS:
        try:
            html = fetch("/paper", params={"tab": tab})
            save(f"/paper-{tab}", html)
        except Exception as e:
            print(f"  FAIL /paper?tab={tab}: {e}")

    # Entry pages
    snapshot_entries()

    # Tier pages
    for t in range(1, 6):
        try:
            html = fetch(f"/tier/{t}")
            save(f"/tier/{t}", html)
        except Exception as e:
            print(f"  FAIL /tier/{t}: {e}")

    # Category pages
    for cat in ["conspiracy", "geopolitics", "technology", "finance", "society"]:
        try:
            html = fetch(f"/category/{cat}")
            save(f"/category/{cat}", html)
        except Exception as e:
            print(f"  FAIL /category/{cat}: {e}")

    print(f"\nDone. Static site in {OUT}/")


if __name__ == "__main__":
    main()
