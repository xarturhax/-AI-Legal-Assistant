import json

import httpx
import pytest
from app.db.models import NewsCache, PostVote
from app.extensions import db
from app.news.service import MAX_FEED_BYTES, read_feed_entries, refresh_feeds
from app.test_module.routes import public_question
from test_accounts import register_and_login


def test_forum_ownership_votes_search(app):
    alice = register_and_login(app, "alice@example.test")
    bob = register_and_login(app, "bob@example.test")
    topic = alice.post(
        "/api/forum/topics", json={"title": "Вопрос об образовании", "body": "Обсуждение"}
    )
    assert topic.status_code == 201
    topic_id = topic.json["id"]
    post = alice.post("/api/forum/posts", json={"topic_id": topic_id, "body": "Личное мнение"})
    identifier = post.json["id"]
    assert bob.put(f"/api/forum/posts/{identifier}", json={"body": "подмена"}).status_code == 404
    assert bob.delete(f"/api/forum/posts/{identifier}", json={}).status_code == 404
    assert alice.post(f"/api/forum/posts/{identifier}/vote", json={"vote": 1}).status_code == 403
    for _ in range(2):
        assert bob.post(f"/api/forum/posts/{identifier}/vote", json={"vote": 1}).status_code == 200
    with app.app_context():
        assert len(db.session.execute(db.select(PostVote)).scalars().all()) == 1
    assert bob.get(f"/api/forum/topics/{topic_id}").json["posts"][0]["score"] == 1
    assert len(bob.get("/api/forum/search?term=образовании").json["items"]) == 1
    assert bob.get("/api/forum/search?term=' OR 1=1 --").json["items"] == []
    assert alice.delete(f"/api/forum/posts/{identifier}", json={}).status_code == 200
    assert bob.get(f"/api/forum/topics/{topic_id}").json["posts"] == []
    assert (
        app.test_client().post("/api/forum/topics", json={"title": "x", "body": "x"}).status_code
        == 401
    )


@pytest.mark.mock
def test_news_cache_survives_network_failure(app, monkeypatch):
    original = httpx.Client
    feed = b'<rss version="2.0"><channel><title>Test</title><item><title>News</title><link>https://example.test/news/1</link><description>Cached</description></item></channel></rss>'
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: original(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, content=feed)), **kw
        ),
    )
    with app.app_context():
        assert refresh_feeds(["https://example.test/rss"])[0]["status"] == "PASS"

    def fail(request):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(
        httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(fail), **kw)
    )
    with app.app_context():
        assert refresh_feeds(["https://example.test/rss"])[0]["status"] == "FAIL"
        assert db.session.execute(db.select(NewsCache)).scalar_one().title == "News"
    assert b"News" in app.test_client().get("/news").data

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: original(
            transport=httpx.MockTransport(
                lambda r: httpx.Response(200, content=b"x" * (MAX_FEED_BYTES + 1))
            ),
            **kw,
        ),
    )
    with app.app_context():
        result = refresh_feeds(["https://example.test/rss"])[0]
        assert result["status"] == "FAIL"
        assert result["detail"] == "В первых 8 МБ ленты нет полной записи"
        assert db.session.execute(db.select(NewsCache)).scalar_one().title == "News"


@pytest.mark.parametrize(
    ("header", "entry"),
    [
        (
            "<rss version='2.0'><channel><title>Test</title>",
            "<item><title>{i}</title><link>https://example.test/{i}</link></item>",
        ),
        (
            "<feed xmlns='http://www.w3.org/2005/Atom'><title>Test</title>",
            "<entry><title>{i}</title><link href='https://example.test/{i}'/></entry>",
        ),
    ],
)
def test_large_news_feed_stops_after_first_hundred_entries(header, entry):
    prefix = (header + "".join(entry.format(i=i) for i in range(101))).encode()
    prefix = prefix.ljust(65_536, b" ")

    class LongFeed(httpx.SyncByteStream):
        def __iter__(self):
            yield prefix
            pytest.fail("Загрузчик продолжил читать ленту после первых 100 записей")

    response = httpx.Response(200, stream=LongFeed())
    entries = read_feed_entries(response)
    assert [entry.title for entry in entries] == [str(i) for i in range(100)]


def test_documents_empty_and_safe_fill(app, tmp_path):
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text("[]", encoding="utf-8")
    app.config["DOCUMENT_CATALOG"] = str(catalog_path)
    page = app.test_client().get("/templates")
    assert page.status_code == 200
    assert "пока не подключены" in page.data.decode()
    # Тестовый документ — техническая фикстура, не нормативный бланк.
    (tmp_path / "sample.txt").write_text("Тест: {{name}}", encoding="utf-8")
    catalog = [
        {
            "id": "sample",
            "title": "Тестовый файл",
            "source_url": "https://example.test/fixture",
            "license": "test fixture",
            "file": "sample.txt",
        }
    ]
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    result = app.test_client().post("/templates/sample", data={"name": "{{7*7}}"})
    assert result.status_code == 200
    assert "{{7*7}}" in result.data.decode("utf-8-sig")
    assert "49" not in result.data.decode("utf-8-sig")


def test_community_pages_and_quiz_redaction(app):
    alice = register_and_login(app, "alice@example.test")
    for path in ("/forum", "/forum/create_topic", "/news", "/templates", "/test"):
        assert alice.get(path).status_code == 200
    assert "correct_id" not in public_question({"id": "test-fixture", "correct_id": "private"})
    assert alice.get("/api/test/question").status_code == 409
