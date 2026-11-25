import re
from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class FieldSpec:
    label: str
    kind: str = "text"
    placeholder: str = ""
    options: tuple[str, ...] = ()
    max_length: int = 200


FIELDS = {
    "applicant_name": FieldSpec("Фамилия, имя, отчество заявителя (при наличии)", "name"),
    "employee_name": FieldSpec("Фамилия, имя, отчество работника (при наличии)", "name"),
    "postal_address": FieldSpec("Почтовый адрес", placeholder="Индекс, город, улица, дом"),
    "institution": FieldSpec("Учреждение образования"),
    "study_program": FieldSpec(
        "Программа или специальность", "description", "Например, информатика"
    ),
    "study_start_year": FieldSpec("Год начала обучения", "year", "Например, 2023"),
    "study_end_year": FieldSpec("Год окончания обучения", "year", "Например, 2026"),
    "date": FieldSpec("Дата заявления", "date"),
    "employer": FieldSpec("Организация и подразделение"),
    "position": FieldSpec("Должность"),
    "employment_start_year": FieldSpec("Год начала работы", "year"),
    "employment_end_year": FieldSpec("Год окончания работы", "year"),
    "requested_information": FieldSpec(
        "Какие сведения нужны",
        options=("Стаж работы", "Заработная плата", "Стаж и заработная плата"),
    ),
    "purpose": FieldSpec("Цель запроса"),
    "reader_name": FieldSpec("Фамилия и инициалы пользователя", "name", "Например, Иванов И. И."),
    "visit_date": FieldSpec("Дата посещения", "date"),
    "research_topic": FieldSpec("Тема исследования"),
    "fund_number": FieldSpec("Номер фонда", "archive_number", max_length=40),
    "inventory_number": FieldSpec("Номер описи", "archive_number", max_length=40),
    "case_number": FieldSpec("Номер дела", "archive_number", max_length=40),
    "case_title": FieldSpec("Заголовок дела"),
    "order_date": FieldSpec("Дата заказа", "date"),
}

FORMATS = {"archive-study", "archive-employment", "archive-reading-room"}
PLACEHOLDER = re.compile(r"\{\{([a-z_]{1,50})\}\}")


def parse_date(value):
    for pattern in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def validate_field(spec, value):
    if not value:
        return "Заполните поле."
    if len(value) > spec.max_length or any(ord(char) < 32 for char in value):
        return f"Введите до {spec.max_length} символов в одну строку."
    if spec.options and value not in spec.options:
        return "Выберите один из вариантов."
    if spec.kind == "date" and parse_date(value) is None:
        return "Укажите существующую календарную дату."
    if spec.kind == "year" and (
        not re.fullmatch(r"[0-9]{4}", value) or not 1000 <= int(value) <= date.today().year
    ):
        return "Укажите год четырьмя цифрами, например 2023."
    if spec.kind == "name" and (
        len(value.split()) < 2
        or not all(any(c.isalpha() for c in part) for part in value.split())
        or any(not (c.isalpha() or c in " .-'’") for c in value)
    ):
        return "Укажите фамилию и имя либо инициалы, если они указаны в подписи поля."
    if spec.kind == "description" and not any(c.isalpha() for c in value):
        return "Введите название программы или специальности."
    if spec.kind == "archive_number" and (
        not re.fullmatch(r"[\w ./\-–]+", value) or not any(c.isdecimal() for c in value)
    ):
        return "Укажите архивный номер, например 12 или Р-12/1."
    return None


def validate_form(fields, data):
    values = {key: data[key].strip() if isinstance(data.get(key), str) else "" for key in fields}
    errors = {
        key: error for key, spec in fields.items() if (error := validate_field(spec, values[key]))
    }
    for key, spec in fields.items():
        if spec.kind == "date" and key not in errors:
            values[key] = parse_date(values[key]).isoformat()
    for prefix in ("study", "employment"):
        first, last = f"{prefix}_start_year", f"{prefix}_end_year"
        if last in values and first not in errors and last not in errors:
            if int(values[last]) < int(values[first]):
                errors[last] = "Год окончания должен быть не раньше года начала."
    if "order_date" in values and "order_date" not in errors and "visit_date" not in errors:
        if parse_date(values["visit_date"]) < parse_date(values["order_date"]):
            errors["visit_date"] = "Дата посещения должна быть не раньше даты заказа."
    return values, errors


def fill(content, fields, values):
    def replacement(match):
        name = match[1]
        value = values.get(name, "")
        if value and fields[name].kind == "date":
            parsed = parse_date(value)
            value = parsed.strftime("%d.%m.%Y") if parsed else ""
        return value or "________________"

    return PLACEHOLDER.sub(replacement, content)
