# Сторонние компоненты

- ostis-apps/ostis-legislation, SHA `903e0c1e38dec25ba2f6ab4a9d5e82fe175d8e38`:
  MIT, Copyright (c) 2025 OSTIS Applications. Полный текст: [ostis/UPSTREAM_LICENSE](ostis/UPSTREAM_LICENSE).
  Исходники подключаются локальным pinned checkout, а не публикуются заново этой сессией.
- sc-machine 0.10.0, py-sc-client 0.4.0, py-sc-kpm 0.4.0 — отдельные upstream OSTIS;
  SDK движка загружается собственным ostis/Dockerfile из официального GitHub Release 0.10.0.
  Лицензия движка сохранена в [ostis/SC_MACHINE_LICENSE](ostis/SC_MACHINE_LICENSE)
  и копируется в образ; лицензии Python SDK остаются в установленных пакетах.
- sc-web `058ed9482806d41ea3190228ea595029f2450a27` и ims.ostis.kb
  `592145835643500878d5fc837df99009cd756c24`: проверка корневых деревьев не обнаружила
  отдельного LICENSE. Права на перераспространение вложенных компонентов/документов остаются
  непроверенными. Checkout игнорируется Git; публичная поставка контейнеров не выполнялась.
- SharkoStepan/sc-legislation-app, SHA `f7b4dab74da2c5f289f282e8b2e9479f4d4a452f`:
  корневой LICENSE отсутствует. Исходники и оформление не копировались. Использован анализ поведения.
- Ollama v0.13.5: [upstream release](https://github.com/ollama/ollama/releases/tag/v0.13.5).
  Модель qwen3:4b-instruct имеет отдельные условия Apache 2.0 на
  [странице модели](https://ollama.com/library/qwen3:4b-instruct).
- Flask/Jinja/Werkzeug, SQLAlchemy/Alembic, Pydantic, HTTPX, Beautiful Soup, feedparser,
  Waitress и зависимости: версии в backend/requirements.lock.txt; лицензии поставляются в пакетах.

Лицензия программы не подтверждает актуальность законодательства и права на все правовые тексты KB.
Собственный код проекта не получает лицензию стороннего автора автоматически.
