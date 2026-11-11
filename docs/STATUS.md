# Состояние проекта

Исправление Q36, S3/S6 — DONE для проверенных сценариев. Общая просьба без предмета
или обстоятельств требует уточнения, поиск не запускается. Проверяются исходный текст,
grounding фактов и явные названия понятий KB. Наличие needs_clarification и
missing_information сохраняет частичный поиск по уже названному предмету.
Проверка контекста лексическая, произвольные формулировки требуют дальнейшей оценки.

Полный прогон текущего кода дал 76 PASS, 1 XFAIL и 0 SKIPPED. Unit — 59 PASS,
из них 31 с меткой mock. Новые live E2E подтвердили пустую выдачу с уточнением
для Q35, Q36 и ещё одной общей просьбы. Частичная жилищная ситуация и запрос
определения сохранили подтверждённые источники. Все регрессии fallback прошли.
Исходный C++-агент сохранён, его известный XFAIL остаётся.

Повторная оценка прежних 36 запросов в двух режимах дала 72 выполнения без ошибок
и таймаутов. Ожидаемый источник найден в 24/30 запросов baseline и 30/30 LLM.
Все 6 отрицательных случаев LLM имеют no_evidence, включая Q35 и Q36.
Изменены legal/situation.py, legal/service.py, промпт, шаблон поиска, unit и live E2E.
JUnit и метрики сохранены в docs/evidence/clarification-live-tests.xml и
docs/evidence/clarification-live-evaluation.json. Текущий код проверен из checkout,
для обновления сайта требуется пересобрать образ app из пользовательского PowerShell.

Предыдущая итерация S2/S3/S6 — PARTIAL. Добавлены привязка контекста ситуации, вопросы
для уточнения и диагностика исходного action_user_request. Baseline больше не зависит
от healthcheck Ollama в Compose. Все пользовательские разделы сохранены.

После пользовательского запуска стека предыдущий код дал 57 PASS, 1 XFAIL, 0 SKIPPED.
Из 45 unit-тестов 23 помечены mock. Миграция SQLite, отказы соединения OSTIS,
baseline с недоступным адресом Ollama и три сложные LLM-ситуации прошли.
Оценка прежних 36 запросов в двух режимах выполнена, 72 выполнения без ошибок
и таймаутов. Ожидаемые источники найдены в 24/30 запросов baseline и 30/30 LLM.
LLM неверно выбрала понятия для неопределённого Q36, в текущей версии случай исправлен.
У XFAIL подтверждено отсутствие singular-связей при наличии plural-связей в KB.
Предложение C++-исправления находится в ACTION_USER_REQUEST.md, исходный агент сохранён.
Docker Engine отклоняет подключение. Остановка настоящих контейнеров и развёртывание
нового образа app из этого сеанса остаются недоступными.

Изменены legal/service.py, новый legal/situation.py, схемы/промпт LLM,
ostis/memory.py, шаблон поиска, Compose, evaluate.py и тесты.
Ruff, validate_infra.py, Compose config и diff check прошли.
Следующий шаг для обновления сайта — пересобрать app и запустить его с новым образом.

11.11.2026. Подтверждены реальные выдержки из OSTIS в baseline и LLM-режиме,
HTTP readiness 200 (database/ostis/llm=true, mock=false). Установка и миграции Docker Python 3.11
пройдены; пользователь подтвердил сохранение кабинета и заметок после перезапуска.

Последний полный набор с live-флагами: **76 PASS, 1 XFAIL**, включая настоящее чтение KB
и Flask → Ollama → OSTIS. XFAIL явно сохраняет ограничение исходного action_user_request:
действие завершено, но источники не возвращены. Это не PASS агента.
Исторический набор при выключенных службах: **2 FAIL OSTIS + 1 FAIL E2E**.
Полная приёмка не завершена; HTTP/Chrome и локальная SQLite проверены без подмен.

| Стадия | Реализация | Проверки / gate |
|---|---|---|
| S0 | DONE: аудит, SHA, карта совместимости | источники прочитаны, лицензии подмодулей требуют проверки |
| S1 | PARTIAL: Compose, pinned upstream, Windows launcher, защита KB/бэкап | setup PASS из свежего клона с отдельными портами и томами; readiness 200 |
| S2 | PARTIAL: Flask, SC SDK worker, action + шаблоны, источники | чтение реальных SC-источников PASS, fallback PASS; исходный агент — известный XFAIL |
| S3 | PARTIAL: локальный Ollama, JSON Schema, контекст и linking | live E2E PASS; 6/6 перефразирований, 6/6 отрицательных запросов; Q36 исправлен |
| S4 | DONE для приложения: аккаунты, кабинет, история, заметки, календарь | проверки изоляции PASS; кабинет/заметки после перезапуска подтверждены пользователем |
| S5 | PARTIAL: форум/рекомендации, SC-тесты, документы, RSS | Учебный тест с живой KB, три шаблона и реальный импорт RSS PASS |
| S6 | DONE: 36 размеченных запросов, полный live-прогон в двух режимах | 72 выполнения без таймаутов, метрики и расхождения в TEST_REPORT.md |
| S7 | DONE: README, архитектура/API, лицензии, реальный HTTP/Chrome | страницы PASS; Windows-установка из свежего Git-клона и readiness PASS |

S0: изменены docs/REPO_AUDIT.md, PARITY_MATRIX.md, DECISIONS.md, evidence/upstream.json.
Проверки: полные деревья GitHub на заданных SHA — PASS; py-sc-client/py-sc-kpm 0.4.0
установлены; docker version — FAIL (Engine pipe отсутствует); wsl --status — FAIL (отказ доступа);
git ls-remote — FAIL (сеть). Проверка не подменяется mock. Следующий шаг S1.

S1: добавлены docker-compose.yml, compose.debug.yml, ostis/upstream.lock.json,
ostis/runtime.ini, backend/Dockerfile, lock зависимостей, .env.example, четыре bat,
scripts/manage.ps1 и validate_infra.py. Локальный .env с новым секретом игнорируется Git.
`python scripts/validate_infra.py`: PASS (static); PowerShell Parser: PASS после исправления
UTF-8 BOM для Windows PowerShell 5.1. `docker compose config --quiet`: PASS.
Upstream checkout/сборка/WS/модель: NOT TESTED, Engine отсутствует. Никакие старые данные
не удалялись. Gate S1 BLOCKED; продолжается разработка S2, без заявления о live-готовности.

S2: добавлены backend/app (factory, legal, ostis, templates, static), pyproject.toml,
backend/tests/unit/test_core.py, integration/test_ostis.py, conftest.py.
`python -m pytest backend/tests/unit backend/tests/integration -q`: 5 PASS, 1 SKIPPED
(из PASS два явно mock — отказ OSTIS и timeout). Реальный вызов /health/ready без
тестовых двойников: 503, database=true, ostis=false, llm=false, mock=false — ожидаемый
отказ зависимости, НЕ успех OSTIS. C++ и исходные агенты не изменены.
OSTIS: NOT TESTED на загруженной KB; LLM: NOT TESTED. Следующий шаг S3.

S3: добавлены backend/app/llm/{schemas,prompts,interpreter}.py, test_llm.py,
e2e/test_stack.py, interpreter подключён в factory. `pytest backend/tests -q`:
9 PASS, 2 SKIPPED; пять PASS явно mock. Проверены строгая схема, отбрасывание
неподтверждённых фактов, два некорректных JSON, отказ OSTIS до LLM, baseline без LLM.
Ollama API и тег qwen3:4b-instruct сверены с официальными источниками:
https://docs.ollama.com/api/chat и https://ollama.com/library/qwen3:4b-instruct .
Живая генерация/качество модели: NOT TESTED. Gate S3 BLOCKED средой. Следующий шаг S4.

S4: добавлены auth/account, модели данных, Alembic-миграция 001, web_utils, rate_limit,
формы Jinja, подключены blueprints и запись истории только для вошедшего пользователя.
`pytest backend/tests/unit -q`: 15 PASS. Проверены два аккаунта (чужие заметки 404,
гость 401), хеши scrypt, CSRF, XSS-экранирование, календарь/даты/часовой пояс,
одноразовый код и восстановление с отзывом прежних сессий, повторяемые миграции,
сохранение записи при новом экземпляре приложения с тем же SQLite-файлом.
Выявлена и исправлена коллизия имени app.db с объектом SQLAlchemy в factory.
OSTIS/LLM: NOT TESTED; данные не подменялись. Stop/start Docker-volume: NOT TESTED.
Следующий шаг S5. DEV_LOCAL_MAIL сохраняет письма локально, отправки email нет.

S5: добавлены forum, test_module, documents, news, миграция 002 и модели,
новые страницы Jinja, SC-чтение вопросов/ответов из обеих найденных схем KB.
`pytest backend/tests -q`: 19 PASS, 2 SKIPPED; `ruff check backend`: PASS.
`docker compose config --quiet`: PASS. Реальный SQLite-форум проверен двумя сессиями:
редактирование/мягкое удаление только своих сообщений, уникальные оценки, поиск с
SQL-подобной строкой. RSS-кеш проверен mock transport с последующим отказом сети;
внешняя лента NOT TESTED. Документ — только техническая тестовая фикстура; настоящих
бланков нет, каталог честно пустой. Учебные SC-вопросы не дублируются в SQLite,
правильный ответ не отдаётся до проверки. Live-тестирование и статьи BLOCKED Docker.
Gate S5 не пройден из-за live и отсутствующего исходного контента. Следующий шаг S6.

S6: data/evaluation/queries.json содержит 36 запросов (24 точных, 6 перефразирований,
4 отрицательных, 2 без достаточного контекста) со ссылками на аудит и ожидаемые SC-ID.
Добавлены app/evaluation.py, scripts/evaluate.py, генератор набора, test_reliability.py,
test_evaluation.py, диагностика single_match_probe.
`pytest backend/tests/unit -q`: 25 PASS. Проверены корреляция двух параллельных запросов
(mock), отказ чужого request_id (mock), ограничение частоты и негативные входы.
Измерено реальное извлечение baseline (без сетевого поиска): precision=0.1021,
recall=0.8000, F1=0.1811, TP=24 FP=211 FN=6. Это кандидаты-словосочетания,
не оценка юридических ответов. Свидетельство: evidence/baseline-terms.json.
`scripts/evaluate.py` на полном стеке: SKIPPED, exit 2, причины ostis_unavailable и
llm_unavailable, метрики=null; evidence/live-evaluation.json.
Принудительный запуск `RUN_LIVE_OSTIS=1 pytest backend/tests/integration -m live_ostis`:
2 FAIL из-за недоступного sc-server; evidence/live-ostis.xml. Это НЕ live PASS.
Особенность guard size()>1: входной link самого action также попадает в SearchLinksByContent.
Поэтому «одно совпадение названия» и «одна ссылка всего» различаются. Исправлять guard
без воспроизведения нельзя. C++ не менялся. Следующий шаг S7, live-gates остаются открыты.

S7: добавлены README.md, THIRD_PARTY_NOTICES.md, ARCHITECTURE.md, API_CONTRACTS.md,
TEST_REPORT.md, scripts/run_local.py, prepare_env.py, setup_linux.py, capture_screenshots.py,
smoke_http.py, requirements-dev.txt. Сохранена лицензия upstream в ostis/UPSTREAM_LICENSE.
Инициализирован локальный Git, push/публикация не выполнялись; .env, runtime DB, кеши и
upstream checkout игнорируются. Проверены реальные HTTP-страницы и Chrome-снимки
home/requests/ostis-unavailable; скриншот 503 не является результатом юридического поиска.
Локальный backend запускается `python scripts/run_local.py`, SQLite в data/runtime.
Readiness: 503, database=true, ostis=false, llm=false, mock=false.
Обновлены матрица функций и ограничения. Настоящие бланки/RSS не подключены.
Свежая установка Docker NOT TESTED.

Дополнение S5/S7 после сверки исходного форума: реализованы персональные рекомендации
по своим просмотрам, похожие темы, обратная связь, тематические метки и лексический поиск
близких формулировок. Новые файлы forum/recommendations.py, миграция 003,
templates/recommendations.html, test_recommendations.py. Проверены две независимые
истории просмотров и обратной связи: 27 unit PASS, в том числе 8 явно mock.
Числовые веса исходного алгоритма не копировались; это собственная реализация сценария.

## Приёмка раздела 11 ТЗ

- [ ] Все источники/лицензии подтверждены: SHA и MIT корня проверены, права подмодулей/документов требуют уточнения.
- [x] Один локальный монорепозиторий с Python-приложением, pinned OSTIS и едиными launcher-ами.
- [x] setup/start/stop прошли настоящую Windows/Docker установку: журналы setup/stop, живая readiness и пользовательский поиск; свежий клон остаётся S7.
- [x] sc-machine запущен, KB собрана, WebSocket отвечает: readiness и test_real_kb_read PASS 11.11.
- [x] Python прочитал юридические элементы через SDK из живой памяти: live PASS.
- [x] Фактические SC-ID/происхождение получены в рабочем стеке: concept_rental_housing_belarus, реальные text links, повторное чтение источника.
- [x] Baseline дал настоящий результат без вызова Ollama: live поиск PASS; принудительное выключение службы Ollama отдельно не проверялось.
- [x] Локальная LLM прошла живую генерацию по JSON Schema: qwen3:4b-instruct, один настоящий запрос, evidence/llm-live.json.
- [x] Код не формирует правовой ответ из памяти LLM; ответ — выдержки OSTIS или ошибка/no_evidence.
- [ ] Полная матрица функций: пользовательское ядро и рекомендации PASS, контент/live остаются PARTIAL.
- [x] Персистентность кабинета и заметок после Docker stop/start подтверждена пользователем. Секреты игнорируются, пароли scrypt.
- [x] Unit/integration/E2E наборы и честные результаты сохранены в docs/evidence.
- [x] Полное сравнение baseline/LLM на 36 запросах выполнено с живой OSTIS и Ollama на GPU.
- [x] Ограничения среды, редакций KB, CPU/GPU, лицензий и контента описаны.

## Продолжение

Поиск, каталог документов и RSS проверены на работающем сайте. Следующая проверка
для S7 — установка из чистой копии.
Пока эти пункты открыты, проект не объявляется полностью готовым.

## Исправление запуска после пользовательской проверки, 28.10.2026

- Найден и остановлен собственный демонстрационный процесс Python из предыдущей сессии,
  занимавший 127.0.0.1:5000 (PID 7632, Waitress). Он конфликтовал с публикацией порта app
  в Docker. После остановки слушателя на порту 5000 нет; данные/тома не удалялись.
- Пользовательский запуск скачал ostis/upstream и оба подмодуля: SHA проверены, соответствуют pin.
  Изолированная среда агента сейчас получает Access denied к Docker API/WSL;
  это не доказывает отсутствия Docker у пользователя.
- setup.bat/start.bat сохраняют код возврата, оставляют окно при ошибке; manage.ps1 сохраняет
  transcript в logs, указывает этап сбоя, корректно обрабатывает прогресс stderr с exit 0.
  start проверяет наличие локальных образов и занятость порта, не останавливая чужие процессы.
- Воспроизведена ошибка прямого cmd.exe-запуска LF-батника: `NoProfile is not recognized`
  и обрезанные строки. Все четыре .bat сохранены с Windows CRLF; validate_infra.py теперь
  проверяет это условие. Прямой `cmd /c start.bat` после исправления корректно выполняет
  PowerShell, сохраняет журнал, выводит русское сообщение и возвращает exit 1 при отказе Docker.
- Изменены scripts/manage.ps1, scripts/test_manage.ps1, scripts/validate_infra.py,
  setup.bat, start.bat, stop.bat, rebuild-kb.bat, .gitignore, README.md.
  Проверки: PowerShell parser/передача аргументов PASS (mock Docker), stderr/exit codes PASS
  (настоящий Python-процесс), занятый/свободный порт PASS (настоящий TCP, mock Docker),
  validate_infra.py PASS static, ruff PASS. Запуск setup из среды агента FAIL на проверке
  Docker Engine с записью диагностического журнала; настоящая сборка не подтверждена.
- Следующий шаг: повторить пользовательский setup/start; если ошибка setup сохраняется,
  исследовать её фактический вывод из нового logs/setup-*.log. Сообщение пользователя
  пока не содержит текста исходной ошибки сборки.

## Исправление Conan TLS по пользовательскому журналу, 28.10.2026

Прочитан logs/setup-20261028-032055-15552.log. Python-образ legal-ai-python:local
успешно собран/экспортирован. Docker и WSL у пользователя работают; machine падает
на conan install: TLSV1_ALERT_INTERNAL_ERROR при обращении к conan.ostis.net.
Это установлено по фактическому логу, не по ошибке доступа в sandbox агента.

Добавлен ostis/Dockerfile: официальный Linux SDK sc-machine 0.10.0 с GitHub Releases
используется через CMAKE_PREFIX_PATH, что прямо предусмотрено документацией upstream
на commit 4ead42282b7a814edbd352f5f5650f0f4a721141. Conan больше не вызывается.
Все 14 исходных групп C++-агентов собираются прежними CMakeLists; SC_BUILD_TESTS=OFF
отключает только сборку тестовых executable, а не учебный test-module.
Добавлены системные зависимости OpenSSL/GLib/XML и проверки loader/версии/модулей
в ostis/verify_runtime.py. Исходный checkout не изменён; KB и тома не затронуты.
Docker build context перенесён в корень с whitelist .dockerignore, который не отправляет
.env, пользовательские файлы, KB, .git и модели в контекст сборки.

Изменены docker-compose.yml, .dockerignore, ostis/Dockerfile, verify_runtime.py,
SC_MACHINE_LICENSE, scripts/validate_infra.py, backend/tests/unit/test_ostis_image.py,
README и уведомления о лицензиях. `pytest backend/tests -q`: 29 PASS, 3 SKIPPED;
два новых теста явно mock, проверяют отказ при отсутствующей shared library и неверной
версии двигателя. Compose config PASS, структура build и сохранение томов подтверждены;
upstream git status чистый. Сборка `docker compose --progress plain build machine`
из sandbox агента FAIL до выполнения Dockerfile: Access denied к Docker/context.
Успех настоящей пересборки не заявляется. Следующий шаг: повторный setup.bat у пользователя;
проверить фактический CMake build, затем KB, WebSocket и локальную модель.

## Очистка места по запросу пользователя, 28.10.2026

Проверка диска: около 1 ГиБ свободно. Docker disk/docker_data.vhdx занимает 15.32 ГиБ
(и логический, и выделенный размер); установленный pip сообщает кеш 512.8 МБ.
Сам проект вне Docker около 300 МиБ: исходный upstream 170 МиБ, .venv 107 МиБ,
временные Chrome-профили около 20 МиБ. Не весь Docker VHDX является мусором.

Из workspace фактически удалено 20 579 151 байт (19.63 МиБ) собственных временных
Chrome-профилей и кешей pytest/ruff. Перед рекурсивным удалением проверены абсолютные
пути внутри workspace и отсутствие reparse points. Хеши .env и data/runtime/app.sqlite3
до/после совпали. Исходники, модели, тома, логи и установленные пакеты сохранены.
Свободное место после этой операции: 1 094 422 528 байт (около 1.02 ГиБ).
Отчёт операции: docs/evidence/disk-cleanup.json.

Попытка `docker builder prune --all --force` из sandbox агента: FAIL/Access denied
к Docker API. Кеш Docker этим сеансом не очищен. Глобальный pip-кеш расположен вне
разрешённого workspace и не удалялся агентом.
Подготовлены cleanup.bat и scripts/cleanup_space.ps1: из пользовательского Windows-сеанса
очищают только неиспользуемый build cache Docker и pip-кеш, оставляя образы/контейнеры/тома.
Есть журнал logs/cleanup-*.log, проверка свободного места, режим отчёта без удаления.
Принудительное сжатие/удаление VHDX и выключение WSL не выполняются.
Проверки: PowerShell parse и ProjectOnly/ReportOnly PASS, фактическая очистка workspace PASS.
Для основной очистки нужен запуск cleanup.bat в пользовательском сеансе с Docker-доступом.

### Результат пользовательского запуска очистки, 28.10.2026

Журнал `logs/cleanup-20261028-034551-23348.log` подтверждает реальную очистку:
Docker builder prune удалил 2.013 GB, после операции Build Cache = 0 B;
pip cache purge удалил 418 файлов (до очистки HTTP-кеш 512.8 MB и wheels 29 kB).
Windows: свободно до 1 130 504 192 байт, после 1 606 742 016 байт (+454.18 МиБ).
Образы (12.14 GB), контейнер и тома сохранены. VHDX остаётся около 15.34 ГиБ:
освобождение блоков внутри Docker не равнозначно немедленному возврату места Windows.
Строка «0 МиБ» относилась только к уже очищенным кешам проекта; итог скрипта уточнён,
чтобы отдельно показывать успешность очистки Docker/pip и изменение свободного места Windows.

На D: обнаружено около 145 ГиБ свободного места. Следующий шаг для освобождения C:
— штатный перенос Docker disk image через Docker Desktop Settings → Resources → Advanced
в `D:\DockerDesktop`, затем Apply (или Apply & Restart). Это рекомендация, перенос не выполнен:
из sandbox нет доступа к управлению Docker и записи вне workspace. Ручное перемещение/удаление VHDX
не выполнялось. Штатный путь подтверждён документацией https://docs.docker.com/desktop/features/wsl/.
Состояние live OSTIS/LLM этим запуском очистки не проверялось.
Проверки обновлённого скрипта: `cleanup_space.ps1 -ProjectOnly -ReportOnly` PASS
(без удаления), `python scripts/validate_infra.py` PASS static, UTF-8 BOM PowerShell PASS.

## После переноса Docker на D:, исправление сборки GWF, 28.10.2026

S1 PARTIAL. Пользователь перенёс хранилище Docker. Проверка файлов подтверждает
`D:\DockerDesktop\DockerDesktopWSL\disk\docker_data.vhdx` (15.33 ГиБ),
на C: свободно 16.87 ГиБ, на D: 129.83 ГиБ. VHDX в прежнем каталоге на C: не обнаружен.
Никаких файлов хранилища агент не перемещал и не удалял.

Исследован более новый журнал `logs/setup-20261028-033233-25752.log`:
оба образа успешно собраны; `verify_runtime.py` подтвердил настоящий SDK sc-machine 0.10.0,
динамические библиотеки и 14 групп C++-агентов. Это подтверждение сборки образа пользователем,
не LIVE PASS для KB/WS. Последующий sc-builder остановился на файле 9/1469:
GWFTranslator не смог записать `question_model.gwf.generated.scs` рядом с исходником,
поскольку upstream подключён как read-only. Сборка KB FAIL, загрузка Ollama ещё не выполнялась.

Исправления: новый `ostis/entrypoint.py` перед запуском настоящего sc-builder копирует
исходники во временный записываемый каталог с сохранением относительных путей и ресурсов,
исключая `.git`. Оригинальное подключение `:ro` сохранено. Временная копия удаляется
после успешной/неуспешной сборки. Команда run передаётся штатному upstream entrypoint.
Dockerfile и .dockerignore включают обёртку; дублирующий Compose init удалён,
поскольку образ уже запускается через tini.

setup теперь может продолжить после частичной сборки: если KB непустая и маркера успешной
установки нет, app/machine останавливаются, KB сохраняется в `backups/kb-ДАТА-PID.tar`,
проверяются ненулевой размер и чтение архива через tar. Только после успешного бэкапа
разрешена повторная сборка; готовая KB пропускается. Пересборка по rebuild использует ту же
функцию резервного копирования и снимает старый маркер готовности перед сборкой.
Модели, SQLite и тома не удаляются.

Изменены: ostis/entrypoint.py, ostis/Dockerfile, .dockerignore, docker-compose.yml,
scripts/manage.ps1, scripts/test_manage.ps1, scripts/validate_infra.py,
backend/tests/unit/test_kb_build.py, README.md, docs/STATUS.md, docs/DECISIONS.md.
Проверки: `.venv/Scripts/python.exe -m pytest backend/tests -q` — 31 PASS, 3 SKIPPED live;
два новых параметризованных теста явно mock: запись GWF в копии, сохранение исходников,
очистка временного каталога и сохранение exit code. `scripts/test_manage.ps1` PASS
(mock Docker: порядок backup/build/marker, отказ бэкапа/сборщика, пропуск готовой KB;
native Python stderr/exit, native TCP). Ruff и validate_infra.py PASS;
`docker compose config --quiet` PASS (предупреждение о недоступном пользовательском config).
Upstream git status чистый. PowerShell UTF-8 BOM сохранён.

Доступ агента к Docker API всё ещё FAIL/permission denied; сборка обновлённого образа
и LIVE OSTIS/LLM NOT TESTED. Следующий шаг: пользовательский `setup.bat`, затем после
успешной установки `start.bat`; при сбое изучить новый logs/setup-*.log.

## Исправление запуска миграций в Docker, 28.10.2026

S1/S4 PARTIAL. Прочитан `logs/setup-20261028-035754-25040.log`.
Резервный архив незавершённой KB создан и проверен; исправленная GWF-сборка обработала
1469/1469 файлов, итоговый счётчик 441980. Ollama успешно скачал и проверил
`qwen3:4b-instruct`. Ошибка произошла после этих шагов, при создании Flask-приложения
перед миграцией: `IndexError: 3` в `backend/app/config.py`.

Причина: путь `/app/app/config.py` в Docker имеет меньше родителей, чем предполагал
`parents[3]`. Даже заданный DOCUMENT_CATALOG не помогал: аргумент по умолчанию os.getenv
вычислялся до вызова. Дополнительно выявлено неверное смещение локального каталога документов
на один уровень вверх. Теперь пути определяются от каталога пакета: checkout использует
`data/documents/catalog.json`, контейнер — `/app/documents/catalog.json`; явные настройки
окружения сохраняют приоритет. Путь dev-mail по умолчанию согласован с APP_INSTANCE_PATH.

В Dockerfile после USER legal добавлен запуск настоящего `python -m app db-upgrade`
на SQLite в памяти: без существующих данных/томов и обращений к OSTIS/LLM,
со случайным временным SECRET_KEY. Проверка выполняется во время сборки с путями контейнера
и тем же непривилегированным пользователем. Она не заменяет миграцию постоянной БД в setup.

Изменены backend/app/config.py, backend/Dockerfile,
backend/tests/unit/test_config.py, backend/tests/integration/test_migrations.py,
docs/STATUS.md, docs/DECISIONS.md.
Регрессия до исправления: 3 FAIL, 1 PASS (включая воспроизведение IndexError при заданном
DOCUMENT_CATALOG). После исправления: `.venv/Scripts/python.exe -m pytest backend/tests -q`
— 36 PASS, 3 SKIPPED live; 4 новых теста путей явно mock (расположение модуля),
1 новый тест настоящего CLI/SQLite проверяет новую БД, повторный upgrade, сохранение
пользователя/заметки и версию 003_recommendations. Ruff и validate_infra.py PASS.
Тесты выполнены на хостовом Python 3.12; Dockerfile целевой Python 3.11.14 ещё не пересобран.

Прямая проверка http://127.0.0.1:11434/api/tags PASS: модель qwen3:4b-instruct присутствует.
Прямой вызов OstisClient.ready() на ws://127.0.0.1:8090/ws_json FAIL:
готовность живой KB не подтверждена, это не отменяет успешного sc-builder в журнале setup.
Docker API из sandbox по-прежнему FAIL/permission denied. Следующий шаг:
повторный пользовательский setup.bat для пересборки только изменившегося Python-образа
и миграции; готовая KB по маркеру пропускается, скачанная модель сохраняется.
После успеха — start.bat и live OSTIS/LLM/E2E.

Дополнительная реальная проверка S3: OllamaInterpreter.interpret() через локальный
http://127.0.0.1:11434 вернул JSON, прошедший строгую схему Interpretation и check_grounding,
для запроса «Что такое арендное жилье?» за 53.203 с. Модель qwen3:4b-instruct,
mock=false; `docs/evidence/llm-live.json`. Это LIVE PASS только для интерпретации одного
запроса, не юридический ответ, не оценка качества и не E2E с OSTIS. В кандидатах есть
лишние расширения, включая упоминание России: они не являются подтверждёнными фактами
и не должны попадать в правовой ответ без источников OSTIS; полный evaluator остаётся открыт.
Попытка `docker compose --progress plain build app` из сеанса агента — FAIL до Dockerfile:
`unable to prepare context: unable to evaluate symlinks in context path: Access is denied`.
Успех проверки миграций внутри обновлённого образа пока не заявляется.

## Проверка журналов и инструкция проверки, 11.11.2026

Изучены более новые пользовательские журналы:
`logs/setup-20261028-143418-27240.log` — PASS: проверка миграций при сборке образа,
миграция постоянной SQLite и сообщение «Первичная установка завершена».
Готовая KB была пропущена, модель сохранена.
`logs/start-20261028-143445-28204.log` — machine и ollama Healthy, app Started;
полная readiness приложения в журнале не зафиксирована. Есть ранняя ошибка HTTP-соединения,
окончательный успех юридического поиска из неё не следует.
`logs/stop-20261028-143628-27548.log` — все три контейнера остановлены.

Текущие прямые проверки HTTP 11.11: /health/live, /health/ready и Ollama /api/tags
не отвечают (connection refused). Это не новая ошибка установки: сервисы сейчас недоступны.
Рекомендована проверка после start.bat: все компоненты /health/ready=true и mock=false,
реальный запрос «Что такое арендное жилье?» в baseline и llm, открытие источника с SC-ID,
сохранение пользовательских данных после stop/start. Для автоматической live-проверки
нужны RUN_LIVE_OSTIS=1, RUN_LIVE_STACK=1 и адреса localhost вместо Docker-имён.
Повторный setup по этим журналам не требуется. Код не изменён, тесты приложения не повторялись.

## Реальный поиск, исправление live-тестов и привязка LLM к словарю, 11.11.2026

S2–S4/S6 PARTIAL по полной приёмке. Пользователь получил concept_rental_housing_belarus
в классическом и LLM-режиме и подтвердил сохранение кабинета и заметок после stop/start.
Живая readiness: HTTP 200, database/ostis/llm=true, mock=false. Пользовательский pytest:
test_real_kb_read PASS, test_existing_agent_single_title_link FAIL, 2 ERROR из-за ACL
AppData/Local/Temp/pytest-of-user, а также предупреждения о .pytest_cache.

Подтверждено независимо: action_user_request завершился с result_nodes_count=0,
source_count=0. Успех завершения не означает наличие ответа. Ранее прочитанный upstream
требует несколько связей одновременно и использует singular-отношения, в KB есть plural-варианты.
Проба считает title-ссылки отдельно от накопившихся input links. XFAIL фиксирует известный
пустой результат C++-агента; fallback отдельно проверяет реальные источники. В приложении
переход к шаблонам выполняется и при наличии узлов агента без пригодных источников.
Новые поля trace result_nodes_count/source_count и reason=agent_no_sources объясняют результат.
Upstream не изменён; C++-агент остаётся ограниченным. Изменения прав/удаления томов не выполнялись.

В pytest: отдельный временный каталог каждого сеанса, временный APP_INSTANCE_PATH для fixture,
без постоянного cacheprovider. Первоначальный повторный прогон — 40 PASS, 1 XFAIL, без ACL-ошибок,
с реальной цепочкой Flask → локальная LLM → OSTIS. Свидетельство: evidence/live-20261111.xml.
Последующие тесты словаря: unit+SQLite CLI 39 PASS; live OSTIS 2 PASS, 1 XFAIL.
Baseline с отсутствующим интерпретатором дал реальные concept_rental_housing_belarus
и by_act_hk1200428_article_1; evidence/ostis-baseline-live-20261111.json.

До привязки к KB модель добавляла непроверенные формулировки (включая «в России»).
После ограничения prompt точный запрос стал короче, но перефразированные Q25/Q29 всё ещё
не находились (1/3 ожидаемых источников в обоих режимах). Добавлено реальное чтение
названий из belarus_legal_term через nrel_main_idtf/lang_ru: 193 термина из 209 членов
в текущей памяти. Локальная модель выбирает из них с enum и проверкой Python.
Выдержки по-прежнему читает OSTIS; новые термины, правовые нормы или SC-ID не выдумываются.
На тех же трёх содержательных вопросах LLM теперь нашла 3/3 ожидаемых источников,
baseline 1/3; два контрольных запроса правильно остались no_evidence в обоих режимах.
Время на CPU 97–121 с LLM, 1–3 с baseline в этом прогоне. У Q29 есть два лишних, но реальных
источника. Полная оценка 36 запросов остаётся открытой. Отчёт и измерения: TEST_REPORT.md,
evidence/mode-comparison-grounded-20261111.json.

Изменены backend/app/{__init__.py,legal/service.py,llm/{interpreter,prompts}.py,
ostis/{client,memory,worker}.py,templates/search.html}, pyproject.toml,
backend/tests/{conftest.py,integration/test_ostis.py,unit/{test_llm,test_ostis_fallback}.py},
README и документация/свидетельства. Ruff, validate_infra.py и git diff --check PASS.
Docker API по-прежнему недоступен агенту. Изменения протестированы на хостовом приложении
с настоящими Docker OSTIS/Ollama; работающий контейнер app ещё не обновлён.
Для применения: `docker compose build app`, затем `docker compose up -d --no-deps app`.
Финальный набор после привязки к словарю: `pytest backend/tests -q` с RUN_LIVE_OSTIS=1
и RUN_LIVE_STACK=1 — **42 PASS, 1 XFAIL**, 122.93 с, exit 0.
E2E прошёл с обновлённым LLM-конвейером и настоящими службами; осталось одно предупреждение
о deprecated имени модуля в py-sc-client. Свидетельство: evidence/live-grounded-20261111.xml.

## Подключение NVIDIA к Ollama, 11.11.2026

Пользователь получил 504 при ожидании LLM. Хостовый nvidia-smi обнаружил RTX 3050 Laptop,
4096 МиБ и драйвер 572.70. WSL сообщает версию 3.0.5. Ollama /api/ps для qwen3:4b-instruct
показал size_vram=0 при контексте 4096. HTTP readiness приложения 200.

Добавлен compose.gpu.yml с резервированием одного NVIDIA GPU только для Ollama.
Локальный `.env` подключает этот файл через COMPOSE_FILE при запуске из Windows.
Проверка Compose config PASS. Сравнение CPU/GPU конфигураций подтвердило одинаковые
имя проекта, образы, порты и тома. Пользователь пересоздал Ollama из своего сеанса.
Сквозная проверка на сайте PASS: вопрос «Я поступаю в вуз. Как называют поступающего?»
сопоставлен с «абитуриент» и вернул выдержку из concept_applicant_belarus через SC-шаблон.
`docker compose exec -T ollama ollama ps` показал 100% GPU и контекст 4096.
Независимый запрос `/api/ps` подтвердил `size_vram=size=3571659904` для qwen3:4b-instruct.
Сравнительный замер приведён в следующем разделе.

## Полная оценка S6 на GPU, 11.11.2026

`scripts/evaluate.py --progress --output docs/evidence/evaluation-gpu-20261111.json` обработал
36 запросов в каждом режиме на живом стеке. Все 72 выполнения завершились без технических
ошибок и таймаутов. В scripts/evaluate.py добавлены прогресс и время ответа отдельно от
перечитывания источников. Ruff PASS, test_evaluation.py PASS. В ходе оценки `/api/ps`
подтвердил размещение qwen3:4b-instruct целиком на RTX 3050 с контекстом 4096.

Ожидаемый источник найден в 23/30 содержательных вопросов классическим поиском и 26/30 с LLM.
Из 6 перефразированных запросов LLM нашла 6 ожидаемых источников, baseline — 0.
Медиана времени самого запроса 1.33 и 13.78 с соответственно. Для пяти общих вопросов
медиана прогона с LLM, включая повторное чтение источников, снизилась со 111.73 с на CPU
до 14.11 с на GPU. Подробные метрики и четыре пропуска LLM описаны в TEST_REPORT.md.

## Точные названия и учебные тесты, 11.11.2026

Общая нормализация принимает запятые и скобки в названиях из OSTIS. Для явного названия
словарь запроса к LLM сужается до одного термина, прочитанного из KB. Точные совпадения
SC-шаблона располагаются перед связанными источниками агента с удалением дублей по ID.
Изменены search_baseline.py, service.py, schemas.py и memory.py.

Повторный live-прогон на GPU нашёл ожидаемые источники в обоих режимах для Q03, Q14, Q15
и Q23. Контроль Q25 по-прежнему находит «абитуриент» через LLM. Свидетельство в
`evidence/search-regressions-20261111.json`. Метрики полного прогона 36 вопросов относятся
к версии до этих исправлений.

`backend/tests/integration/test_quiz.py` прошёл раунд с двумя вопросами из живой OSTIS,
неверным и верным ответами, счётом 1 из 2 и завершением раунда. Аккаунт и попытки созданы
в изолированной тестовой SQLite. Добавлена проверка порядка источников в test_ostis.py.
Pytest с RUN_LIVE_OSTIS=1 дал 43 PASS, 1 XFAIL и 1 SKIPPED. Flask E2E с LLM выключен
в этом прогоне. Реальные LLM и OSTIS проверены отдельным прогоном пяти вопросов.
Ruff PASS. JUnit сохранён в `evidence/search-quiz-20261111.xml`.

Docker Engine отклонил подключение из сеанса агента. Для применения на сайте нужны
`docker compose build app` и `docker compose up -d --no-deps app` из пользовательского PowerShell.
Последующая проверка работающего сайта подтвердила обновление. Классический запрос
«воспитание» вернул `concept_education_belarus` первым и `reason=exact_title` в trace.

## Варианты ответов в учебном тесте, 11.11.2026

Проверка живой OSTIS насчитала 30 доступных уникальных вопросов. До исправления
правильный вариант занимал первую позицию во всех 30. В `test_module/routes.py`
варианты перемешиваются по идентификаторам раунда и вопроса. Один вопрос внутри
раунда сохраняет порядок при повторном чтении и в обоих API учебного теста.
Проверка по идентификатору ответа использует исходную разметку OSTIS.

Ruff PASS. Учебный live-тест и проверки разделов дали 5 PASS. Расширенный live-тест
отдельно подтвердил разные позиции правильного ответа между раундами и дал 1 PASS.
Пользователь прошёл все 30 вопросов и сообщил о пересборке и запуске контейнера app.
После запуска `/health/ready` подтвердил доступность SQLite, OSTIS и Ollama.

## Документы из Национального архива, 11.11.2026

Добавлены три текстовых шаблона проекта в data/documents. Для учёбы и стажа использованы
опубликованные образцы НАРБ. Для читального зала использован список полей заказа НАРБ.
Ссылки на страницы учреждения находятся в catalog.json. Исходные образцы доступны
на сайте архива. Заполненные версии скачиваются как TXT.

На работающем сайте проверены открытие всех трёх карточек, заполнение с CSRF и точное
содержимое скачиваемых файлов. Тест пустого каталога переведён на отдельную фикстуру.
Обычный каталог читается из подключённого тома data/documents.

## Настройка RSS, 11.11.2026

В локальном `.env` задан `NEWS_RSS_URLS=https://bielarus.fyi/index.xml`.
Это лента стороннего трекера публикаций pravo.by. Источник и адрес ленты подтверждены
на сайте издателя. [Описание трекера](https://bielarus.fyi/about/).

Тесты разделов приложения PASS (4 теста). Реальный запрос через refresh_feeds
в тестовой SQLite завершился ConnectError из сеанса агента. Доступ к Docker API
также отклонён. Для проверки загрузки в пользовательском сеансе используется
`docker compose exec -T -e NEWS_RSS_URLS=https://bielarus.fyi/index.xml app python -m app refresh-news`.
Приёмка RSS ожидает PASS с записями и их отображения на `/news`.

Пользовательский запуск в Docker вернул FAIL/ValueError. Старая версия команды скрывала
текст исключения. В `news/service.py` добавлена выдача `detail` для ValueError.
Тест отказа по размеру ленты подтвердил сообщение и сохранение кеша. Pytest для
test_community.py дал 4 PASS, Ruff PASS. Причина отказа реальной ленты требует
диагностики из пользовательского контейнера.

Диагностика пользователя подтвердила превышение 2 МБ. В `news/service.py` загрузка
завершается при получении первых 100 полных записей RSS/Atom. Если раньше достигнут
предел в 8 МБ, сохраняются уже полностью прочитанные записи. Счётчик CLI показывает
количество сохранённых записей с допустимыми ссылками.

Pytest для `test_community.py` дал 6 PASS. Две проверки подтвердили раннюю остановку
на RSS и Atom. Отдельная проверка подтвердила, что при достижении лимита неполная
запись отбрасывается. Ruff PASS. Docker Engine и прямой запрос к источнику из сеанса
агента недоступны. Реальный повторный импорт ожидает пересборки app у пользователя.

После пересборки пользовательский импорт реальной ленты вернул PASS и 100 записей.
Работающая страница `/news` ответила HTTP 200, показала 100 карточек и ссылки на источник.

## S7. Проверка первичной установки на Windows

Для проверки подготовлена локальная копия исходников в `reports/s7-clean-install`.
В репозитории пока нет коммитов, поэтому свежий Git checkout остаётся непроверенным.
Копия начинается без `.env`, базы SQLite, виртуального окружения и `ostis/upstream`.
В копии `verify-install.bat` вызывает `setup.bat`, `start.bat` и `/health/ready`.
Проверка `docker compose config` подтвердила отдельные имя проекта, образы приложения
и OSTIS, тома и порты `5037`, `8097`, `11437`.

В копии `scripts/validate_infra.py` дал PASS. Pytest для `backend/tests/unit` и
`backend/tests/integration/test_migrations.py` дал 41 PASS с предупреждением
об устаревшем импорте в `sc_client`. Использовалось существующее окружение Python.
Пользователь успешно выполнил `.\reports\s7-clean-install\verify-install.bat`.
Повторный запрос `curl.exe -fsS --max-time 6 http://127.0.0.1:5037/health/ready`
вернул `{"database":true,"llm":true,"mock":false,"ostis":true}`.
Первичная установка из отдельной локальной копии и готовность реальных служб — PASS.
Свежий клон с GitHub получен на коммите `7ccdd97`. Для запуска параллельно с рабочим
сайтом в клоне настроены отдельные порты `5038`, `8098`, `11438`, тома и метки образов.
`docker compose config` и `git diff --check` прошли. Пользователь успешно выполнил
`.\reports\s7-github-clone\verify-install.bat`. Повторный запрос к `/health/ready` на
порту `5038` подтвердил SQLite, реальный OSTIS и локальный Ollama (`mock=false`).
Проверка S7 пройдена. Тестовый стек можно остановить той же командой с аргументом `stop`.
