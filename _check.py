import sqlite3
db = sqlite3.connect('/data/articles.db')
db.row_factory = sqlite3.Row

cols = [r[1] for r in db.execute("PRAGMA table_info(articles)").fetchall()]
new_cols = ["cognitive_bias_score","signal_type","signal_credibility","deception_probability",
            "game_family","move_type","strategy_detected","cooperation_level",
            "cascade_risk","independent_sources","strategy_type","strategy_fitness","predicted_next_cycle"]
print("=== Column Check ===")
for c in new_cols:
    print(f"  {c}: {'OK' if c in cols else 'MISSING'}")

tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
new_tables = ["belief_states","article_biases","actor_profiles","actor_positions",
              "game_instances","game_moves","narrative_strategies","game_dependencies"]
print("=== Table Check ===")
for t in new_tables:
    print(f"  {t}: {'OK' if t in tables else 'MISSING'}")

print("=== Latest Article Data ===")
rows = db.execute(
    "SELECT slug, signal_type, signal_credibility, deception_probability, "
    "game_family, move_type, cascade_risk, independent_sources, "
    "strategy_type, strategy_fitness, cognitive_bias_score "
    "FROM articles WHERE created >= datetime('now','-1 hour') "
    "ORDER BY created DESC LIMIT 3"
).fetchall()
for r in rows:
    d = dict(r)
    print(f"  {d['slug']}")
    print(f"    signal: type={d['signal_type']} cred={d['signal_credibility']} deception={d['deception_probability']}")
    print(f"    game: family={d['game_family']} move={d['move_type']} cascade_risk={d['cascade_risk']}")
    print(f"    fitness: type={d['strategy_type']} score={d['strategy_fitness']} bias={d['cognitive_bias_score']}")

print("=== New Table Row Counts ===")
for tbl in ["belief_states","article_biases","actor_positions","game_instances","narrative_strategies"]:
    try:
        cnt = db.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {cnt} rows")
    except Exception as e:
        print(f"  {tbl}: ERROR - {e}")

if db.execute("SELECT COUNT(*) FROM belief_states").fetchone()[0] > 0:
    print("=== Sample Beliefs ===")
    for r in db.execute("SELECT claim_text, prior, posterior, evidence_strength FROM belief_states LIMIT 3").fetchall():
        d = dict(r)
        print(f"  prior={d['prior']:.2f} post={d['posterior']:.2f} str={d['evidence_strength']}: {d['claim_text'][:60]}")

if db.execute("SELECT COUNT(*) FROM article_biases").fetchone()[0] > 0:
    print("=== Sample Biases ===")
    for r in db.execute("SELECT article_slug, bias_type, severity FROM article_biases LIMIT 3").fetchall():
        d = dict(r)
        print(f"  {d['article_slug'][:30]}: {d['bias_type']} (severity={d['severity']})")

db.close()
