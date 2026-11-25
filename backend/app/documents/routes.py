import io
import json
from pathlib import Path

from flask import Blueprint, abort, current_app, render_template, request, send_file
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.documents.export import MIME_TYPES, render_document
from app.documents.fields import FIELDS, FORMATS, PLACEHOLDER, fill, validate_form
from app.web_utils import payload, string_value

bp = Blueprint("documents", __name__)


class Document(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(pattern=r"^[a-z0-9_-]{1,80}$")
    title: str = Field(min_length=1, max_length=200)
    source_url: str = Field(pattern=r"^https://[^\s]+$")
    license: str = Field(min_length=1, max_length=200)
    file: str = Field(min_length=1, max_length=200)


def catalog():
    path = Path(current_app.config["DOCUMENT_CATALOG"])
    if not path.is_file():
        return []
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            raise ValueError
        return [Document.model_validate(entry) for entry in entries]
    except (ValueError, ValidationError):
        abort(503, description="Каталог документов содержит ошибку. Проверьте источники бланков.")


@bp.get("/templates")
def templates():
    return render_template("documents.html", documents=catalog())


@bp.route("/templates/<identifier>", methods=["GET", "POST"])
def document(identifier):
    entry = next((item for item in catalog() if item.id == identifier), None)
    if not entry:
        abort(404, description="Бланк не найден.")
    base = Path(current_app.config["DOCUMENT_CATALOG"]).resolve().parent
    path = (base / entry.file).resolve()
    if not path.is_relative_to(base) or not path.is_file() or path.suffix != ".txt":
        abort(404, description="Файл бланка недоступен.")
    content = path.read_text(encoding="utf-8")
    fields = list(dict.fromkeys(PLACEHOLDER.findall(content)))
    if identifier in FORMATS:
        specs = {key: FIELDS[key] for key in fields}
        values, errors = {}, {}
        preview_ready = False
        if request.method == "POST":
            data = payload()
            values, errors = validate_form(specs, data)
            if not errors:
                action = data.get("action", "docx")
                if not isinstance(action, str) or action not in {"preview", *MIME_TYPES}:
                    abort(400, description="Выберите предпросмотр, DOCX или PDF.")
                if action in MIME_TYPES:
                    try:
                        export = render_document(fill(content, specs, values), action)
                    except FileNotFoundError:
                        abort(503, description="PDF сейчас недоступен. Скачайте бланк в DOCX.")
                    return send_file(
                        export,
                        mimetype=MIME_TYPES[action],
                        as_attachment=True,
                        download_name=f"{entry.id}.{action}",
                        max_age=0,
                    )
                preview_ready = True
        return render_template(
            "document.html",
            document=entry,
            specs=specs,
            content=fill(content, specs, values if preview_ready else {}),
            values=values,
            errors=errors,
            preview_ready=preview_ready,
        ), 422 if errors else 200
    if request.method == "POST":
        data = payload()
        content = PLACEHOLDER.sub(lambda match: string_value(data, match[1], 1000), content)
        return send_file(
            io.BytesIO(content.encode("utf-8-sig")),
            mimetype="text/plain",
            as_attachment=True,
            download_name=entry.id + ".txt",
        )
    return render_template("document.html", document=entry, fields=fields, content=content)
