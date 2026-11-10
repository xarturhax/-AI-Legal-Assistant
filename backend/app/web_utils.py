from datetime import datetime

from flask import abort, request
from flask_login import current_user

from app.extensions import db


def payload():
    data = request.get_json(silent=True) if request.is_json else request.form.to_dict()
    if not isinstance(data, dict):
        abort(400, description="Ожидается объект с полями формы.")
    return data


def string_value(data, key, maximum=200, required=True):
    value = data.get(key, "")
    if not isinstance(value, str):
        abort(400, description=f"Поле {key} должно быть строкой.")
    value = value.strip()
    if len(value) > maximum or (required and not value) or "\x00" in value:
        abort(400, description=f"Недопустимая длина поля {key}.")
    return value


def integer_value(data, key):
    value = data.get(key)
    try:
        if isinstance(value, bool) or str(int(value)) != str(value) or int(value) < 1:
            raise ValueError
        return int(value)
    except (ValueError, TypeError):
        abort(400, description=f"Недопустимый идентификатор {key}.")


def own_row(model, identifier):
    row = db.session.execute(
        db.select(model).filter_by(id=identifier, user_id=current_user.id)
    ).scalar_one_or_none()
    if row is None:
        abort(404, description="Запись не найдена.")
    return row


def serialize(row):
    result = {}
    for column in row.__table__.columns:
        if column.name in {"user_id", "password_hash", "token_hash"}:
            continue
        value = getattr(row, column.name)
        result[column.name] = value.isoformat() if isinstance(value, datetime) else value
    return result
