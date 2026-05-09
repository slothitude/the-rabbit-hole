import os

# Points to the SAME data directory as the-guide (shared entries + DB)
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
REPORTS_DIR = os.path.join(DATA_DIR, "entries")
ENTRIES_DIR = os.path.join(DATA_DIR, "entries")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
DB_PATH = os.path.join(DATA_DIR, "encyclopedia.db")
SEARCH_INDEX_DB = os.path.join(DATA_DIR, "search.db")
ARTICLES_DB = os.path.join(DATA_DIR, "articles.db")

RSSHUB_URL = os.environ.get("RSSHUB_URL", "http://127.0.0.1:1200")
RABBIT_INGEST_KEY = os.environ.get("RABBIT_INGEST_KEY", "rabbit-hole-2026-secret")
REPORTS_PER_PAGE = 20
