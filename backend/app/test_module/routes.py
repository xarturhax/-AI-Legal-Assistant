from random import Random
from uuid import uuid4

from flask import Blueprint, abort, current_app, jsonify, render_template, request, session
from flask_login import current_user, login_required

from app.db.models import QuizAttempt
from app.extensions import db
from app.web_utils import payload, string_value

bp = Blueprint("quiz", __name__)


def attempts():
    return (
        db.session.execute(
            db.select(QuizAttempt).filter_by(
                user_id=current_user.id, round_id=session.get("quiz_round", "")
            )
        )
        .scalars()
        .all()
    )


def score():
    records = attempts()
    return {"answered": len(records), "correct": sum(record.correct for record in records)}


def current_question():
    if "quiz_round" not in session:
        abort(409, description="Сначала начните тест.")
    question = current_app.extensions["legal_service"].ostis.call(
        "question",
        identifier=session.get("quiz_question"),
        exclude=[record.question_id for record in attempts()],
    )
    if question:
        session["quiz_question"] = question["id"]
        answers = sorted(question["answers"], key=lambda answer: answer["id"])
        Random(f"{session['quiz_round']}:{question['id']}").shuffle(answers)
        question["answers"] = answers
    return question


def public_question(question):
    return {key: value for key, value in question.items() if key != "correct_id"}


def grade(data):
    question = current_question()
    identifier = string_value(data, "question_id", 220)
    answer_id = string_value(data, "answer_id", 220)
    if not question or question["id"] != identifier:
        abort(409, description="Вопрос изменился. Обновите страницу теста.")
    if answer_id not in {answer["id"] for answer in question["answers"]}:
        abort(400, description="Этот ответ не относится к текущему вопросу.")
    correct = answer_id == question["correct_id"]
    db.session.add(
        QuizAttempt(
            user_id=current_user.id,
            round_id=session["quiz_round"],
            question_id=identifier,
            answer_id=answer_id,
            correct=correct,
        )
    )
    db.session.commit()
    session.pop("quiz_question", None)
    return {
        "correct": correct,
        "expected_answer_id": question["correct_id"],
        "source": question["provenance"],
        "score": score(),
        "notice": "Результат по учебной разметке KB; актуальность правовой нормы не подтверждена.",
    }


@bp.route("/test", methods=["GET", "POST"])
@login_required
def test_page():
    question, result = None, None
    if request.method == "POST":
        data = payload()
        action = data.get("action")
        if action == "start":
            session["quiz_round"] = str(uuid4())
            session.pop("quiz_question", None)
            question = current_question()
        elif action == "answer":
            result = grade(data)
        elif action == "next":
            question = current_question()
        elif action == "finish":
            result = {"score": score()}
            session.pop("quiz_question", None)
            session.pop("quiz_round", None)
        else:
            abort(400)
    return render_template(
        "test.html", question=public_question(question) if question else None, result=result
    )


@bp.post("/api/test/start")
@login_required
def start():
    session["quiz_round"] = str(uuid4())
    session.pop("quiz_question", None)
    return jsonify(ok=True)


@bp.get("/api/test/question")
@login_required
def question():
    found = current_question()
    if not found:
        return jsonify(
            status="no_content", message="В KB нет новых вопросов с проверяемой разметкой."
        ), 404
    return jsonify(question=public_question(found))


@bp.post("/api/test/answer")
@login_required
def answer():
    return jsonify(grade(payload()))


@bp.get("/api/test/answers/<identifier>")
@login_required
def answers(identifier):
    found = current_question()
    if not found or identifier != found["id"]:
        abort(404)
    return jsonify(answers=found["answers"])


@bp.get("/api/test/rating")
@login_required
def rating():
    return jsonify(score())


@bp.post("/api/test/finish")
@login_required
def finish():
    result = score()
    session.pop("quiz_round", None)
    session.pop("quiz_question", None)
    return jsonify(result)
