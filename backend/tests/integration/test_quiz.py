from uuid import UUID

import pytest
from app.db.models import User
from app.extensions import db
from werkzeug.security import generate_password_hash

pytestmark = pytest.mark.live_ostis


def test_quiz_reads_and_grades_live_ostis_questions(app):
    email, password = "quiz@example.test", "quiz-local-test-123"
    with app.app_context():
        db.session.add(
            User(email=email, password_hash=generate_password_hash(password), is_verified=True)
        )
        db.session.commit()
    client = app.test_client()
    assert client.post("/auth", data={"email": email, "password": password}).status_code == 302
    landing = client.get("/test").get_data(as_text=True)
    assert "После каждого ответа можно посмотреть результат" in landing
    assert "актуальность которой не подтверждена" not in landing
    assert client.post("/api/test/start").status_code == 200

    ostis = app.extensions["legal_service"].ostis
    seen = set()
    for correct in (False, True):
        response = client.get("/api/test/question")
        assert response.status_code == 200, response.json
        question = response.json["question"]
        assert question["id"] not in seen
        seen.add(question["id"])
        assert "correct_id" not in question
        assert question["provenance"]["source_system"] == "ostis"
        assert question["provenance"]["content_link"] > 0
        source = ostis.call("question", identifier=question["id"])
        assert question["text"] == source["text"]
        assert sorted(question["answers"], key=lambda answer: answer["id"]) == sorted(
            source["answers"], key=lambda answer: answer["id"]
        )
        assert client.get("/api/test/question").json["question"]["answers"] == question["answers"]
        answers_response = client.get(f"/api/test/answers/{question['id']}")
        assert answers_response.json["answers"] == question["answers"]
        answer_id = next(
            item["id"]
            for item in source["answers"]
            if (item["id"] == source["correct_id"]) == correct
        )
        response = client.post(
            "/api/test/answer", json={"question_id": question["id"], "answer_id": answer_id}
        )
        assert response.status_code == 200, response.json
        assert response.json["correct"] is correct
        assert response.json["expected_answer_id"] == source["correct_id"]
        assert response.json["score"] == {"answered": len(seen), "correct": int(correct)}

    assert client.get("/api/test/rating").json == {"answered": 2, "correct": 1}
    assert client.post("/api/test/finish").json == {"answered": 2, "correct": 1}
    assert client.get("/api/test/question").status_code == 409

    correct_positions = set()
    for seed in range(8):
        with client.session_transaction() as session:
            session["quiz_round"] = str(UUID(int=seed))
            session["quiz_question"] = source["id"]
        response = client.get("/api/test/question")
        assert response.status_code == 200
        order = [answer["id"] for answer in response.json["question"]["answers"]]
        correct_positions.add(order.index(source["correct_id"]))
        if len(correct_positions) > 1:
            break
    assert len(correct_positions) > 1

    result = client.post(
        "/test",
        data={"action": "answer", "question_id": source["id"], "answer_id": source["correct_id"]},
    ).get_data(as_text=True)
    assert "<h2>Верно</h2>" in result
    assert "<summary>Источник проверки</summary>" in result
