"""Neutral Scheduler schema and task value objects."""

from dataclasses import dataclass


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
        if required_options - names:
            errors.append(name)
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
