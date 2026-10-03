"""Direct Notion API transport for Scheduler tasks."""

from collections.abc import Callable
import time
from typing import Any

from notion_client import Client, RetryOptions
from notion_client.errors import APIResponseError

from .schema import (
    AuthenticationError,
    PermissionError,
    Target,
    TargetError,
    TransportError,
    plain_text,
    validate_scheduler_schema,
)


REQUEST_INTERVAL_SECONDS = 0.35
READ_529_RETRIES = 2


class NotionClient:
    """Configured Notion transport."""

    def __init__(
        self,
        *,
        token: str = "",
        database_id: str = "",
        database_name: str = "",
        data_source_id: str = "",
        sdk: Any | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        monotonic_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.database_id = database_id.strip()
        self.database_name = database_name.strip()
        self.data_source_id = data_source_id.strip()
        self.sdk = sdk if sdk is not None else Client(auth=token, retry=RetryOptions(max_retries=3))
        self._sleep = sleep_fn
        self._monotonic = monotonic_fn
        self._last_request_at: float | None = None

    def _throttle(self) -> None:
        now = self._monotonic()
        if self._last_request_at is not None:
            wait = REQUEST_INTERVAL_SECONDS - (now - self._last_request_at)
            if wait > 0:
                self._sleep(wait)
                now = self._monotonic()
        self._last_request_at = now

    @staticmethod
    def _safe_error(error: APIResponseError) -> Exception:
        status = getattr(error, "status", None)
        if status == 401:
            return AuthenticationError("Notion authentication failed. Check the integration token.")
        if status == 403:
            return PermissionError("Notion integration lacks Scheduler access.")
        if status == 404:
            return TargetError("Configured Notion Scheduler could not be found.")
        return TransportError("Notion API request failed.")

    def _read(self, operation: Callable[..., Any], **kwargs: Any) -> Any:
        for attempt in range(READ_529_RETRIES + 1):
            self._throttle()
            try:
                return operation(**kwargs)
            except APIResponseError as error:
                if getattr(error, "status", None) == 529 and attempt < READ_529_RETRIES:
                    continue
                raise self._safe_error(error) from None
        raise AssertionError("unreachable")

    def _write(self, operation: Callable[..., Any], **kwargs: Any) -> Any:
        self._throttle()
        try:
            return operation(**kwargs)
        except APIResponseError as error:
            raise self._safe_error(error) from None

    def resolve_target(self) -> Target:
        """Prefer an explicit ID, otherwise discover one exact data-source name."""
        if self.data_source_id:
            source = self._read(self.sdk.data_sources.retrieve, data_source_id=self.data_source_id)
            parent_id = source.get("parent", {}).get("database_id")
            if not parent_id:
                raise TargetError("Configured data source has no database parent.")
            return Target(str(parent_id), self.data_source_id, plain_text(source.get("title")))
        if self.database_id:
            database = self._read(self.sdk.databases.retrieve, database_id=self.database_id)
            children = database.get("data_sources", [])
            matches = children if len(children) == 1 else [child for child in children if child.get("name") == self.database_name]
            if len(matches) != 1 or not matches[0].get("id"):
                raise TargetError("Configured database does not identify one Scheduler data source.")
            child = matches[0]
            return Target(self.database_id, str(child["id"]), plain_text(database.get("title")) or str(child.get("name", "")))
        if not self.database_name:
            raise TargetError("A Scheduler database ID, data source ID, or exact name is required.")
        matches = []
        cursor = None
        while True:
            kwargs = {"query": self.database_name, "filter": {"property": "object", "value": "data_source"}, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor
            response = self._read(self.sdk.search, **kwargs)
            matches.extend(item for item in response.get("results", []) if item.get("object") == "data_source" and (plain_text(item.get("title")) or item.get("name")) == self.database_name)
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")
            if not cursor:
                raise TransportError("Notion search pagination ended without a cursor.")
        if len(matches) != 1:
            raise TargetError("Scheduler name did not identify exactly one data source.")
        match = matches[0]
        parent_id = match.get("parent", {}).get("database_id")
        if not parent_id or not match.get("id"):
            raise TargetError("Scheduler search result is missing its database parent or ID.")
        return Target(str(parent_id), str(match["id"]), self.database_name)

    def validate_scheduler_schema(self, data_source_id: str) -> dict:
        source = self._read(self.sdk.data_sources.retrieve, data_source_id=data_source_id)
        properties = source.get("properties", {})
        validate_scheduler_schema(properties)
        return properties

    def query_pages(self, data_source_id: str) -> list[dict]:
        """Read every task, including completed and old tasks, for safe lookups."""
        pages = []
        cursor = None
        while True:
            kwargs = {"data_source_id": data_source_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor
            response = self._read(self.sdk.data_sources.query, **kwargs)
            pages.extend(response.get("results", []))
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")
            if not cursor:
                raise TransportError("Notion query pagination ended without a cursor.")
        return pages

    def create_page(self, data_source_id: str, properties: dict) -> dict:
        return self._write(self.sdk.pages.create, parent={"type": "data_source_id", "data_source_id": data_source_id}, properties=properties)

    def update_page(self, page_id: str, properties: dict) -> dict:
        return self._write(self.sdk.pages.update, page_id=page_id, properties=properties)
