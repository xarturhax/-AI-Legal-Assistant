from app import create_app
from app.db.migrate import upgrade


def main():
    import os
    import sys

    from waitress import serve

    app = create_app()
    with app.app_context():
        upgrade()
        from app.forum.recommendations import backfill_tags

        backfill_tags()
    if len(sys.argv) > 1 and sys.argv[1] == "db-upgrade":
        print("Миграции применены.")
        return
    if len(sys.argv) > 1 and sys.argv[1] == "refresh-news":
        import json

        from app.news.service import refresh_feeds

        with app.app_context():
            results = refresh_feeds(
                [url.strip() for url in app.config["NEWS_RSS_URLS"].split(",") if url.strip()]
            )
        print(json.dumps(results, ensure_ascii=False))
        return
    serve(
        app,
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "5000")),
        threads=8,
    )


if __name__ == "__main__":
    main()
