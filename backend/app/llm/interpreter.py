import json

import httpx
from pydantic import ValidationError

from app.config import local_service_url
from app.errors import ServiceError
from app.llm.prompts import DIRECTORY_PROMPT, SOURCE_RELEVANCE_PROMPT, SYSTEM_PROMPT
from app.llm.schemas import DirectoryTerms, Interpretation, SourceRelevance


class OllamaInterpreter:
    def __init__(self, base_url, model, timeout=120):
        self.base_url = local_service_url(
            base_url, "http", {"ollama", "localhost", "127.0.0.1", "host.docker.internal"}
        )
        if "cloud" in model.lower():
            raise ValueError("Облачные модели запрещены. Выберите локальную модель Ollama.")
        self.model = model
        self.timeout = timeout

    def ready(self):
        try:
            with httpx.Client(timeout=3, trust_env=False) as connection:
                response = connection.get(self.base_url + "/api/tags")
                response.raise_for_status()
                for model in response.json().get("models", []):
                    if model.get("name") == self.model and not model.get("remote_model"):
                        return True
        except (httpx.HTTPError, ValueError, TypeError):
            pass
        return False

    def interpret(self, query, vocabulary=None):
        return self._complete(
            query, vocabulary, Interpretation, SYSTEM_PROMPT, 1500
        ).check_grounding(query)

    def interpret_directory(self, query, vocabulary):
        result = self._complete(query, vocabulary, DirectoryTerms, DIRECTORY_PROMPT, 320)
        return Interpretation(
            intent="definition",
            domain_hints=[],
            search_terms=result.search_terms,
            entities=[],
            facts=[],
            missing_information=[],
            needs_clarification=False,
        )

    def relevant_sources(self, query, sources):
        question = {
            "question": query,
            "sources": [
                {"number": n, "title": source["title"], "excerpt": source["excerpt"][:480]}
                for n, source in enumerate(sources, start=1)
            ],
        }
        return self._complete(
            json.dumps(question, ensure_ascii=False),
            None,
            SourceRelevance,
            SOURCE_RELEVANCE_PROMPT,
            420,
            timeout=min(self.timeout, 30),
            attempts=1,
        ).relevant

    def _complete(
        self, query, vocabulary, output_type, system_prompt, tokens, *, timeout=None, attempts=2
    ):
        if not self.ready():
            raise ServiceError(
                "Локальная модель недоступна. Выберите классический поиск.", "llm_unavailable"
            )
        schema = output_type.model_json_schema()
        user_content = query
        if vocabulary is not None:
            if not vocabulary:
                raise ServiceError(
                    "В OSTIS нет доступных названий понятий.", "ostis_vocabulary_empty"
                )
            schema["properties"]["search_terms"]["items"]["enum"] = vocabulary
            user_content = json.dumps(
                {"question": query, "available_terms": vocabulary}, ensure_ascii=False
            )
        payload = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "options": {"temperature": 0, "num_predict": tokens, "num_ctx": 4096},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
        for attempt in range(attempts):
            try:
                with httpx.Client(timeout=timeout or self.timeout, trust_env=False) as connection:
                    response = connection.post(self.base_url + "/api/chat", json=payload)
                    response.raise_for_status()
                    content = response.json()["message"]["content"]
                if not isinstance(content, str) or len(content) > 16000:
                    raise ValueError("Недопустимый размер ответа модели")
                interpretation = output_type.model_validate_json(content)
                if vocabulary is not None and any(
                    term not in vocabulary for term in interpretation.search_terms
                ):
                    raise ValueError("Модель выбрала термин вне текущего словаря OSTIS")
                return interpretation
            except httpx.TimeoutException as error:
                raise ServiceError(
                    "Истекло время ожидания локальной модели.", "llm_timeout", 504
                ) from error
            except httpx.HTTPError as error:
                raise ServiceError(
                    "Ollama недоступен. Выберите классический поиск.", "llm_unavailable"
                ) from error
            except (
                ValidationError,
                json.JSONDecodeError,
                KeyError,
                ValueError,
                TypeError,
            ) as error:
                if attempt + 1 == attempts:
                    raise ServiceError(
                        "Модель вернула некорректный JSON.", "llm_format", 502
                    ) from error
        raise AssertionError("Недостижимая ветка")
