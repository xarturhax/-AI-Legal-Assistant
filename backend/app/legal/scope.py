"""Bounded scope check for maritime registration against the live legal vocabulary."""

import re

MARITIME = re.compile(
    r"\b(?:морск[а-яё]+|судн[а-яё]+|корабл[а-яё]+|судов(?:ой|ого|ому|ом|ым|ые|ых|ыми))\b",
    re.IGNORECASE,
)
REGISTRY = re.compile(
    r"\b(?:(?:за|пере)?регистр[а-яё]+|реестр[а-яё]*|флаг[а-яё]*)\b", re.IGNORECASE
)


def maritime_registration(text):
    return bool(MARITIME.search(text) and REGISTRY.search(text))
