"""Контекст пользователя и кандидаты из словаря KB, без правовых выводов."""

import re

from app.legal.search_baseline import STOP_WORDS, normalize_search_term

# Слова общей просьбы не описывают предмет поиска. Названия понятий KB проверяются отдельно.
REQUEST_WORDS = STOP_WORDS | set(
    (
        "помоги помогите помощь помощи помочь нужна нужен нужно нужны хочу хочется "
        "получить совет совета консультация консультацию консультации подскажите подсказать "
        "разобраться разберитесь понять понимать делать сделать поступить "
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


def situation_plan(interpretation, query, vocabulary):
    interpretation.check_grounding(query)
    context_words = set(re.findall(r"[а-яёa-z]+", query.casefold())) - REQUEST_WORDS
    # Проверяем исходный текст, чтобы выдуманные entities/facts не создавали контекст.
    has_context = bool(context_words) or any(
        re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", query.casefold()) for term in vocabulary
    )
    items = []
    for entity in interpretation.entities:
        items.append({"kind": "entity", "text": entity.original_text, "candidate": entity.name})
    for fact in interpretation.facts:
        if fact.present_in_user_text:
            items.append({"kind": "fact", "text": fact.value, "candidate": fact.value})
    for item in items:
        candidate = normalize_search_term(item.pop("candidate")) or ""
        item["terms"] = [
            term
            for term in vocabulary
            if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", candidate)
        ][:4]
    questions = list(dict.fromkeys(interpretation.missing_information))
    if not has_context:
        questions = ["Опишите, что произошло, кто участвует и что вы хотите выяснить."]
    return {
        "items": items,
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
