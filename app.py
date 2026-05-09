from __future__ import annotations
from flask import Flask, request
import config
from base import init_db, init_search_db, init_articles_db, init_predictions_db, reindex


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["DATA_DIR"] = config.DATA_DIR

    # Init databases (shared with the-guide)
    init_db()
    init_search_db()
    init_articles_db()
    init_predictions_db()
    reindex()

    @app.context_processor
    def inject_prefix():
        prefix = request.headers.get("X-Forwarded-Prefix", "").rstrip("/")
        return {"prefix": prefix}

    # Register blueprints
    from routes.home import home_bp
    from routes.entry import entry_bp
    from routes.map import map_bp
    from routes.tier import tier_bp
    from routes.category import category_bp
    from routes.news import news_bp
    from routes.search import search_bp
    from routes.reports import reports_bp
    from routes.articles import articles_bp
    from routes.timeline import timeline_bp
    from routes.contradictions import contradictions_bp
    from routes.actors import actors_bp
    from routes.forecast import forecast_bp
    from routes.mythology import mythology_bp
    from routes.narrative_energy import energy_bp
    from routes.persistence import persistence_bp
    from routes.reflexivity import reflexivity_bp
    from routes.paper import paper_bp
    from routes.tomorrow import tomorrow_bp
    from routes.day_after import day_after_bp
    from routes.future import future_bp
    from routes.today import today_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(entry_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(tier_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(news_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(articles_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(contradictions_bp)
    app.register_blueprint(actors_bp)
    app.register_blueprint(forecast_bp)
    app.register_blueprint(mythology_bp)
    app.register_blueprint(energy_bp)
    app.register_blueprint(persistence_bp)
    app.register_blueprint(reflexivity_bp)
    app.register_blueprint(paper_bp)
    app.register_blueprint(today_bp)
    app.register_blueprint(tomorrow_bp)
    app.register_blueprint(day_after_bp)
    app.register_blueprint(future_bp)

    # Serve images from shared data dir
    import os
    from flask import send_from_directory

    @app.route("/data/images/<path:filename>")
    def serve_image(filename):
        return send_from_directory(config.IMAGES_DIR, filename)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=True)
