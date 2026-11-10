# Аудит исходных репозиториев — S0

Дата: 28.10.2026. Файлы прочитаны через подключённый GitHub, не по пересказу ТЗ.
Машиночитаемые свидетельства: [evidence/upstream.json](evidence/upstream.json).

## Ревизии и права

| Источник | Зафиксированный SHA | Результат |
|---|---|---|
| [ostis-legislation](https://github.com/ostis-apps/ostis-legislation/tree/903e0c1e38dec25ba2f6ab4a9d5e82fe175d8e38) | 903e0c1e38dec25ba2f6ab4a9d5e82fe175d8e38 | MIT, Copyright 2025 OSTIS Applications; разрешено подключение с лицензией |
| [sc-legislation-app](https://github.com/SharkoStepan/sc-legislation-app/tree/f7b4dab74da2c5f289f282e8b2e9479f4d4a452f) | f7b4dab74da2c5f289f282e8b2e9479f4d4a452f | LICENSE в полном дереве не найден; только анализ поведения, исходники и оформление не переносятся |
| sc-web, подмодуль | 058ed9482806d41ea3190228ea595029f2450a27 | отдельная проверка лицензии при установке, debug не обязателен |
| ims.ostis.kb, подмодуль | 592145835643500878d5fc837df99009cd756c24 | отдельная проверка лицензии при установке обязательна |

Лицензия приложения upstream не доказывает актуальность и права на все вложенные документы.
Публикация нового проекта не выполняется. Лицензии подмодулей пока не подтверждены:
попытка получить файл LICENSE не дала читаемого результата.

Уточнение S7: корневые деревья обоих подмодулей прочитаны через GitHub на pin-SHA,
отдельного LICENSE в корне не найдено. Это не утверждение об отсутствии любых лицензионных
заголовков во всём дереве; публичное перераспространение требует отдельной проверки.
Дополнительно проверены интерфейсы recommendation.py, topic_tags.py и
recommendation_feedback_db.py старого приложения: похожие/персональные темы, метки,
поиск близких слов и обратная связь yes/no. Сценарии реализованы самостоятельно на S7.

## Реальная сборка

Прочитаны Dockerfile, docker-compose.yml, scripts/docker_entrypoint.sh, scripts/healthcheck.py,
ostis-legislation.ini, repo.path, .gitmodules и problem-solver/cxx/CMakeLists.txt.
Dockerfile скачивает sc-machine 0.10.0, собирает C++ расширения через Conan/CMake на Ubuntu noble.
Исходный Compose монтирует весь checkout в /knowledge-base и том /kb.bin.
Entrypoint build вызывает sc-builder --clear: повторный setup не должен запускать это на существующем томе.
CONFIG_PATH=/knowledge-base/ostis-legislation.ini, KB_PATH=/knowledge-base/repo.path;
extensions=/app/build/Release/extensions;/app/sc-machine/lib/extensions.
SC_SERVER_HOST=0.0.0.0 обязателен внутри сети контейнеров.
sc-web 0.9.0 оставляется отдельным debug-профилем. Flask — единственная основная точка входа.

## Протокол и ограничения агента

Прочитан целиком problem-solver/cxx/user-request-module/agent/user_request_agent.cpp,
проанализированы call_user_request_agent и обработчики старого Python приложения.
Действие action_user_request принимает SC-link через rrel_1, запускается action_initiated,
завершается action_finished_successfully/unsuccessfully, результат — структура через nrel_result.
В структуру добавляются ссылка определения, concept и article; это не JSON с полями статьи.
Агент ищет точное содержимое ссылок и требует одновременно русское название, belarus_legal_term,
определение, related concept и related article. Его guard linkAddrs1.size() > 1 действительно есть.
Кроме того, ветка fallback повторно добавляет reversed template вместо direct template.
Эффект на живой KB НЕ проверен, C++ код не исправлялся.

Существенное расхождение: в агенте nrel_related_article/nrel_related_concept (единственное число),
а проверенные housing SCS используют nrel_related_articles/nrel_related_concepts (множественное).
Поэтому gateway должен сначала вызвать старое действие, затем явно сообщать переход на чтение
SC-шаблонами при пустом/неуспешном результате. Это поиск, не эквивалентность юридическому выводу.
Оба написания отношений читаются только если узлы действительно существуют; узлы не создаются.

py-sc-client 0.4.0 установлен и изучен. SDK имеет глобальную сессию и ожидание ответа без deadline.
Нужны изолированный процесс с конечным timeout и сериализация операций, чтобы зависший SDK
не блокировал Flask и параллельные запросы не смешивали данные. Состояние действия локальное.
При таймауте действия автоматический повтор записи не допускается (неизвестный исход).

## База знаний и источники

Проверены три SCS словаря education/labor/housing, education act by_act_hk1100243.scs,
housing related_article/related_concepts, tests.scs, tests_trud.scs и test_keynodes.scs.
Из словарей извлечены 110 пар название/SC-ID для аудита и будущей оценки; приложение их не читает.
Примеры: concept_applicant_belarus (абитуриент), concept_employment_belarus (занятость),
concept_rental_housing_belarus (арендное жилье), by_act_hk1100243_article_1.
Обнаружен повтор concept_education_belarus для «воспитание» и «образование» — качество KB не гарантируется.
Определения: element ← rrel_key_sc_element: definition_structure ← nrel_sc_text_translation:
translation → rrel_example: text_link, с lang_ru → text_link.
Статьи используют тот же путь к HTML, загружаемому sc-builder из file://text/....
Нельзя отдавать file:// как рабочую пользовательскую ссылку или читать произвольный файл с хоста.
Текст статьи и системный идентификатор нужно получать из живой памяти. Редакция неизвестна,
если дата не получена из источника. Строка SHA — версия набора, не дата действия закона.

Тесты: tests_trud.scs содержит ll_d1_v1 и concept_correct_answer; tests.scs использует
concept_questions/nrel_answers, а агент — concept_question/nrel_answer. Обе схемы надо читать,
проверять наличие правильного ответа в KB и не объявлять учебную разметку юридической истиной.
Шаблоны старого сайта — три карточки с кнопками без обработчиков/файлов. Реальные бланки
не обнаружены: новый каталог допускает только явно подключённые файлы с источником.
Новости старого сайта читают filtered_news SQLite; новый RSS-кеш хранит источник и время загрузки.

## Среда и gate S0

Windows amd64; точную редакцию ОС проверить не удалось (CIM: Access denied).
Установлен Python 3.12.6, целевой runtime в Docker — 3.11.
Docker CLI 29.8.2 есть, Engine pipe отсутствует; чтение пользовательского Docker config запрещено.
WSL --status: E_ACCESSDENIED. Git HTTPS: соединение недоступно; GitHub connector работает.
PyPI доступен: зависимости SDK/Flask/pytest установлены. Ollama CLI/запущенная модель не обнаружены.
Живой OSTIS/LLM: NOT TESTED. Gate S0: аудит выполнен, непроверенные свойства явно отмечены.
Следующий шаг: безопасная установка pinned upstream и инфраструктура S1; остальные этапы
продолжаются при недоступности Engine с отдельными статусами live-проверок.
