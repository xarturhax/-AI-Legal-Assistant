FROM python:3.11.14-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ENV APP_INSTANCE_PATH=/app/data/instance
ENV APP_HOST=0.0.0.0
WORKDIR /app
COPY requirements.lock.txt ./requirements.lock.txt
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY . .
RUN useradd --create-home --uid 10001 legal && mkdir -p /app/data && chown legal:legal /app/data
USER legal
# Настоящие миграции на временной SQLite в памяти, без подключения к OSTIS/LLM.
# Проверка выполняется с тем же пользователем и путями, что и запуск контейнера.
RUN SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
    DATABASE_URL=sqlite:///:memory: DOCUMENT_CATALOG=/app/documents/catalog.json \
    python -m app db-upgrade
EXPOSE 5000
CMD ["python", "-m", "app"]

