from app.db.models import Profile, QueryHistory
from app.errors import ServiceError
from app.extensions import db
from app.legal.contracts import QueryInput
from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user
from pydantic import ValidationError

bp = Blueprint("legal", __name__)


def legal_service():
    return current_app.extensions["legal_service"]


def default_mode():
    if current_user.is_authenticated:
        profile = db.session.get(Profile, current_user.id)
        if profile:
            return profile.settings.get("mode", "baseline")
    return current_app.config["LEGAL_QUERY_DEFAULT_MODE"]


def run_query(query):
    status = "failed"
    try:
        result = legal_service().query(query.query, query.mode)
        status = result["answer"]["status"]
        return result
    except ServiceError as error:
        status = error.code
        raise
    finally:
        if current_user.is_authenticated:
            db.session.add(
                QueryHistory(
                    user_id=current_user.id, query=query.query, mode=query.mode, status=status
                )
            )
            db.session.commit()


def validated_query(data):
    try:
        if isinstance(data, dict) and "mode" not in data:
            data = {**data, "mode": default_mode()}
        query = QueryInput.model_validate(data)
        if len(query.query) > current_app.config["MAX_QUERY_LENGTH"]:
            raise ValueError("Запрос слишком длинный.")
        return query
    except (ValidationError, ValueError):
        from flask import abort

        abort(400, description="Проверьте текст запроса и режим baseline/llm.")


@bp.route("/requests", methods=["GET", "POST"])
@bp.route("/requests_results", methods=["GET"])
def requests_page():
    result = None
    if request.method == "POST":
        query = validated_query(
            {
                "query": request.form.get("query", ""),
                "mode": request.form.get("mode", default_mode()),
            }
        )
        result = run_query(query)
    return render_template(
        "search.html",
        result=result,
        directory=False,
        selected_mode=request.form.get("mode", default_mode()),
    )


@bp.post("/api/legal/query")
def query_api():
    query = validated_query(request.get_json(silent=True))
    return jsonify(run_query(query))


@bp.route("/directory", methods=["GET", "POST"])
@bp.get("/directory_results")
def directory():
    term = request.values.get("term", "").strip()
    mode = request.values.get("mode", "baseline")
    result = None
    if term:
        result = lookup_concepts(term, mode)
    return render_template("search.html", result=result, directory=True, selected_mode=mode)


@bp.get("/api/legal/concepts")
def concepts():
    return jsonify(
        lookup_concepts(request.args.get("term", "").strip(), request.args.get("mode", "baseline"))
    )


def lookup_concepts(term, mode):
    from flask import abort

    if not 2 <= len(term) <= 200:
        abort(400, description="Введите название или описание длиной от 2 до 200 символов.")
    if mode not in {"baseline", "llm"}:
        abort(400, description="Выберите поиск по названию или по описанию.")
    return legal_service().lookup_concepts(term, mode)


@bp.get("/api/legal/sources/<identifier>")
@bp.get("/article/<identifier>")
def source(identifier):
    from flask import abort

    found = legal_service().ostis.source(identifier)
    if not found:
        abort(404, description="Источник не найден в OSTIS.")
    if request.path.startswith("/api/"):
        return jsonify(found)
    return render_template("source.html", source=found)
