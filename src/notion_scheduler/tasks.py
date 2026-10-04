"""General task operations with explicit previews."""

from dataclasses import dataclass

from .client import NotionClient
from .schema import InputError, SchedulerTask, Target, parse_page, serialize_fields


@dataclass(frozen=True)
class Preview:
    action: str
    target: Target
    page_id: str | None
    before: SchedulerTask | None
    properties: dict


class Scheduler:
    def __init__(self, client: NotionClient):
        self.client = client

    def list_tasks(self) -> list[SchedulerTask]:
        _, _, tasks = self._snapshot()
        return tasks

    def preview_create(self, *, title: str, priority: str = "🔵 보통 (P3)", status: str = "시작 전", **fields) -> Preview:
        target, schema, tasks = self._snapshot()
        if any(task.title == title for task in tasks):
            raise InputError("A Scheduler task already has this title; use an explicit page ID to edit it.")
        values = {"title": title, "priority": priority, "status": status, **fields}
        return Preview("create", target, None, None, serialize_fields(values, schema))

    def preview_update(self, *, page_id: str | None = None, lookup_title: str | None = None, **fields) -> Preview:
        target, schema, tasks = self._snapshot()
        if bool(page_id) == bool(lookup_title):
            raise InputError("Provide either page_id or lookup_title.")
        matches = [task for task in tasks if task.page_id == page_id] if page_id else [task for task in tasks if task.title == lookup_title]
        if len(matches) != 1:
            raise InputError("Task did not identify exactly one Scheduler page.")
        if not fields:
            raise InputError("At least one field must be supplied for update.")
        return Preview("update", target, matches[0].page_id, matches[0], serialize_fields(fields, schema))

    def preview_complete(self, *, page_id: str | None = None, lookup_title: str | None = None) -> Preview:
        return self.preview_update(page_id=page_id, lookup_title=lookup_title, status="완료")

    def apply(self, preview: Preview) -> dict:
        """Apply an explicit preview after checking the target and page again."""
        target, _, tasks = self._snapshot()
        if target != preview.target:
            raise InputError("Scheduler target changed since preview.")
        if preview.action == "create":
            title_parts = preview.properties.get("이름", {}).get("title", [])
            title = title_parts[0]["text"]["content"] if title_parts else ""
            if any(task.title == title for task in tasks):
                raise InputError("A Scheduler task with this title appeared since preview.")
            return self.client.create_page(target.data_source_id, preview.properties)
        if preview.action != "update" or not preview.page_id or preview.before is None:
            raise InputError("Invalid Scheduler preview.")
        current = [task for task in tasks if task.page_id == preview.page_id]
        if len(current) != 1 or current[0] != preview.before:
            raise InputError("Scheduler task changed since preview.")
        return self.client.update_page(preview.page_id, preview.properties)

    def _snapshot(self):
        target = self.client.resolve_target()
        schema = self.client.validate_scheduler_schema(target.data_source_id)
        tasks = [parse_page(page) for page in self.client.query_pages(target.data_source_id)]
        return target, schema, tasks
