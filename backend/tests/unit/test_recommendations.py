from app.db.models import RecommendationFeedback, TopicView
from app.extensions import db
from test_accounts import register_and_login


def create_topic(client, title, body):
    response = client.post("/api/forum/topics", json={"title": title, "body": body})
    assert response.status_code == 201
    return response.json["id"]


def test_personal_recommendations_and_feedback_are_private(app):
    alice = register_and_login(app, "alice@example.test")
    bob = register_and_login(app, "bob@example.test")
    labor = create_topic(alice, "Труд и увольнение", "Работники обсуждают увольнение")
    related = create_topic(bob, "Обсуждение увольнения", "Работники и трудовой договор")
    housing = create_topic(bob, "Аренда квартиры", "Обсуждение арендного жилья")
    housing_related = create_topic(bob, "Аренда жилья", "Арендная квартира")
    alice.get(f"/forum/topic/{labor}")
    bob.get(f"/forum/topic/{housing}")
    assert alice.get("/api/forum/recommendations").json["items"][0]["id"] == related
    assert bob.get("/api/forum/recommendations").json["items"][0]["id"] == housing_related
    for _ in range(2):
        assert (
            alice.post(
                "/api/forum/recommendation_feedback", json={"topic_id": related, "useful": "no"}
            ).status_code
            == 200
        )
    assert related not in [
        row["id"] for row in alice.get("/api/forum/recommendations").json["items"]
    ]
    assert related in [row["id"] for row in bob.get("/api/forum/recommendations").json["items"]]
    with app.app_context():
        assert len(db.session.execute(db.select(RecommendationFeedback)).scalars().all()) == 1
        views = db.session.execute(db.select(TopicView)).scalars().all()
        assert len(views) == 2 and views[0].user_id != views[1].user_id
    assert app.test_client().get("/api/forum/recommendations").status_code == 401


def test_tags_similar_word_search_and_topic_recommendations(app):
    alice = register_and_login(app, "alice@example.test")
    labor = create_topic(alice, "Обсуждение увольнения", "Трудовой договор работника")
    related = create_topic(alice, "Порядок увольнения", "Личный опыт работника")
    create_topic(alice, "Школьное образование", "Учебные занятия")
    items = alice.get("/api/forum/topics?tag=labor").json["items"]
    assert {row["id"] for row in items} == {labor, related}
    assert alice.get("/api/forum/search?term=увольнение&semantic=1").json["items"]
    assert (
        alice.get(f"/api/forum/recommendations?source_topic_id={labor}").json["items"][0]["id"]
        == related
    )
    assert alice.get(f"/forum/topic/{labor}").status_code == 200
