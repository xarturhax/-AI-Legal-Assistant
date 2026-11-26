import re
import unicodedata

STOP_WORDS = set(
    (
        "что такое как мне меня я в на для по о об и или это пожалуйста "
        "найти расскажи объясни про можно ли у не"
    ).split()
)
DEFINITION_QUESTION = re.compile(
    r"\b(?:что (?:такое|означает)|кто так(?:ой|ая|ие)|"
    r"как (?:называют|называется|называются|назвать))\b"
)


def normalize_search_term(value):
    value = " ".join(unicodedata.normalize("NFKC", value).casefold().split())
    return value if re.fullmatch(r"[а-яёa-z][а-яёa-z ,()\-]{1,199}", value) else None


def matching_text(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().replace("ё", "е").split())


def contains_phrase(text, phrase):
    return bool(phrase) and re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text) is not None


def is_definition_question(query):
    return DEFINITION_QUESTION.search(matching_text(query)) is not None


def query_phrase(query):
    return re.sub(r"^(что такое|кто такой|кто такая)\s+", "", query.casefold()).strip(" ?!.\n\t")


def extract_terms(query):
    """Лексические кандидаты. Каждый кандидат далее проверяется в живой SC-памяти."""
    words = [w for w in re.findall(r"[а-яёa-z-]+", query.casefold()) if w not in STOP_WORDS]
    phrase = query_phrase(query)
    terms = [phrase] if 2 <= len(phrase) <= 200 else []
    for width in range(min(4, len(words)), 0, -1):
        for offset in range(len(words) - width + 1):
            term = " ".join(words[offset : offset + width])
            if term not in terms and 2 <= len(term) <= 200:
                terms.append(term)
    return terms[:16]
