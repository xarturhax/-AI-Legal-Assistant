from flask import Blueprint, abort, jsonify, redirect, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from app.db.models import ForumPost, ForumTopic, PostVote, RecommendationFeedback, now
from app.extensions import db
from app.forum.recommendations import (
    TAGS,
    rank_topics,
    recommendation_payload,
    record_view,
    tag_keys,
    tags,
)
from app.web_utils import integer_value, own_row, payload, serialize, string_value

bp = Blueprint("forum", __name__)


def topics_query():
    query = db.select(ForumTopic)
    term = request.args.get("term", "").strip()[:200]
    if term:
        query = query.where(
            or_(
                ForumTopic.title.contains(term, autoescape=True),
                ForumTopic.body.contains(term, autoescape=True),
            )
        )
    tag = request.args.get("tag", "")
    if tag:
        if tag not in TAGS:
            abort(400, description="Неизвестная тема форума.")
        query = query.where(ForumTopic.tag_keys.contains(f"|{tag}|", autoescape=True))
    return query.order_by(ForumTopic.id.desc()).limit(100)


def listed_topics():
    term = request.args.get("term", "").strip()[:200]
    if request.args.get("semantic") == "1" and term:
        return [row["topic"] for row in rank_topics(query=term, limit=100)]
    return db.session.execute(topics_query()).scalars().all()


def topic_or_404(identifier):
    topic = db.session.get(ForumTopic, identifier)
    if not topic:
        abort(404, description="Тема не найдена.")
    return topic


def posts_for(topic_id):
    score = (
        db.select(func.coalesce(func.sum(PostVote.vote), 0))
        .where(PostVote.post_id == ForumPost.id)
        .scalar_subquery()
    )
    query = db.select(ForumPost, score.label("score")).where(
        ForumPost.topic_id == topic_id, ForumPost.deleted_at.is_(None)
    )
    if request.args.get("sort") == "rating":
        query = query.order_by(score.desc(), ForumPost.id)
    else:
        query = query.order_by(ForumPost.id)
    return [
        {
            **serialize(post),
            "is_own": current_user.is_authenticated and post.user_id == current_user.id,
            "score": rating,
        }
        for post, rating in db.session.execute(query.limit(200))
    ]


@bp.get("/forum")
def forum():
    recommendations = rank_topics(user_id=current_user.id) if current_user.is_authenticated else []
    return render_template(
        "forum.html",
        topics=listed_topics(),
        tag_labels=TAGS,
        tags=tags,
        recommendations=recommendation_payload(recommendations),
        source_topic_id=None,
    )


@bp.get("/api/forum/topics")
@bp.get("/api/forum/search")
def topics_api():
    return jsonify(items=[{**serialize(topic), "tags": tags(topic)} for topic in listed_topics()])


@bp.route("/forum/create_topic", methods=["GET", "POST"])
@bp.post("/api/forum/topics")
@login_required
def create_topic():
    if request.method == "GET":
        return render_template("forum_create.html")
    data = payload()
    topic = ForumTopic(
        user_id=current_user.id,
        title=string_value(data, "title", 200),
        body=string_value(data, "body", 20000),
    )
    topic.tag_keys = tag_keys(topic.title, topic.body)
    db.session.add(topic)
    db.session.commit()
    if request.is_json:
        return jsonify(serialize(topic)), 201
    return redirect(f"/forum/topic/{topic.id}")


@bp.get("/forum/topic/<int:identifier>")
@bp.get("/api/forum/topics/<int:identifier>")
def topic(identifier):
    record = topic_or_404(identifier)
    posts = posts_for(identifier)
    if current_user.is_authenticated and not request.path.startswith("/api/"):
        record_view(current_user.id, identifier)
    recommendations = recommendation_payload(
        rank_topics(
            user_id=current_user.id if current_user.is_authenticated else None, source=record
        )
    )
    if request.path.startswith("/api/"):
        return jsonify(
            topic={**serialize(record), "tags": tags(record)},
            posts=posts,
            recommendations=recommendations,
        )
    return render_template(
        "forum_topic.html",
        topic=record,
        posts=posts,
        recommendations=recommendations,
        source_topic_id=identifier,
    )


@bp.get("/api/forum/recommendations")
@login_required
def recommended():
    source_id = request.args.get("source_topic_id")
    source = topic_or_404(integer_value({"id": source_id}, "id")) if source_id else None
    return jsonify(
        items=recommendation_payload(rank_topics(user_id=current_user.id, source=source))
    )


@bp.post("/api/forum/recommendation_feedback")
@bp.post("/forum/recommendation_feedback")
@login_required
def recommendation_feedback():
    data = payload()
    topic_id = integer_value(data, "topic_id")
    topic_or_404(topic_id)
    source_id = data.get("source_topic_id")
    if source_id:
        source = topic_or_404(integer_value(data, "source_topic_id"))
        context = f"topic:{source.id}"
    else:
        context = "personal"
    useful = data.get("useful")
    if not isinstance(useful, str) or useful not in {"yes", "no"}:
        abort(400, description="Укажите полезность рекомендации: yes или no.")
    record = db.session.execute(
        db.select(RecommendationFeedback).filter_by(
            user_id=current_user.id, context=context, topic_id=topic_id
        )
    ).scalar_one_or_none()
    if record is None:
        record = RecommendationFeedback(user_id=current_user.id, context=context, topic_id=topic_id)
        db.session.add(record)
    record.useful = useful == "yes"
    db.session.commit()
    if request.is_json:
        return jsonify(ok=True)
    return redirect(f"/forum/topic/{source_id}" if source_id else "/forum")


@bp.post("/api/forum/posts")
@bp.post("/forum/topic/<int:identifier>/add_message")
@login_required
def add_post(identifier=None):
    data = payload()
    identifier = identifier or integer_value(data, "topic_id")
    topic_or_404(identifier)
    post = ForumPost(
        user_id=current_user.id, topic_id=identifier, body=string_value(data, "body", 20000)
    )
    db.session.add(post)
    db.session.commit()
    if request.is_json:
        return jsonify(serialize(post)), 201
    return redirect(f"/forum/topic/{identifier}")


@bp.route("/api/forum/posts/<int:identifier>", methods=["PUT", "DELETE"])
@bp.post("/forum/post/<int:identifier>")
@login_required
def edit_post(identifier):
    post = own_row(ForumPost, identifier)
    if post.deleted_at:
        abort(404, description="Сообщение удалено.")
    data = payload()
    if request.method == "DELETE" or data.get("action") == "delete":
        post.deleted_at = now()
    else:
        post.body = string_value(data, "body", 20000)
    db.session.commit()
    if request.is_json:
        return jsonify(ok=True)
    return redirect(f"/forum/topic/{post.topic_id}")


@bp.post("/api/forum/posts/<int:identifier>/vote")
@bp.post("/forum/post/<int:identifier>/vote")
@login_required
def vote(identifier):
    post = db.session.get(ForumPost, identifier)
    if post is None or post.deleted_at:
        abort(404, description="Сообщение не найдено.")
    if post.user_id == current_user.id:
        abort(403, description="Нельзя оценивать собственное сообщение.")
    value = payload().get("vote")
    if isinstance(value, bool) or str(value) not in {"-1", "0", "1"}:
        abort(400, description="Оценка должна быть -1, 0 или 1.")
    record = db.session.execute(
        db.select(PostVote).filter_by(user_id=current_user.id, post_id=identifier)
    ).scalar_one_or_none()
    if int(value) == 0:
        if record:
            db.session.delete(record)
    elif record:
        record.vote = int(value)
    else:
        db.session.add(PostVote(user_id=current_user.id, post_id=identifier, vote=int(value)))
    db.session.commit()
    if request.is_json:
        return jsonify(ok=True)
    return redirect(f"/forum/topic/{post.topic_id}")
