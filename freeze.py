"""Snapshot the Paper page into a fully standalone static HTML for GitHub Pages."""
from __future__ import annotations
import base64
import os
import re
from pathlib import Path
import requests

BASE = os.environ.get("RABBIT_URL", "http://192.168.0.33:5421")
OUT = Path(os.environ.get("FREEZE_DIR", "_site"))
SPLASH = Path(__file__).parent / "static" / "splash.jpg"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Snapshotting {BASE}/paper -> {OUT}")

    r = requests.get(f"{BASE}/paper", timeout=30)
    r.raise_for_status()
    html = r.text

    # Extract ALL <style> blocks from the paper page (base + paper CSS)
    styles = re.findall(r'<style>(.*?)</style>', html, re.DOTALL)
    all_css = "\n".join(styles)

    # Extract just the <main> content (no site header/nav/footer)
    main_content = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL)
    if not main_content:
        print("ERROR: Could not find <main> content")
        return
    content = main_content.group(1)

    # Rewrite all internal href="/..." to point to live site
    content = re.sub(r'href="/(?!/)', f'href="{BASE}/', content)

    # Extract JS from the page
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
    all_js = "\n".join(s for s in scripts if s.strip())

    # Base64-encode splash image for self-contained HTML
    splash_b64 = ""
    if SPLASH.exists():
        splash_b64 = base64.b64encode(SPLASH.read_bytes()).decode()
        print(f"  inlined splash image ({len(splash_b64)} bytes)")

    splash_css = """
    /* Splash screen */
    .splash {
        position: fixed; inset: 0; z-index: 9999;
        background: #0a0a0a;
        display: flex; align-items: center; justify-content: center;
        transition: opacity 0.8s ease-out;
    }
    .splash.fade-out { opacity: 0; pointer-events: none; }
    .splash img {
        max-width: 80vw; max-height: 80vh;
        object-fit: contain;
        animation: splashIn 1s ease-out;
    }
    @keyframes splashIn {
        0% { opacity: 0; transform: scale(0.95); }
        100% { opacity: 1; transform: scale(1); }
    }
    """

    splash_html = ""
    if splash_b64:
        splash_html = f"""
    <div class="splash" id="splash">
        <img src="data:image/jpeg;base64,{splash_b64}" alt="The Rabbit Hole">
    </div>
    <script>
    setTimeout(function() {{
        var s = document.getElementById('splash');
        if (s) {{ s.classList.add('fade-out'); setTimeout(function() {{ s.remove(); }}, 800); }}
    }}, 2500);
    </script>
    """

    # Build standalone page — no site chrome
    standalone = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Rabbit Hole — Tomorrow's Paper</title>
    <style>
{all_css}
{splash_css}
    </style>
</head>
<body>
{splash_html}
{content}
<script>
{all_js}
</script>
</body>
</html>"""

    (OUT / "index.html").write_text(standalone, encoding="utf-8")
    print(f"  saved index.html ({len(standalone)} bytes)")
    print(f"Done.")


if __name__ == "__main__":
    main()
