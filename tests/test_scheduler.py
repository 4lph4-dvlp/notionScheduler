"""Standalone fake-SDK behavior checks; no live Notion calls."""

from unittest.mock import MagicMock

import pytest

from notion_scheduler import __version__
from notion_scheduler.client import NotionClient
from notion_scheduler.schema import SchemaError, TargetError
from notion_scheduler.tasks import Scheduler


def schema():
    return {
        "이름": {"type": "title", "title": {}},
        "선택": {"type": "select", "select": {"options": [{"name": "루틴"}, {"name": "이벤트"}]}},
        "구분": {"type": "multi_select", "multi_select": {"options": [{"name": "개인"}, {"name": "학업"}]}},
        "DueDate": {"type": "date", "date": {}},
        "Plan": {"type": "date", "date": {}},
        "우선순위": {"type": "select", "select": {"options": [{"name": "🔴 긴급 (P1)"}, {"name": "🟡 중요 (P2)"}, {"name": "🔵 보통 (P3)"}, {"name": "⚪ 낮음 (P4)"}]}},
        "상태": {"type": "status", "status": {"options": [{"name": "시작 전"}, {"name": "진행 중"}, {"name": "완료"}, {"name": "폐기"}]}},
        "메모": {"type": "rich_text", "rich_text": {}},
    }


def page(page_id="page-one", title="Buy groceries"):
    return {"id": page_id, "properties": {
        "이름": {"title": [{"plain_text": title}]},
        "선택": {"select": {"name": "이벤트"}},
        "구분": {"multi_select": [{"name": "개인"}]},
        "DueDate": {"date": {"start": "2026-10-05"}},
        "Plan": {"date": None},
        "우선순위": {"select": {"name": "🔵 보통 (P3)"}},
        "상태": {"status": {"name": "시작 전"}},
        "메모": {"rich_text": [{"plain_text": "old note"}]},
    }}


def sdk_with_pages():
    sdk = MagicMock()
    sdk.databases.retrieve.return_value = {"title": [{"plain_text": "Scheduler"}], "data_sources": [{"id": "source-one", "name": "Scheduler"}]}
    sdk.data_sources.retrieve.return_value = {"properties": schema()}
    def query(**kwargs):
        if kwargs.get("start_cursor") == "next":
            return {"results": [page("page-two", "Call plumber")], "has_more": False}
        return {"results": [page()], "has_more": True, "next_cursor": "next"}

    sdk.data_sources.query.side_effect = query
    return sdk


def test_standalone_list_paginates_and_preview_makes_no_writes():
    assert __version__ == "0.1.0"
    sdk = sdk_with_pages()
    tasks = Scheduler(NotionClient(token="test", database_id="database-one", sdk=sdk))

    listed = tasks.list_tasks()
    preview = tasks.preview_update(page_id="page-one", memo="new note")

    assert [task.title for task in listed] == ["Buy groceries", "Call plumber"]
    assert preview.target.data_source_id == "source-one"
    assert preview.properties == {"메모": {"rich_text": [{"text": {"content": "new note"}}]}}
    assert sdk.data_sources.query.call_args_list[1].kwargs["start_cursor"] == "next"
    sdk.pages.create.assert_not_called()
    sdk.pages.update.assert_not_called()


@pytest.mark.parametrize("children", [[], [{"id": "a", "name": "Scheduler"}, {"id": "b", "name": "Scheduler"}]])
def test_ambiguous_target_fails_closed(children):
    sdk = sdk_with_pages()
    sdk.databases.retrieve.return_value["data_sources"] = children
    with pytest.raises(TargetError):
        Scheduler(NotionClient(token="test", database_id="database-one", sdk=sdk)).list_tasks()
    sdk.pages.create.assert_not_called()


def test_schema_mismatch_fails_closed():
    sdk = sdk_with_pages()
    del sdk.data_sources.retrieve.return_value["properties"]["Plan"]
    with pytest.raises(SchemaError, match="Plan"):
        Scheduler(NotionClient(token="test", database_id="database-one", sdk=sdk)).list_tasks()
    sdk.pages.update.assert_not_called()
