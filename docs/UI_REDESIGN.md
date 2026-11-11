# Визуальная переработка — S4/S5, 11.11.2026

## Аудит до изменений

Прочитаны IMPLEMENTATION_SPEC.md, REPO_AUDIT.md, все 16 шаблонов, app.css,
app.js и маршруты legal, auth, account, forum, documents, news, test_module.
Исходная проверка: 59 unit-тестов PASS, одно предупреждение upstream sc_client.

- Горизонтальное меню из девяти пунктов плохо масштабируется на узких экранах.
- Одинаковые белые скруглённые панели не различают формы, источники и обсуждения.
- Поисковый экран не выделяет основной ввод, режим и происхождение результатов.
- Длинные идентификаторы, даты и тексты требуют правил переноса и ограничения длины строки.
- Личный кабинет не имеет внутреннего оглавления; формы и история сливаются.
- Отсутствуют оформленные состояния загрузки, явный клавиатурный фокус и mobile navigation.

## Дизайн-система

Направление: современный юридический архив. Бумага #f6f3ed, светлый лист #fffdf8,
чернила #202d35, бордо #7b3442, вторичный текст #666961, линии #d9d5cb.
Serif Georgia/Times New Roman для заголовков и редакционных акцентов;
Segoe UI/system-ui для форм и навигации. Все шрифты доступны без CDN.
Шкала отступов: 4, 8, 12, 16, 24, 32, 48, 64 px. Скругления 2–4 px.

Боковое оглавление на desktop; раскрываемая навигация до 1000 px.
Основная область до 1440 px, читаемый текст до 76ch. Две колонки переходят
в одну на tablet/mobile. Источники — нумерованный реестр, юридический текст —
документный лист, форум/новости — редакционные списки, личные данные — секции.
Анимации короткие; prefers-reduced-motion отключает движение.

## Контракты, которые необходимо сохранить

- Все URL, HTTP-методы, CSRF-поля и meta csrf-token; window.localApi.
- search.html: term/query, mode=baseline|llm, ограничения 200/1500, selected_mode.
- Все ветвления answer, interpretation, matches, situation, unmatched_terms, trace;
  реальный source.id, sc_identifier/sc_address, currency и provenance.
- auth.html: kind, email, display_name, user_type, password, token; resend_code и guest_mode.
- cabinet/calendar: action=add|edit|delete, id, source_id, имена полей профиля,
  mode, timezone, text, title, starts_at, description, все серверные actions.
- forum: три независимых GET-формы, semantic=1, tag, term; body, title;
  кнопки action, vote и useful сохраняют name/value отправленной кнопки.
- test: action=start|answer|next|finish, question_id, answer_id и quiz_round.
- document: динамические fields и обычная отправка формы со скачиванием TXT.

Редизайн не включает Python runtime, модели, маршруты, зависимости, данные,
интеграции, публикацию или новые продуктовые функции.

## Реализовано

Обновлены все 16 шаблонов backend/app/templates, app.css, app.js; добавлен локальный
favicon.svg. Общий каркас содержит оглавление из всех восьми разделов, активную
страницу, вход/выход, skip link и доступное мобильное меню с Escape/возвратом фокуса.
Без JavaScript оглавление остаётся раскрытым, формы работают через обычную отправку.

- Главная: редакционная композиция и лист с порядком исследования.
- Запрос/справочник: рабочая форма, native selector режима, состояние ожидания,
  нумерованный реестр, идентификаторы, отсутствие результатов, контекст и уточнения.
- Источник: читаемый лист с мерой 76ch, редакция, закладка, связи и provenance.
- Кабинет: внутреннее оглавление, профиль, настройки, заметки, закладки, история.
- Календарь: журнал событий и отдельная форма добавления.
- Документы: реестр бланков, просмотр текста и форма скачивания TXT.
- Форум: список обсуждений, отдельные исходные фильтры, ответы, оценки, рекомендации.
- Новости: редакционная лента с датами и состоянием RSS.
- Тесты: отдельная форма вопроса, выбор ответа и результаты учебной проверки.
- Авторизация: все четыре состояния kind и повторная выдача кода.
- Ошибки: единый экран с кодом, исходным сообщением и возвратом к запросам.

## Проверки и свидетельства

| Проверка | Команда | Результат |
|---|---|---|
| Исходный unit baseline | `.venv/Scripts/python.exe -m pytest backend/tests/unit -q -p no:cacheprovider` | 59 PASS |
| Доступный набор после редизайна | `.venv/Scripts/python.exe -m pytest backend/tests -q -p no:cacheprovider` | 62 PASS, 15 SKIPPED |
| Live Flask → LLM → OSTIS, live учебный тест | `RUN_LIVE_OSTIS=1 RUN_LIVE_STACK=1 .venv/Scripts/python.exe -m pytest backend/tests/e2e/test_stack.py backend/tests/integration/test_quiz.py -q` | 2 PASS, 43.84 с |
| Python lint | `.venv/Scripts/python.exe -m ruff check backend` | PASS |
| JavaScript syntax | `node --check backend/app/static/app.js` | PASS |
| Сравнение исходных/новых форм | `.venv/Scripts/python.exe reports/redesign_contracts.py` | 42 PASS, mock render |
| Headless Edge | `node reports/redesign_browser.mjs` | 97 PASS, 0 FAIL; [browser report](evidence/redesign-browser.json) |
| Сборка/применение | `docker compose build app`, `docker compose up -d --no-deps app` | PASS; обновлён только app |

Сравнение форм проверяет методы, action, name, type, value, selected, required,
minlength/maxlength, включая динамические поля документов, оба состояния авторизации,
radio и значения submitter. [42 проверки](evidence/redesign-contracts.json) выполнены
на оригинальных шаблонах, сохранённых до редизайна, и новых с одинаковым контекстом.
Юридические объекты этого сравнения явно помечены MOCK и используются только при render.

Браузер проверяет 17 маршрутов на 360, 768, 1280 и 1920 px: главную, запрос, справочник,
каталог и бланк, форум/тему/создание темы, новости, кабинет, календарь, тест,
вход, регистрацию, восстановление, подтверждение и ошибку 404. Дополнительно проверены
живые источники, LLM-уточнение без выдуманной выдачи и настоящий вопрос OSTIS.
Ошибок JavaScript и горизонтальных переполнений не обнаружено.

Через реальные HTML-формы в изолированной SQLite проверены профиль, режим поиска,
создание/редактирование/удаление заметки, добавление закладки реального источника,
добавление/удаление события, ответ и оценка на форуме, учебный ответ и скачивание TXT.
Проверены мобильное меню, Escape/фокус, prefers-reduced-motion, навигация без JS,
контраст подписей меню/placeholder и границ полей. Все правовые тексты/ID в браузере
получены от действующего OSTIS; локальная Ollama не подменялась.

QA-приложение использовало временную SQLite в памяти на порту 5056. Записи для проверки
кабинета и форума не добавлялись в пользовательскую БД. Временные помощники находятся
в игнорируемом reports/, исходный снимок шаблонов — в .cache/redesign-baseline/.

## Снимки и работающее приложение

- [Главная desktop](screenshots/redesign/home-running-1280.png), [mobile](screenshots/redesign/home-running-360.png) — обновлённое приложение на 5000.
- [Запрос desktop](screenshots/redesign/requests-1280.png), [mobile](screenshots/redesign/requests-360.png).
- [Реальная выдача OSTIS](screenshots/redesign/results-1280.png), [источник mobile](screenshots/redesign/source-360.png).
- [Уточнение LLM](screenshots/redesign/clarification-1280.png), [mobile](screenshots/redesign/clarification-360.png).
- [Кабинет](screenshots/redesign/cabinet-1280.png), [форум](screenshots/redesign/forum-1280.png), [вопрос теста](screenshots/redesign/quiz-question-360.png).

Локальный сайт: http://127.0.0.1:5000. После применения `/health/ready` вернул HTTP 200,
database=true, ostis=true, llm=true, mock=false; CSS/JS совпали с файлами checkout.
[Свидетельство runtime](evidence/redesign-runtime.json).

## Ограничения проверки

В общем прогоне 15 live-тестов SKIPPED из-за отсутствующих флагов запуска;
два целевых live-теста затем запущены отдельно и прошли. Полная переоценка качества
LLM и всех сценариев S0–S7 не выполнялась: это фронтенд-итерация S4/S5.
Browser QA выполнена в установленном Chromium/Edge; Firefox, Safari, реальный телефон
и проверка экранным диктором не проводились. RSS-сеть не обновлялась; браузер проверил
пустую ленту, исходный тест кеша новостей и mock render заполненной ленты прошли.
Осталось upstream DeprecationWarning sc_client; Python runtime не менялся.
