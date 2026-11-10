"""Независимая локальная реализация рекомендаций по тексту и своим просмотрам."""

import math
import re
from collections import Counter

from app.db.models import ForumTopic, RecommendationFeedback, TopicView, now
from app.extensions import db

TAGS = {
    "education": "Образование",
    "labor": "Труд",
    "housing": "Жильё",
    "family": "Семья",
    "civil": "Договоры и имущество",
    "other": "Другие темы",
}
HINTS = {
    "education": ("образован", "студент", "обучен", "школ", "университет"),
    "labor": ("труд", "работ", "нанимател", "увольн", "отпуск"),
    "housing": ("жиль", "жилищ", "квартир", "аренд", "общежит"),
    "family": ("семь", "семей", "алимент", "развод", "брак"),
    "civil": ("договор", "имуще", "собственност", "наслед"),
}
STOP = set(
    (
        "что как это для или при про по на об от за мы вы она они его мне меня "
        "такой какая можно почему"
    ).split()
)


def tag_keys(title, body):
    text = (title + " " + body).casefold()
    found = [key for key, hints in HINTS.items() if any(hint in text for hint in hints)]
    return "|" + "|".join(found[:3] or ["other"]) + "|"


def tags(topic):
    keys = topic.tag_keys or tag_keys(topic.title, topic.body)
    return [{"key": key, "label": label} for key, label in TAGS.items() if f"|{key}|" in keys]


def backfill_tags():
    records = db.session.execute(db.select(ForumTopic).where(ForumTopic.tag_keys == "")).scalars()
    for topic in records:
        topic.tag_keys = tag_keys(topic.title, topic.body)
    db.session.commit()


def vector(text):
    words = re.findall(r"[а-яёa-z]{3,}", text.casefold()[:8000])
    return Counter(word[:6] if len(word) > 6 else word for word in words if word not in STOP)


def similarity(left, right):
    product = sum(value * right.get(key, 0) for key, value in left.items())
    norm = math.sqrt(
        sum(value * value for value in left.values())
        * sum(value * value for value in right.values())
    )
    return product / norm if norm else 0


def record_view(user_id, topic_id):
    record = db.session.get(TopicView, (user_id, topic_id))
    if record is None:
        record = TopicView(user_id=user_id, topic_id=topic_id)
        db.session.add(record)
    record.viewed_at = now()
    db.session.commit()


def rank_topics(*, user_id=None, source=None, query=None, limit=6):
    topics = (
        db.session.execute(db.select(ForumTopic).order_by(ForumTopic.id.desc()).limit(1000))
        .scalars()
        .all()
    )
    context = f"topic:{source.id}" if source else "personal"
    viewed = []
    if user_id and source is None:
        viewed = (
            db.session.execute(
                db.select(ForumTopic)
                .join(TopicView, TopicView.topic_id == ForumTopic.id)
                .where(TopicView.user_id == user_id)
                .order_by(TopicView.viewed_at.desc())
                .limit(20)
            )
            .scalars()
            .all()
        )
    seeds = [source] if source else viewed
    seed_vector = (
        vector(query)
        if query
        else vector(" ".join(topic.title + " " + topic.body[:1000] for topic in seeds))
    )
    seed_tags = {item["key"] for topic in seeds for item in tags(topic)} - {"other"}
    feedback = {}
    if user_id and not query:
        rows = db.session.execute(
            db.select(RecommendationFeedback).filter_by(user_id=user_id, context=context)
        ).scalars()
        feedback = {row.topic_id: row.useful for row in rows}
    viewed_ids = {topic.id for topic in viewed}
    ranked = []
    for topic in topics:
        if (source and topic.id == source.id) or feedback.get(topic.id) is False:
            continue
        lexical = similarity(seed_vector, vector(topic.title + " " + topic.body))
        overlap = len(seed_tags & {item["key"] for item in tags(topic)})
        if source and lexical <= 0 and not overlap:
            continue
        if query and lexical <= 0:
            continue
        score = lexical + overlap * 0.08 + (0.25 if feedback.get(topic.id) else 0)
        if topic.id in viewed_ids:
            score *= 0.2
        reason = "Похоже на обсуждаемую тему" if source else "По вашим просмотрам"
        if (not seeds and not query) or score <= 0:
            reason = "Недавнее обсуждение"
        ranked.append({"topic": topic, "score": score, "reason": reason})
    return sorted(ranked, key=lambda row: (row["score"], row["topic"].id), reverse=True)[:limit]


def recommendation_payload(rows):
    return [
        {
            "id": row["topic"].id,
            "title": row["topic"].title,
            "score": round(row["score"], 4),
            "reason": row["reason"],
            "tags": tags(row["topic"]),
        }
        for row in rows
    ]
