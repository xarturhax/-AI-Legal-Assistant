import io
import json
import re
from pathlib import Path

from flask import Blueprint, abort, current_app, render_template, request, send_file
from pydantic import BaseModel, ConfigDict, Field, ValidationError

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
    fields = sorted(set(re.findall(r"\{\{([a-z_]{1,50})\}\}", content)))
    if request.method == "POST":
        data = payload()
        for field in fields:
            content = content.replace("{{" + field + "}}", string_value(data, field, 1000))
        return send_file(
            io.BytesIO(content.encode("utf-8-sig")),
            mimetype="text/plain",
            as_attachment=True,
            download_name=entry.id + ".txt",
        )
    return render_template("document.html", document=entry, fields=fields, content=content)
