"""General task operations with explicit previews."""

from dataclasses import dataclass

from .client import NotionClient
from .schema import InputError, SchedulerTask, Target, parse_page


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

    def preview_update(self, *, page_id: str, memo: str) -> Preview:
        target, _, tasks = self._snapshot()
        matches = [task for task in tasks if task.page_id == page_id]
        if len(matches) != 1:
            raise InputError("Task page ID did not identify exactly one Scheduler task.")
        if not isinstance(memo, str):
            raise InputError("Memo must be text.")
        return Preview("update", target, page_id, matches[0], {"메모": {"rich_text": [{"text": {"content": memo}}]}})

    def _snapshot(self):
        target = self.client.resolve_target()
        schema = self.client.validate_scheduler_schema(target.data_source_id)
        tasks = [parse_page(page) for page in self.client.query_pages(target.data_source_id)]
        return target, schema, tasks
