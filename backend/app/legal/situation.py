"""Контекст пользователя и кандидаты из словаря KB, без правовых выводов."""

import re

from app.legal.relevance import matched_topic_terms, topic_mentions
from app.legal.search_baseline import (
    STOP_WORDS,
    contains_phrase,
    matching_text,
    normalize_search_term,
)

# Слова общей просьбы не описывают предмет поиска. Названия понятий KB проверяются отдельно.
REQUEST_WORDS = STOP_WORDS | set(
    (
        "помоги помогите помощь помощи помочь нужна нужен нужно нужны хочу хочется "
        "получить совет совета консультация консультацию консультации подскажите подсказать "
        "разобраться разберитесь понять понимать делать сделать поступить действовать "
        "дальше теперь есть был была было были будет будут пожалуйста скажите расскажите "
        "объясните объяснение разъясните разъяснение ситуация ситуации ситуацию ситуацией "
        "проблема проблемы проблему проблемой вопрос вопросы вопроса вопросом вопросу "
        "мой моя моё мое мои моей мою моем моём мною мной меня мне я мы наш наша нашей "
        "всё все это этой этом этого такой такая такое такие так как что тут здесь "
        "очень сложная сложной сложную сложный сложным сложное юридическая юридической "
        "юридическую юридический правовая правовой правовую с со к ко от из за до же бы "
        "ну вот то а но вы ваш ваша вас вам"
    ).split()
)


def situation_plan(interpretation, query, vocabulary, *, topic_markers=None):
    interpretation.check_grounding(query)
    context_words = set(re.findall(r"[а-яёa-z]+", query.casefold())) - REQUEST_WORDS
    # Проверяем исходный текст, чтобы выдуманные entities/facts не создавали контекст.
    has_context = bool(context_words) or any(
        re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", query.casefold()) for term in vocabulary
    )
    extracted = []
    for entity in interpretation.entities:
        extracted.append({"kind": "entity", "text": entity.original_text, "candidate": entity.name})
    for fact in interpretation.facts:
        if fact.present_in_user_text:
            extracted.append({"kind": "fact", "text": fact.value, "candidate": fact.value})
    items = {}
    vocabulary_set = set(vocabulary)
    topic_markers = topic_markers or {}
    for item in extracted:
        candidate = normalize_search_term(item.pop("candidate")) or ""
        text = matching_text(item["text"])
        existing = items.setdefault(text, {**item, "terms": []})
        aliases = matched_topic_terms(text, topic_markers)
        terms = [term for term in aliases if term in vocabulary_set]
        terms.extend(term for term in vocabulary if contains_phrase(candidate, term))
        existing["terms"] = list(dict.fromkeys(existing["terms"] + terms))[:4]
    linked_terms = {term for item in items.values() for term in item["terms"]}
    for term, quote in topic_mentions(query, topic_markers).items():
        if term in vocabulary_set and term not in linked_terms:
            item = items.setdefault(
                matching_text(quote), {"kind": "topic", "text": quote, "terms": []}
            )
            item["terms"].append(term)
    questions = list(dict.fromkeys(interpretation.missing_information))
    if not has_context:
        questions = ["Опишите, что произошло, кто участвует и что вы хотите выяснить."]
    return {
        "items": list(items.values()),
        "search_allowed": has_context,
        "clarification_questions": questions,
        "needs_clarification": interpretation.needs_clarification or bool(questions),
        "assessment_status": "not_performed",
        "notice": "Найденные определения не устанавливают права и обязанности в этой ситуации.",
    }


def link_situation(plan, matches):
    for item in plan["items"]:
        item["source_ids"] = [
            source["id"]
            for source in matches
            if set(item["terms"]) & set(source.get("matched_terms", []))
        ]
        item["status"] = "linked" if item["source_ids"] else "unlinked"
    return plan
