from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import Blueprint, abort, current_app, jsonify, redirect, render_template, request
from flask_login import current_user, login_required

from app.db.models import Bookmark, CalendarEvent, Note, Profile, QueryHistory
from app.extensions import db
from app.web_utils import integer_value, own_row, payload, serialize, string_value

bp = Blueprint("account", __name__)
COLLECTIONS = {
    "notes": Note,
    "bookmarks": Bookmark,
    "calendar": CalendarEvent,
    "history": QueryHistory,
}


def own_items(model):
    return (
        db.session.execute(
            db.select(model).filter_by(user_id=current_user.id).order_by(model.id.desc()).limit(100)
        )
        .scalars()
        .all()
    )


def validate_timezone(value):
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        abort(400, description="Неизвестный часовой пояс.")
    return value


@bp.get("/cabinet")
@login_required
def cabinet():
    return render_template(
        "cabinet.html",
        profile=db.session.get(Profile, current_user.id),
        notes=own_items(Note),
        bookmarks=own_items(Bookmark),
        history=own_items(QueryHistory),
    )


@bp.route("/api/profile", methods=["GET", "PUT"])
@bp.post("/cabinet/profile")
@login_required
def profile():
    record = db.session.get(Profile, current_user.id)
    if request.method != "GET":
        data = payload()
        record.display_name = string_value(data, "display_name", 120, required=False)
        record.details = {
            key: string_value(data, key, 200, required=False)
            for key in ("gender", "age", "experience", "field")
        }
        db.session.commit()
    if request.path.startswith("/cabinet/"):
        return redirect("/cabinet")
    return jsonify(
        display_name=record.display_name,
        details=record.details,
        email=current_user.email,
        user_type=current_user.role,
        verified=current_user.is_verified,
    )


@bp.route("/api/settings", methods=["GET", "PUT"])
@bp.post("/cabinet/settings")
@login_required
def settings():
    record = db.session.get(Profile, current_user.id)
    if request.method != "GET":
        data = payload()
        mode = data.get("mode", "baseline")
        if not isinstance(mode, str) or mode not in {"baseline", "llm"}:
            abort(400, description="Неизвестный режим поиска.")
        timezone = validate_timezone(string_value(data, "timezone", 80))
        record.settings = {"mode": mode, "timezone": timezone}
        db.session.commit()
    if request.path.startswith("/cabinet/"):
        return redirect("/cabinet")
    return jsonify(record.settings)


def collection_action(name, method):
    model = COLLECTIONS[name]
    if method == "GET":
        return jsonify(items=[serialize(row) for row in own_items(model)])
    data = payload()
    if name == "history" and method == "DELETE":
        db.session.execute(db.delete(QueryHistory).where(QueryHistory.user_id == current_user.id))
        db.session.commit()
        return jsonify(ok=True)
    if method in {"DELETE", "PUT"}:
        record = own_row(model, integer_value(data, "id"))
        if method == "DELETE":
            db.session.delete(record)
            db.session.commit()
            return jsonify(ok=True)
    elif method == "POST":
        record = model(user_id=current_user.id)
    else:
        abort(405)
    if name == "notes":
        record.text = string_value(data, "text", 10000)
        source_id = string_value(data, "source_id", 220, required=False)
        if source_id and not current_app.extensions["legal_service"].ostis.source(source_id):
            abort(404, description="Источник заметки не найден в OSTIS.")
        record.source_id = source_id or None
    elif name == "bookmarks":
        source_id = string_value(data, "source_id", 220)
        source = current_app.extensions["legal_service"].ostis.source(source_id)
        if not source:
            abort(404, description="Источник не найден в OSTIS.")
        existing = db.session.execute(
            db.select(Bookmark).filter_by(
                user_id=current_user.id, source_system="ostis", source_id=source_id
            )
        ).scalar_one_or_none()
        if existing:
            return jsonify(serialize(existing))
        record.source_id, record.title = source_id, source["title"][:1000]
    elif name == "calendar":
        record.title = string_value(data, "title", 200)
        record.description = string_value(data, "description", 5000, required=False)
        record.timezone = validate_timezone(string_value(data, "timezone", 80))
        try:
            date = datetime.fromisoformat(string_value(data, "starts_at", 50))
            if date.tzinfo:
                date = date.astimezone(ZoneInfo(record.timezone)).replace(tzinfo=None)
            record.starts_at = date
        except ValueError:
            abort(400, description="Проверьте дату события.")
    else:
        abort(405)
    db.session.add(record)
    db.session.commit()
    return jsonify(serialize(record)), 201 if method == "POST" else 200


@bp.route("/api/<name>", methods=["GET", "POST", "PUT", "DELETE"])
@login_required
def collection_api(name):
    if name not in COLLECTIONS:
        abort(404)
    return collection_action(name, request.method)


@bp.post("/cabinet/<name>")
@login_required
def collection_form(name):
    if name not in COLLECTIONS:
        abort(404)
    method = {"add": "POST", "edit": "PUT", "delete": "DELETE"}.get(request.form.get("action"))
    if not method:
        abort(400)
    collection_action(name, method)
    return redirect("/show_calendar" if name == "calendar" else "/cabinet")


@bp.post("/bookmarks/add")
@login_required
def bookmark_form():
    collection_action("bookmarks", "POST")
    return redirect("/cabinet")


@bp.get("/show_calendar")
@login_required
def calendar():
    return render_template(
        "calendar.html",
        events=own_items(CalendarEvent),
        timezone=db.session.get(Profile, current_user.id).settings.get("timezone", "Europe/Minsk"),
    )
