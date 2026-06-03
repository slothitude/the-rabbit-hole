"""
Rabbit Hole Reporter v3 — Pure consumer of SearchV2 RSS API.
Fetches articles from SearchV2, analyzes with LLM, publishes to GitHub Pages.
Runs on Lappy where everything is local (SearchV2, Ollama, Alphabetty).
"""

import requests
import json
import re
import time
import hashlib
import os
import sys
import io
import subprocess
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Force UTF-8 on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# --- Config via env vars ---
# Everything is local on Lappy
SEARCHV2_URL = os.environ.get("RABBIT_SEARCHV2_URL", "http://localhost:7710")
SEARCHV2_KEY = os.environ.get("RABBIT_SEARCHV2_KEY", "").strip()

OLLAMA_BASE = os.environ.get("RABBIT_OLLAMA_BASE", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("RABBIT_OLLAMA_MODEL", "qwen3.5:4b")
OLLAMA_META_MODEL = os.environ.get("RABBIT_OLLAMA_META_MODEL", "qwen3.5:4b")
OLLAMA_FB_MODEL = os.environ.get("RABBIT_OLLAMA_FB_MODEL", "qwen3.5:0.8b")

ALPHABETTY_URL = os.environ.get("RABBIT_ALPHABETTY_URL", "http://localhost:7700")
ALPHABETTY_TOKEN = None

REPO_DIR = os.environ.get("RABBIT_REPO_DIR", r"D:\dev\the-rabbit-hole")

LOG_FILE = os.path.join(os.path.dirname(__file__), "rabbit_reporter_v3.log")

logging.basicConfig(
    filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("rabbit_reporter_v3")


# --- SearchV2 helpers ---

def _sv2_headers():
    h = {"Content-Type": "application/json"}
    if SEARCHV2_KEY:
        h["Authorization"] = f"Bearer {SEARCHV2_KEY}"
    return h


def _sv2_get(path, params=None):
    try:
        resp = requests.get(f"{SEARCHV2_URL}{path}", params=params,
                           headers=_sv2_headers(), timeout=30)
        if resp.status_code == 200:
            return resp.json()
        log.warning("SearchV2 GET %s returned %d", path, resp.status_code)
    except Exception as e:
        log.warning("SearchV2 GET %s failed: %s", path, e)
    return {}


def _sv2_retrieve(query, limit=5, include_belief=True):
    try:
        resp = requests.post(
            f"{SEARCHV2_URL}/api/retrieve",
            json={"query": query[:200], "limit": limit, "use_semantic": True, "include_belief": include_belief},
            headers=_sv2_headers(), timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        log.warning("SearchV2 retrieve failed: %s", e)
    return {}


def _sv2_ingest(query, topic=None, max_urls=1):
    try:
        resp = requests.post(
            f"{SEARCHV2_URL}/api/ingest",
            json={"query": query[:200], "max_urls": max_urls, "classify": False,
                  "index_embeddings": False, "topic": topic},
            headers=_sv2_headers(), timeout=120,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        log.warning("SearchV2 ingest failed: %s", e)
    return {}


def _match_entities_via_searchv2(title, description=""):
    query = f"{title} {description}"[:200]
    result = _sv2_retrieve(query, limit=5, include_belief=True)

    entities = []
    claims = result.get("claims", [])
    seen = set()
    for claim in claims[:5]:
        entity_name = claim.get("entity", claim.get("entity_name", ""))
        if entity_name and entity_name not in seen:
            seen.add(entity_name)
            entities.append({
                "name": entity_name,
                "confidence": claim.get("effective_confidence", claim.get("confidence", 0.5)),
                "disputed": claim.get("disputed", False),
            })

    top_entities = result.get("entities", [])
    for ent in top_entities[:3]:
        name = ent.get("name", "")
        if name and name not in seen:
            seen.add(name)
            entities.append({"name": name, "confidence": ent.get("confidence", 0.5), "disputed": False})

    return entities, result


def _build_kg_context(entities):
    if not entities:
        return ""
    parts = []
    for e in entities[:5]:
        conf = e.get("confidence", 0.5)
        disp = " [DISPUTED]" if e.get("disputed") else ""
        parts.append(f"- {e['name']} (confidence: {conf:.2f}{disp})")
    return "Knowledge Graph Context:\n" + "\n".join(parts)


# --- LLM calls ---

def _call_llm(prompt, model=None, timeout=120):
    model = model or OLLAMA_MODEL
    base_url = f"{OLLAMA_BASE}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {"num_predict": 4096},
    }
    headers = {"Content-Type": "application/json"}

    for attempt in range(3):
        try:
            resp = requests.post(base_url, json=payload, headers=headers, timeout=timeout)
            if resp.status_code == 429:
                time.sleep(30 * (attempt + 1))
                continue
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "")
        except requests.exceptions.Timeout:
            time.sleep(5)
        except Exception as e:
            time.sleep(5)
    return "ANALYSIS FAILED"


def _get_alphabetty_token():
    global ALPHABETTY_TOKEN
    if ALPHABETTY_TOKEN:
        return ALPHABETTY_TOKEN
    try:
        resp = requests.post(f"{ALPHABETTY_URL}/api/auth/login", json={
            "username": "demo", "password": "demo"
        }, timeout=10)
        if resp.status_code == 200:
            ALPHABETTY_TOKEN = resp.json().get("access_token", "")
    except Exception as e:
        log.warning("Alphabetty auth failed: %s", e)
    return ALPHABETTY_TOKEN


def _call_llm_alphabetty(prompt):
    token = _get_alphabetty_token()
    if not token:
        return "ANALYSIS FAILED"
    try:
        resp = requests.post(
            f"{ALPHABETTY_URL}/api/chat",
            json={"query": prompt, "mode": "detailed", "search_enabled": False},
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
        if resp.status_code == 200:
            return resp.json().get("response", resp.json().get("message", ""))
    except Exception as e:
        print(f"    (Alphabetty fallback failed: {e})", flush=True)
    return "ANALYSIS FAILED"


# --- Prompts ---

ANALYSIS_PROMPT = """You are a media analyst for "The Rabbit Hole" — a news analysis system that maps narratives, bias, and power structures behind world events.

Analyze this article. Output ONLY these fields:

SUBJECT: [one category: Politics, Economy, Technology, Science, Health, Climate, Conflict, Crime, Sport, Culture, Infrastructure, Australia, Other]
SUMMARY:
- [factual bullet point]
- [factual bullet point]
- [factual bullet point]
BIAS_TYPE: [left-leaning / right-leaning / neutral / corporate / nationalist / sensationalist / none detected]
NARRATIVE: [what conclusion is the article pushing the reader toward?]
ENTITIES: [comma-separated key actors, orgs, countries]

{kg_context}

---

TITLE: {title}
SOURCE: {source}
TEXT: {text}
"""

META_ANALYSIS_PROMPT = """You are a newspaper editor writing a cross-article analysis section. Given these article summaries, identify patterns.

ARTICLES:
{article_summaries}

{contradictions}

Output in this EXACT format:

NARRATIVE_TRENDS:
- [trend description]

RECURRING_ACTORS:
- [actor name] (mentioned in N stories)

CONTRADICTIONS:
- [description of contradiction between sources or claims]

PREDICTIONS_6H:
- [what likely happens in the next 6 hours based on these stories]
"""


# --- Parsing ---

def parse_single_analysis(raw):
    result = {
        "subject": "Other", "summary": [], "bias_type": "unknown",
        "narrative": "", "entities": [],
    }
    lines = raw.strip().split("\n")
    current_section = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("SUBJECT:"):
            result["subject"] = line.split(":", 1)[1].strip()
            current_section = None
        elif upper.startswith("BIAS_TYPE:"):
            result["bias_type"] = line.split(":", 1)[1].strip()
            current_section = None
        elif upper.startswith("NARRATIVE:"):
            result["narrative"] = line.split(":", 1)[1].strip()
            current_section = "narrative"
        elif upper.startswith("ENTITIES:"):
            raw_ents = line.split(":", 1)[1].strip()
            result["entities"] = [e.strip() for e in raw_ents.split(",") if e.strip()]
            current_section = None
        elif upper == "SUMMARY:":
            current_section = "summary"
        elif line.startswith("- ") and current_section == "summary":
            result["summary"].append(line[2:].strip())
        elif not line.startswith("- ") and current_section == "narrative":
            result["narrative"] += " " + line
    if not result["summary"]:
        result["summary"] = ["(analysis parse incomplete)"]
    return result


def parse_meta_analysis(raw):
    sections = {"narrative_trends": [], "recurring_actors": [], "contradictions": [], "predictions_6h": []}
    current_section = None
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("NARRATIVE_TRENDS:"):
            current_section = "narrative_trends"
        elif upper.startswith("RECURRING_ACTORS:"):
            current_section = "recurring_actors"
        elif upper.startswith("CONTRADICTIONS:"):
            current_section = "contradictions"
        elif upper.startswith("PREDICTIONS_6H:"):
            current_section = "predictions_6h"
        elif line.startswith("- ") and current_section:
            sections[current_section].append(line[2:].strip())
    return sections


# --- Analysis ---

def analyze_single(article, kg_context=""):
    text = article.get("full_text", "") or article.get("summary", "")
    text = text[:2000] if text else "Full text unavailable — summary only from RSS feed."

    prompt = ANALYSIS_PROMPT.format(
        title=article["title"],
        source=article["feed"],
        text=text,
        kg_context=kg_context,
    )

    # LLM ladder: 4b -> 0.8b -> Alphabetty (start with 4b, not 9b)
    raw = _call_llm(prompt, timeout=120)
    if raw == "ANALYSIS FAILED":
        print(f"    (4b failed, trying 0.8b fallback...)", flush=True)
        raw = _call_llm(prompt, model=OLLAMA_FB_MODEL, timeout=90)
    if raw == "ANALYSIS FAILED":
        print(f"    (Ollama failed, trying Alphabetty...)", flush=True)
        raw = _call_llm_alphabetty(prompt)
    return raw


# --- Newspaper ---

def _wikilink(text, entities):
    if not entities:
        return text
    for ent in sorted(entities, key=len, reverse=True):
        if ent in text and f"[[{ent}]]" not in text:
            text = text.replace(ent, f"[[{ent}]]")
    return text


def build_newspaper(analyses, meta, sources_count):
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%B %d, %Y")

    lines = []
    lines.append(f"# The Rabbit Hole — {date_str}")
    lines.append("")
    lines.append(f"*{len(analyses)} stories from {sources_count} sources | Generated {now.strftime('%H:%M')} UTC*")
    lines.append("")

    # Sort by KG connection count
    scored = [(len(a.get("matched_entities", [])), a) for a in analyses]
    scored.sort(key=lambda x: x[0], reverse=True)

    lines.append("## Front Page")
    lines.append("")
    for rank, (_, a) in enumerate(scored[:15], 1):
        ana = a["analysis"]
        bias = ana.get("bias_type", "unknown")
        entities = ana.get("entities", [])
        matched = a.get("matched_entities", [])

        lines.append(f"### {rank}. {a['title']}")
        lines.append(f"**Source:** {a['feed']} | **Bias:** {bias}")
        if matched:
            kg_names = ", ".join(e["name"] for e in matched[:3])
            lines.append(f"**KG Match:** {kg_names}")
        lines.append("")
        for point in ana.get("summary", [])[:3]:
            lines.append(f"- {_wikilink(point, entities)}")
        lines.append(f"**Narrative:** {ana.get('narrative', '')}")
        if entities:
            lines.append(f"**Entities:** {', '.join(entities[:8])}")
        lines.append("")
        lines.append("---")
        lines.append("")

    if meta:
        lines.append("## Meta-Analysis")
        lines.append("")
        if meta.get("narrative_trends"):
            lines.append("### Narrative Trends")
            for t in meta["narrative_trends"]:
                lines.append(f"- {t}")
            lines.append("")
        if meta.get("recurring_actors"):
            lines.append("### Recurring Actors")
            for a_name in meta["recurring_actors"][:10]:
                lines.append(f"- {a_name}")
            lines.append("")
        if meta.get("contradictions"):
            lines.append("### Contradictions")
            for c in meta["contradictions"]:
                lines.append(f"- {c}")
            lines.append("")
        if meta.get("predictions_6h"):
            lines.append("### 6-Hour Outlook")
            for p in meta["predictions_6h"]:
                lines.append(f"- {p}")
            lines.append("")

    lines.append("---")
    lines.append(f"*Auto-generated by Rabbit Hole Reporter v3. Powered by SearchV2.*")
    return "\n".join(lines)


# --- Git push ---

def git_push_newspaper(newspaper_md, slug):
    """Save newspaper to repo, commit, and push."""
    try:
        repo = Path(REPO_DIR)
        if not repo.is_dir():
            log.warning("Repo not found at %s", REPO_DIR)
            print(f"  Repo not found at {REPO_DIR}")
            return False

        filename = f"newspaper-{slug.replace('report-', '')}.md"
        filepath = repo / filename
        filepath.write_text(newspaper_md, encoding="utf-8")
        print(f"  Saved: {filepath}")

        # Git add, commit, push
        subprocess.run(["git", "add", filename], cwd=str(repo), check=True,
                      capture_output=True, text=True)
        subprocess.run(
            ["git", "commit", "-m", f"Add {filename}"],
            cwd=str(repo), check=True, capture_output=True, text=True,
        )
        subprocess.run(["git", "push"], cwd=str(repo), check=True,
                      capture_output=True, text=True, timeout=60)
        print(f"  Pushed to GitHub Pages")
        return True
    except subprocess.CalledProcessError as e:
        log.error("Git push failed: %s", e.stderr[:200] if e.stderr else str(e))
        print(f"  Git push failed: {e.stderr[:200] if e.stderr else e}")
        return False
    except Exception as e:
        log.error("Git push failed: %s", e)
        print(f"  Git push failed: {e}")
        return False


# --- Main pipeline ---

def run(test_mode=False):
    period_end = datetime.now(timezone.utc)
    print(f"=== Rabbit Hole Reporter v3 — {period_end.strftime('%Y-%m-%d %H:%M')} UTC ===\n")
    log.info("Starting v3 report run")

    # Step 1: Fetch articles from SearchV2 RSS API
    hours = 3 if test_mode else 6
    print(f"[1/5] Fetching articles from SearchV2 (last {hours}h)...")
    articles_data = _sv2_get("/api/articles", params={
        "hours": hours,
        "include_text": "true",
        "limit": 200,
    })

    articles = articles_data if isinstance(articles_data, list) else []
    if not articles:
        print("  No articles from SearchV2. Exiting.")
        return

    sources = set(a.get("feed", "?") for a in articles)
    print(f"  {len(articles)} articles from {len(sources)} sources")

    if test_mode:
        articles = articles[:3]
        print(f"  Test mode: {len(articles)} articles")

    # Step 2: Match entities via SearchV2 + ingest
    print(f"\n[2/5] Matching entities via SearchV2...")
    for i, a in enumerate(articles):
        matched, retrieve_result = _match_entities_via_searchv2(
            a["title"], f"{a.get('summary', '')} {a.get('full_text', '')[:300]}"
        )
        a["matched_entities"] = matched

        if matched:
            names = ", ".join(f"{e['name']}({e['confidence']:.2f})" for e in matched[:3])
            print(f"  [{i+1}/{len(articles)}] {a['title'][:50]}... -> {names}")
            # Ingest under best-matched entity
            _sv2_ingest(a["title"], topic=matched[0]["name"], max_urls=1)

    # Step 3: Per-article LLM analysis
    print(f"\n[3/5] Analyzing {len(articles)} articles...")
    FAILED_ANALYSIS = {
        "subject": "Other", "summary": ["(analysis failed)"],
        "bias_type": "unknown", "narrative": "", "entities": [],
    }

    def process_article(idx, article):
        kg_ctx = _build_kg_context(article.get("matched_entities", []))
        raw = analyze_single(article, kg_ctx)
        if raw == "ANALYSIS FAILED":
            return idx, {
                "title": article["title"], "feed": article["feed"],
                "url": article["url"], "analysis": FAILED_ANALYSIS,
                "matched_entities": article.get("matched_entities", []),
            }
        parsed = parse_single_analysis(raw)
        print(f"    {article['title'][:40]}... -> {parsed['subject']} (bias: {parsed['bias_type']})", flush=True)
        return idx, {
            "title": article["title"], "feed": article["feed"],
            "url": article["url"], "analysis": parsed,
            "matched_entities": article.get("matched_entities", []),
        }

    analyses = [None] * len(articles)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(process_article, i, a): i for i, a in enumerate(articles)}
        for future in as_completed(futures):
            try:
                idx, result = future.result()
                analyses[idx] = result
            except Exception as e:
                print(f"    Analysis error: {e}", flush=True)
    analyses = [a for a in analyses if a is not None]

    # Step 4: Meta-analysis
    meta = {}
    if analyses:
        print(f"\n[4/5] Running meta-analysis...")
        article_summaries = []
        for a in analyses:
            ana = a["analysis"]
            article_summaries.append(
                f"- [{ana['subject']}] {a['title'][:80]} (src: {a['feed']})\n"
                f"  Narrative: {ana['narrative'][:150]}\n"
                f"  Entities: {', '.join(ana['entities'][:5])}"
            )

        contradictions_ctx = ""
        belief_result = _sv2_retrieve("contradictions disputes claims", limit=5, include_belief=True)
        contra_claims = belief_result.get("claims", [])
        if contra_claims:
            contradictions_ctx = "Knowledge Graph Contradictions:\n"
            for c in contra_claims[:3]:
                contradictions_ctx += f"- {c.get('entity', '?')}: {c.get('key', '?')} (confidence: {c.get('effective_confidence', 0):.2f}, disputed: {c.get('disputed', False)})\n"

        meta_prompt = META_ANALYSIS_PROMPT.format(
            article_summaries="\n".join(article_summaries),
            contradictions=contradictions_ctx,
        )
        raw = _call_llm(meta_prompt, model=OLLAMA_META_MODEL, timeout=120)
        if raw == "ANALYSIS FAILED":
            raw = _call_llm(meta_prompt, model=OLLAMA_FB_MODEL, timeout=90)
        if raw != "ANALYSIS FAILED":
            meta = parse_meta_analysis(raw)
            print(f"    Trends: {len(meta.get('narrative_trends', []))}, Actors: {len(meta.get('recurring_actors', []))}")
        else:
            print("    Meta-analysis failed, skipping section")

    # Step 5: Build newspaper + git push
    print(f"\n[5/5] Building newspaper + pushing to GitHub Pages...")
    newspaper_md = build_newspaper(analyses, meta, len(sources))
    slug = f"report-{period_end.strftime('%Y-%m-%d-%H%M')}"

    ok = git_push_newspaper(newspaper_md, slug)

    kg_hits = sum(len(a.get("matched_entities", [])) for a in analyses)
    status = "OK" if ok else "PUSH FAILED"
    print(f"\n=== Done — {status} ({len(analyses)} articles, {kg_hits} KG matches) ===")
    log.info("Report v3 complete: %s (%d articles, %d KG hits)", status, len(analyses), kg_hits)


if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    run(test_mode=test_mode)
