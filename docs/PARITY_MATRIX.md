# Матрица совместимости

Собственная реализация по поведению; код sc-legislation-app не копируется.
Результаты реализации ниже; live-приёмка отделена от проверки пользовательских функций.

| Функция | Исходные маршруты / данные | Новый маршрут | Стадия / проверка |
|---|---|---|---|
| Гость | /guest_mode, сессия | /guest_mode, открытые страницы | S4, guest |
| Вход, регистрация, проверка | /auth /reg /verification, агенты регистрации | те же + /recover | S4, auth |
| Профиль и настройки | /api/profile /api/settings, cabinet agents | те же, /cabinet | S4, ownership |
| Юридические запросы | /requests /requests_results, action_user_request | /requests, /api/legal/query | S2–S3, live_ostis/live_stack |
| Справочник | /directory /directory_results, search-module | /directory, /api/legal/concepts | S2, live_ostis |
| Статьи | /article/<id>, SC + статический fallback одного кодекса | /article/<id>, /api/legal/sources/<id> | S2/S5, live_ostis |
| История | /api/history, cabinet agents | тот же | S4, ownership/persistence |
| Заметки, закладки | /api/notes /api/bookmarks | те же | S4, ownership |
| Календарь | /show_calendar /add_event /delete_event | /show_calendar, /api/calendar | S4, ownership |
| Форум | /forum /forum/create_topic /forum/topic/<id>, сообщения/оценки/поиск | /forum, /api/forum/topics, /api/forum/posts | S5, forum ownership |
| Учебные тесты | /test /api/test/*, test-module | /test /api/test/* | S5, live_ostis; только проверенные в KB вопросы |
| Шаблоны | /templates, три неработающие кнопки без бланков | /templates, /templates/<id> | S5, заполнение и скачивание трёх шаблонов по материалам НАРБ проверены |
| Новости | /news, filtered_news SQLite/RSS | /news, CLI refresh-news | S5, реальный импорт 100 записей и вывод на странице PASS |

Незавершённые live-gates и контентные блокировки не считаются пройденной совместимостью.

## Итог проверки

- Аккаунты, профиль, настройки, заметки, календарь и файловая персистентность:
  [test_accounts.py](../backend/tests/unit/test_accounts.py), PASS на настоящей SQLite.
  Docker stop/start и перенос прежних SC-пользователей не проверены/не выполнялись.
- Юридический поиск, справочник и статьи: код реализован, тесты
  [test_ostis.py](../backend/tests/integration/test_ostis.py) дают 2 FAIL без службы;
  [test_stack.py](../backend/tests/e2e/test_stack.py) даёт 503 без OSTIS.
  Подтверждённых юридических результатов в этой среде нет.
- Форум, сообщения/оценки/поиск: [test_community.py](../backend/tests/unit/test_community.py), PASS.
  Персональные/похожие рекомендации, обратная связь, метки и поиск близких формулировок:
  [test_recommendations.py](../backend/tests/unit/test_recommendations.py), PASS на настоящей SQLite.
  Алгоритм реализован независимо; числовые веса старой системы не копировались.
- Учебные вопросы проверены на живой OSTIS. Приложение загрузило два разных вопроса,
  оценило ответы по разметке KB и завершило раунд со счётом 1 из 2.
  [Live-тест](../backend/tests/integration/test_quiz.py).
- Документы: три текстовых шаблона по опубликованным образцам и полям НАРБ.
  Каталог, открытие, заполнение и скачивание проверены на работающем сайте.
- Новости: ручное обновление через CLI прошло на реальной ленте bielarus.fyi.
  На странице показаны 100 записей со ссылками. Отказ сети сохраняет кеш по тесту.
- Все разделы доступны из меню. Публичные страницы подтверждены HTTP/Chrome,
  приватные страницы — вошедшей тестовой сессией. Итоговый S5 остаётся PARTIAL.
