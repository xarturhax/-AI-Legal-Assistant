import re

from app.errors import ServiceError
from app.legal.search_baseline import contains_phrase, matching_text


def literal_terms(query, vocabulary):
    text = matching_text(query)
    return sorted(
        (term for term in vocabulary if contains_phrase(text, matching_text(term))),
        key=len,
        reverse=True,
    )


def topic_mentions(query, topic_markers):
    mentions = {}
    for term, markers in topic_markers.items():
        for marker in sorted(markers, key=len, reverse=True):
            words = re.escape(matching_text(marker)).replace("е", "[её]").replace(r"\ ", r"\s+")
            if words and (match := re.search(rf"(?<!\w){words}(?!\w)", query, re.IGNORECASE)):
                mentions[term] = match.group()
                break
    return mentions


def matched_topic_terms(query, topic_markers):
    return list(topic_mentions(query, topic_markers))


def filter_sources(query, result, interpreter, *, direct_terms):
    text = matching_text(query)
    direct_titles = {matching_text(term) for term in direct_terms}
    direct, inferred = set(), []
    for source in result["matches"]:
        if matching_text(source["title"]) in direct_titles:
            direct.add(source["id"])
        elif source["excerpt"]:
            inferred.append(source)

    accepted = set()
    error_code = None
    if inferred:
        try:
            decisions = interpreter.relevant_sources(query, inferred)
        except ServiceError as error:
            error_code = error.code
        else:
            for decision in decisions:
                quote = matching_text(decision.query_quote)
                if (
                    1 <= decision.number <= len(inferred)
                    and any(character.isalnum() for character in quote)
                    and contains_phrase(text, quote)
                ):
                    accepted.add(inferred[decision.number - 1]["id"])

    kept, rejected = [], []
    allowed = direct | accepted
    for source in result["matches"]:
        if source["id"] in allowed:
            kept.append(source)
        else:
            rejected.append(source["id"])
    if inferred or rejected:
        event = {
            "method": "source_relevance",
            "status": "unavailable" if error_code else "checked",
            "accepted_checked_ids": sorted(accepted),
            "excluded_ids": rejected,
        }
        if error_code:
            event["reason"] = error_code
        result["trace"].append(event)
    result["matches"] = kept
    return error_code
