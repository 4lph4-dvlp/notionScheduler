"""Neutral Scheduler schema and task value objects."""

from dataclasses import dataclass
from datetime import datetime


class SchedulerError(Exception):
    """Base error safe for presentation to an end user."""


class TargetError(SchedulerError):
    """The configured target cannot be resolved uniquely."""


class SchemaError(SchedulerError):
    """The target is not a compatible Scheduler."""


class InputError(SchedulerError):
    """Invalid user supplied task input."""


class AuthenticationError(SchedulerError):
    """Notion rejected the integration token."""


class PermissionError(SchedulerError):
    """The integration lacks access to the Scheduler."""


class TransportError(SchedulerError):
    """Notion could not complete a request."""


@dataclass(frozen=True)
class Target:
    database_id: str
    data_source_id: str
    title: str


@dataclass(frozen=True)
class SchedulerTask:
    page_id: str
    title: str
    selection: str | None = None
    category: tuple[str, ...] = ()
    due_date: str | None = None
    plan_date: str | None = None
    priority: str | None = None
    status: str | None = None
    memo: str = ""


SCHEDULER_SCHEMA = {
    "이름": ("title", frozenset()),
    "선택": ("select", frozenset({"루틴", "이벤트"})),
    "구분": ("multi_select", frozenset()),
    "DueDate": ("date", frozenset()),
    "Plan": ("date", frozenset()),
    "우선순위": ("select", frozenset({"🔴 긴급 (P1)", "🟡 중요 (P2)", "🔵 보통 (P3)", "⚪ 낮음 (P4)"})),
    "상태": ("status", frozenset({"시작 전", "진행 중", "완료", "폐기"})),
    "메모": ("rich_text", frozenset()),
}


def plain_text(parts):
    return "".join(str(part.get("plain_text") or part.get("text", {}).get("content", "")) for part in parts or [])


def validate_scheduler_schema(properties):
    """Validate all eight properties and required options without mutation."""
    errors = []
    for name, (expected_type, required_options) in SCHEDULER_SCHEMA.items():
        actual = properties.get(name)
        if not isinstance(actual, dict) or actual.get("type") != expected_type:
            errors.append(name)
            continue
        options = actual.get(expected_type, {}).get("options", [])
        names = {item.get("name") for item in options}
        missing = required_options - names
        if missing:
            errors.append(name + ": missing " + ", ".join(sorted(missing)))
    if errors:
        raise SchemaError("Incompatible Scheduler properties: " + ", ".join(errors))


def parse_page(page):
    """Read neutral task values from a Notion page."""
    props = page.get("properties", {})
    return SchedulerTask(
        page_id=str(page["id"]),
        title=plain_text(props.get("이름", {}).get("title")),
        selection=(props.get("선택", {}).get("select") or {}).get("name"),
        category=tuple(item.get("name", "") for item in props.get("구분", {}).get("multi_select") or []),
        due_date=(props.get("DueDate", {}).get("date") or {}).get("start"),
        plan_date=(props.get("Plan", {}).get("date") or {}).get("start"),
        priority=(props.get("우선순위", {}).get("select") or {}).get("name"),
        status=(props.get("상태", {}).get("status") or {}).get("name"),
        memo=plain_text(props.get("메모", {}).get("rich_text")),
    )


FIELD_TYPES = {
    "title": ("이름", "title"),
    "selection": ("선택", "select"),
    "category": ("구분", "multi_select"),
    "due_date": ("DueDate", "date"),
    "plan_date": ("Plan", "date"),
    "priority": ("우선순위", "select"),
    "status": ("상태", "status"),
    "memo": ("메모", "rich_text"),
}


def serialize_fields(fields: dict, schema: dict) -> dict:
    """Encode only explicitly supplied Scheduler fields."""
    properties = {}
    for key, value in fields.items():
        if key not in FIELD_TYPES:
            raise InputError(f"Unknown Scheduler field: {key}")
        name, kind = FIELD_TYPES[key]
        if kind in {"title", "rich_text"}:
            if not isinstance(value, str) or (kind == "title" and not value.strip()):
                raise InputError(f"{key} must be text" + (" with a value." if kind == "title" else "."))
            item = {"text": {"content": value}}
            properties[name] = {kind: [item] if value else []}
        elif kind in {"select", "status"}:
            choices = {item.get("name") for item in schema[name][kind].get("options", [])}
            if not isinstance(value, str) or value not in choices:
                raise InputError(f"Invalid {key} option.")
            properties[name] = {kind: {"name": value}}
        elif kind == "multi_select":
            if not isinstance(value, (list, tuple)) or not value or any(not isinstance(item, str) for item in value):
                raise InputError("category must be a nonempty list of option names.")
            choices = {item.get("name") for item in schema[name][kind].get("options", [])}
            if any(item not in choices for item in value):
                raise InputError("Invalid category option.")
            properties[name] = {kind: [{"name": item} for item in value]}
        else:
            if value is not None:
                if not isinstance(value, str):
                    raise InputError(f"{key} must be an ISO date or datetime.")
                try:
                    datetime.fromisoformat(value)
                except ValueError as error:
                    raise InputError(f"{key} must be an ISO date or datetime.") from error
            properties[name] = {"date": {"start": value} if value is not None else None}
    return properties
