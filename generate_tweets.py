"""Generate tweet-style cheap/expensive narrative posts from Rabbit Hole predictions.

Pulls predictions from the DB via SSH, uses GLM-5.1 to craft sharp
cheap/expensive narrative pairs, and outputs them grouped by target date.

Usage:
    python generate_tweets.py                  # all recent predictions
    python generate_tweets.py --date 2026-05-10  # specific date
    python generate_tweets.py --limit 3         # top N per date
    python generate_tweets.py --raw             # skip LLM, use raw data
"""
from __future__ import annotations
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests

BASE = "http://192.168.0.33:5421"
AEST = timezone(timedelta(hours=10))

TWEET_TEMPLATE = """*The cheap narrative: {cheap}*

*The expensive narrative: {expensive}*

*You're being sold the cheap one.*

*— The Rabbit Hole | {date}*"""

LLM_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
LLM_KEY = "a63a2a7ee2d5431d929c776122e3b706.hzHjrJlnfPd7cYfj"

SYSTEM_PROMPT = """You are The Rabbit Hole. Write exactly TWO short sentences. Nothing else. No preamble.

CHEAP: [one short punchy sentence — the emotional tabloid headline the public is being sold]
EXPENSIVE: [one short sharp sentence — the real game theory truth beneath the surface]

RULES:
- Each sentence MUST be under 150 characters
- No bullet points, no markdown, no extra text
- Be cynical and sharp
- Cheap = what they want you to think
- Expensive = what's actually happening
- If cascade risk is high, the cheap narrative is likely herd-driven — call it out
- If signal credibility is low, the expensive narrative should expose the bluff
- If bias score is high, the cheap narrative is distorted — strip the framing
- Start with CHEAP: and EXPENSIVE:"""


def fetch_predictions(date_filter: str | None = None) -> list[dict]:
    """Fetch predictions via paramiko SSH to Lappy Docker container."""
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.0.33', username='aaron', password='T0b1@n7243')
    sftp = ssh.open_sftp()
    with sftp.open('/tmp/tweet_gen.py', 'w') as f:
        f.write("""import sys, sqlite3, json
sys.stdout.reconfigure(encoding='utf-8')
c = sqlite3.connect('/data/articles.db')
c.row_factory = sqlite3.Row
where = "WHERE p.target_cycle >= date('now', '-2 days')"
rows = c.execute(f'''
    SELECT p.target_cycle, p.title, p.body, p.confidence, p.source_title,
           p.importance, p.game_type, p.source_slug,
           a.signal_type, a.signal_credibility, a.deception_probability,
           a.cascade_risk, a.cognitive_bias_score, a.game_family,
           a.strategy_type, a.strategy_fitness
    FROM predictions p
    LEFT JOIN articles a ON p.source_slug = a.slug
    {where}
    ORDER BY p.target_cycle, p.importance DESC
''').fetchall()
result = []
for r in rows:
    result.append({
        'cycle': r['target_cycle'],
        'title': r['title'],
        'body': (r['body'] or '')[:600],
        'confidence': r['confidence'],
        'source': r['source_title'],
        'importance': r['importance'],
        'game_type': r['game_type'],
        'signal_type': r['signal_type'] or '',
        'signal_credibility': r['signal_credibility'] or 0,
        'deception_probability': r['deception_probability'] or 0,
        'cascade_risk': r['cascade_risk'] or 0,
        'cognitive_bias_score': r['cognitive_bias_score'] or 0,
        'game_family': r['game_family'] or '',
        'strategy_type': r['strategy_type'] or '',
        'strategy_fitness': r['strategy_fitness'] or 0,
    })
print(json.dumps(result, ensure_ascii=False))
""")
    sftp.close()
    stdin, stdout, stderr = ssh.exec_command('docker cp /tmp/tweet_gen.py the-rabbit-hole:/tmp/tweet_gen.py && docker exec the-rabbit-hole python3 /tmp/tweet_gen.py')
    data = stdout.read().decode('utf-8')
    ssh.close()
    preds = json.loads(data)
    if date_filter:
        preds = [p for p in preds if date_filter in p['cycle']]
    return preds


def generate_narrative_llm(title: str, body: str, intel: dict | None = None) -> tuple[str, str]:
    """Use GLM-5.1 to generate cheap/expensive narrative pair."""
    headers = {"Authorization": f"Bearer {LLM_KEY}", "Content-Type": "application/json"}

    intel_lines = ""
    if intel:
        parts = []
        if intel.get('signal_type'):
            parts.append(f"Signal: {intel['signal_type']} (credibility: {intel.get('signal_credibility', 0)*10:.0f}/10)")
        if intel.get('deception_probability'):
            parts.append(f"Deception probability: {intel['deception_probability']*100:.0f}%")
        if intel.get('cascade_risk'):
            parts.append(f"Cascade risk: {intel['cascade_risk']*10:.0f}/10")
        if intel.get('cognitive_bias_score'):
            parts.append(f"Source bias: {intel['cognitive_bias_score']*10:.0f}/10")
        if intel.get('game_family'):
            parts.append(f"Game: {intel['game_family']}")
        if intel.get('strategy_type'):
            parts.append(f"Narrative strategy: {intel['strategy_type']}")
        if parts:
            intel_lines = "\nINTEL:\n" + "\n".join(f"- {p}" for p in parts)

    prompt = f"""{SYSTEM_PROMPT}

Headline: {title}
Summary: {body[:300]}{intel_lines}"""

    try:
        r = requests.post(LLM_URL, headers=headers, json={
            "model": "glm-5.1",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 32768,
        }, timeout=60)
        r.raise_for_status()
        text = r.json()['choices'][0]['message']['content']

        cheap_m = re.search(r'CHEAP:\s*(.+?)(?:\n|EXPENSIVE:|$)', text, re.DOTALL)
        exp_m = re.search(r'EXPENSIVE:\s*(.+?)$', text, re.DOTALL)

        cheap = cheap_m.group(1).strip() if cheap_m else title.split('\n')[0].strip('# ')
        expensive = exp_m.group(1).strip() if exp_m else body.split('\n')[0].strip('* ')
        return cheap, expensive
    except Exception as e:
        print(f"  LLM error: {e}", file=sys.stderr)
        return title.split('\n')[0].strip('# '), body.split('\n')[0].strip('* ')


def cycle_to_date(cycle: str) -> str:
    """Convert '2026-05-10-ed1' to 'May 10, 2026'."""
    date_str = cycle.split('-ed')[0]
    d = datetime.strptime(date_str, '%Y-%m-%d')
    return d.strftime('%B %d, %Y').replace(' 0', ' ')


def format_tweets(predictions: list[dict], limit_per_date: int = 3, use_llm: bool = True) -> str:
    """Format predictions into tweet posts grouped by date."""
    by_date: dict[str, list[dict]] = {}
    for p in predictions:
        date_key = p['cycle'].split('-ed')[0]
        if date_key not in by_date:
            by_date[date_key] = []
        by_date[date_key].append(p)

    parts = []
    for date_key in sorted(by_date.keys()):
        preds = by_date[date_key][:limit_per_date]
        formatted_date = cycle_to_date(preds[0]['cycle'])

        parts.append(f"\n{formatted_date}\n")

        for i, p in enumerate(preds, 1):
            title = re.sub(r'^#+\s*', '', p['title']).strip()
            body = re.sub(r'\*+', '', p['body']).strip()
            body = re.sub(r'\n{2,}', '\n', body)

            if use_llm:
                cheap, expensive = generate_narrative_llm(title, body, intel=p)
            else:
                cheap = title
                expensive = body.split('\n')[0][:200]

            tweet = TWEET_TEMPLATE.format(cheap=cheap, expensive=expensive, date=formatted_date)
            parts.append(tweet)
            if i < len(preds):
                parts.append("")

    return '\n\n'.join(parts)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate Rabbit Hole tweets')
    parser.add_argument('--date', help='Specific date (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, default=3, help='Max predictions per date')
    parser.add_argument('--raw', action='store_true', help='Skip LLM, use raw data')
    parser.add_argument('--output', '-o', help='Output file path')
    args = parser.parse_args()

    print("Fetching predictions...", file=sys.stderr)
    predictions = fetch_predictions(date_filter=args.date)
    print(f"Found {len(predictions)} predictions", file=sys.stderr)

    if not predictions:
        print("No predictions found.")
        return

    tweets = format_tweets(predictions, limit_per_date=args.limit, use_llm=not args.raw)

    if args.output:
        Path(args.output).write_text(tweets, encoding='utf-8')
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(tweets)


if __name__ == "__main__":
    main()
