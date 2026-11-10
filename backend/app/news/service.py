from urllib.parse import urlsplit
from xml.parsers import expat

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.db.models import NewsCache, NewsFeedState, now
from app.extensions import db

MAX_FEED_BYTES = 8_000_000
MAX_ENTRIES = 100
ENTRY_PATHS = {
    ("rss", "channel", "item"),
    ("http://www.w3.org/2005/Atom feed", "http://www.w3.org/2005/Atom entry"),
    ("http://www.w3.org/1999/02/22-rdf-syntax-ns# RDF", "http://purl.org/rss/1.0/ item"),
}


def safe_url(value):
    parsed = urlsplit(value)
    return parsed.scheme in {"https", "http"} and bool(parsed.hostname) and not parsed.username


def read_feed_entries(response):
    """Читает ограниченную часть ленты и считает завершённые записи."""
    content = bytearray()
    path = []
    completed = 0
    parser = expat.ParserCreate(namespace_separator=" ")
    # Для подсчёта элементов разворачивать XML-сущности не нужно.
    parser.DefaultHandler = lambda _: None

    def start_element(name, _attributes):
        path.append(name)

    def end_element(_name):
        nonlocal completed
        if len(path) <= 3 and tuple(path) in ENTRY_PATHS:
            completed += 1
        path.pop()

    parser.StartElementHandler = start_element
    parser.EndElementHandler = end_element
    entry_limit = MAX_ENTRIES
    for chunk in response.iter_bytes(chunk_size=65_536):
        remaining = MAX_FEED_BYTES - len(content)
        prefix = chunk[:remaining]
        content.extend(prefix)
        if parser is not None:
            try:
                parser.Parse(prefix, False)
            except expat.ExpatError:
                # В пределах лимита feedparser может обработать нестрогий XML.
                parser = None
        if completed >= MAX_ENTRIES or len(chunk) > remaining:
            if not completed:
                raise ValueError("В первых 8 МБ ленты нет полной записи")
            entry_limit = min(completed, MAX_ENTRIES)
            break

    feed = feedparser.parse(bytes(content))
    if not feed.version or (feed.bozo and not feed.entries):
        raise ValueError("Некорректный RSS/Atom")
    return feed.entries[:entry_limit]


def refresh_feeds(urls):
    results = []
    for url in urls[:5]:
        state = db.session.get(NewsFeedState, url) or NewsFeedState(source_url=url)
        state.checked_at = now()
        db.session.add(state)
        try:
            if not safe_url(url) or not url.startswith("https://"):
                raise ValueError("Разрешены только HTTPS RSS-источники")
            with httpx.Client(timeout=10, follow_redirects=False, trust_env=False) as connection:
                with connection.stream("GET", url) as response:
                    response.raise_for_status()
                    entries = read_feed_entries(response)
            saved = 0
            for entry in entries:
                link = entry.get("link", "")
                if not safe_url(link) or len(link) > 2000:
                    continue
                record = db.session.execute(
                    db.select(NewsCache).filter_by(link=link)
                ).scalar_one_or_none()
                if record is None:
                    record = NewsCache(link=link)
                    db.session.add(record)
                record.source_url = url
                record.title = BeautifulSoup(
                    entry.get("title", "Без заголовка"), "html.parser"
                ).get_text(" ")[:500]
                record.excerpt = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(
                    " "
                )[:3000]
                record.published_at = entry.get("published", entry.get("updated", ""))[:100] or None
                record.fetched_at = now()
                saved += 1
            state.error, state.succeeded_at = None, now()
        except (httpx.HTTPError, ValueError, TypeError) as error:
            state.error = "Источник недоступен; сохранён последний успешный кеш."
            result = {"url": url, "status": "FAIL", "error_type": type(error).__name__}
            if isinstance(error, ValueError):
                result["detail"] = str(error)
            results.append(result)
        else:
            results.append({"url": url, "status": "PASS", "entries": saved})
        db.session.commit()
    return results
