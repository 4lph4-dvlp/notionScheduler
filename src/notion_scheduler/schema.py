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
