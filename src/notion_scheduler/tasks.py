"""General task operations with explicit previews."""

from dataclasses import dataclass

from .client import NotionClient
from .schema import SchedulerTask, Target


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
        return []

    def preview_update(self, *, page_id: str, memo: str) -> Preview:
        return None
