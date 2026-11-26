# API и ошибки

JSON API использует ту же cookie-сессию, что сайт. Получите CSRF-токен из meta csrf-token
на `/requests` и передавайте его в `X-CSRFToken` для POST/PUT/DELETE. Защита не отключена
для юридических запросов гостей. Неавторизованные приватные API отвечают 401 до CSRF-проверки.

| Метод / путь | Вход / результат |
|---|---|
| GET /health/live | процесс, mock=false; без зависимостей |
| GET /health/ready | database/ostis/llm отдельно; 503 при критической неготовности |
| POST /api/legal/query | query 2–1500 символов, mode baseline/llm; interpretation, matches, unmatched_terms, trace, answer, runtime |
| GET /api/legal/concepts?term=...&mode=baseline\|llm | название или описание от 2 до 200 символов. По умолчанию baseline. LLM подбирает термины по словарю OSTIS. Оба режима возвращают карточки из SC-шаблонов |
| GET /api/legal/sources/{id} | текст/название/SC-ID/SC-адрес/происхождение/связи; 404 если источник отсутствует |
| GET/PUT /api/profile | свой профиль, email и verified read-only |
| GET/PUT /api/settings | mode и timezone |
| GET/DELETE /api/history | свои запросы / очистка своей истории |
| GET/POST/PUT/DELETE /api/notes | text, optional source_id; для изменения id |
| GET/POST/DELETE /api/bookmarks | source_id проверяется в OSTIS; для удаления id |
| GET/POST/PUT/DELETE /api/calendar | title, description, starts_at ISO, timezone; для изменения id |
| GET/POST /api/forum/topics | список / создание темы с title, body |
| GET /api/forum/topics/{id} | тема и неудалённые сообщения с оценками |
| GET /api/forum/search?term=... | буквальный поиск по темам, SQL/wildcards экранированы |
| GET /api/forum/search?term=...&semantic=1 | локальная лексическая близость русских формулировок |
| GET /api/forum/topics?tag=labor | тематический фильтр; education/labor/housing/family/civil/other |
| GET /api/forum/recommendations | личные рекомендации; optional source_topic_id для похожих тем |
| POST /api/forum/recommendation_feedback | topic_id, optional source_topic_id, useful yes/no; только своя обратная связь |
| POST /api/forum/posts | topic_id, body; нужен вход |
| PUT/DELETE /api/forum/posts/{id} | свои сообщения; удаление мягкое |
| POST /api/forum/posts/{id}/vote | vote -1/0/1; 0 снять, свой пост оценивать нельзя |
| POST /api/test/start | новая попытка; прежние результаты не удаляются |
| GET /api/test/question | текущий/следующий вопрос из живой KB; правильный ответ скрыт |
| GET /api/test/answers/{id} | варианты текущего вопроса |
| POST /api/test/answer | question_id, answer_id; повторное чтение SC-разметки и запись личного результата |
| GET /api/test/rating | answered/correct для текущего раунда |
| POST /api/test/finish | итог, завершение раунда |

`matches` содержат source_system=ostis, фактические sc_identifier (может быть null),
sc_address, id, title, excerpt, text, source_document, revision, currency, related и provenance.
`source_exists=true` подтверждает, что карточка прочитана из OSTIS.
`source_relevant=true` у результата запроса означает совпадение нормализованного
предмета запроса с названием. `source_relevant=null` означает, что релевантность
не установлена. `legal_applicability=null` означает отсутствие оценки применимости.
У отдельно открытого источника релевантность не оценивается.
`text_status` принимает `available`, `unavailable_file_reference` или `unavailable`.
`text_kind=summary` помечает редакционное изложение статьи, прочитанное из SC-ссылки.
`text_kind=source` обозначает текст из основного блока источника. Это может быть выдержка.
При наличии только файловой ссылки сохраняются SC-ID, связи и provenance,
а `text` и `excerpt` пусты. Файловый путь не включается в текст выдачи.
`addr:N` в URL означает настоящий числовой адрес, не выдуманный SC-ID. Он может устареть после rebuild.
`revision=null` означает неизвестную редакцию. Нет подтверждённых выдержек — answer.status=no_evidence,
без юридических утверждений. При отказе OSTIS ответ 503/504 не содержит answer.

`search_terms` верхнего уровня содержит кандидаты, фактически отправленные в поиск,
включая термины из контекста. `interpretation.search_terms` сохраняет список модели.
В LLM-режиме `situation.items` связывает цитаты entities и явно присутствующих facts
с `terms` из текущего словаря и `source_ids` из найденных результатов. `status` каждого
элемента принимает `linked` или `unlinked`. Эта связь означает поиск понятия, применимость
нормы к обстоятельствам не установлена. `assessment_status=not_performed`.
Если поисковая формулировка из OSTIS буквально присутствует в запросе, контекст
может содержать дополнительно связанный фрагмент с `kind=topic`.
`clarification_questions` содержит missing_information модели, `needs_clarification`
учитывает как исходный флаг, так и наличие вопросов. В baseline `situation` обычно
равно `null`, при ограничении предметной области оно содержит уточнение.
`situation.search_allowed=false` означает, что исходный запрос содержит только общую
просьбу без предмета или обстоятельств. В этом случае поиск и action не запускаются,
`search_terms=[]`, `matches=[]`, `answer.status=no_evidence`, а trace содержит
`query_interpretation` с `reason=insufficient_context`. Уточнение обязательно,
вопросы не предполагают выдуманный договор или событие. При наличии предмета либо
события `needs_clarification=true` допускает частичный поиск вместе с вопросами.
Если запрос явно о регистрации морских судов, а живой словарь не подтверждает
предметную область, оба режима возвращают пустую выдачу и уточнение с
`reason=outside_confirmed_scope`. При таком отказе `runtime.llm_used=false`.

`answer.guidance` содержит пояснения для принятых тем. Для каждой темы
`provisions` содержит формулировку `text`, SC-идентификатор статьи `id`,
адрес ссылки `text_link`, реквизиты `citation` и `official_url`.
`checks` содержит условия, которые предлагается проверить в ситуации.
При отсутствии тематических пояснений массив `guidance` пуст.
У карточки темы эти сведения доступны также в `case_guidance`.

Событие action_user_request в trace содержит result_nodes_count и source_count:
status=finished означает завершение действия, но не гарантирует непустой ответ.
При отсутствии пригодных источников SC-template событие помечено reason=agent_no_sources.
Точные совпадения по названию из SC-шаблона идут перед связанными результатами агента.
При наличии результатов агента событие точного совпадения имеет reason=exact_title.
LLM выбирает interpretation.search_terms из словаря, прочитанного в текущей SC-памяти;
это кандидаты поиска, а не правовые выводы. Названия, отсутствующие в словаре, отклоняются
с ошибкой формата; пустой словарь даёт ostis_vocabulary_empty (503).
`sc_situation_topic` отмечает совпадение исходной формулировки с темой.
`source_relevance` показывает статус проверки, принятые `accepted_checked_ids`
и исключённые `excluded_ids`. При недоступности проверки сохраняются прямые
совпадения, а событие получает статус `unavailable`.

Ошибки: `error: {code, message}`. Код 400 для входа/CSRF, 401 входа, 403 запрета,
404 отсутствия/чужой приватной записи, 409 конфликта, 429 частоты, 502 формата LLM,
503 недоступной службы, 504 таймаута. Чужие пароли, токены и приватные поля в ответ не включаются.
history гостей не сохраняется. Ответы API имеют Cache-Control: no-store.

Регистрация `/reg`, вход `/auth`, проверка `/verification`, восстановление `/recover`
работают HTML-формами. Мутации старого сайта, выполнявшиеся GET-запросами, переведены на POST
(выход, повторный код, удаление события). Старые внешние JS-клиенты не переносятся автоматически;
новый UI реализует требуемые пользовательские сценарии через эти контракты.
