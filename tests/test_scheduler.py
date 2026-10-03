"""Standalone fake-SDK behavior checks; no live Notion calls."""

from unittest.mock import MagicMock

import pytest

from notion_scheduler import __version__
from notion_scheduler.client import NotionClient
from notion_scheduler.schema import InputError, SchemaError, TargetError
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


def test_filtered_query_keeps_filter_on_every_cursor_page():
    sdk = sdk_with_pages()
    client = NotionClient(token="test", database_id="database-one", sdk=sdk)
    predicate = {"property": "상태", "status": {"does_not_equal": "완료"}}

    assert len(client.query_pages("source-one", filter=predicate)) == 2
    assert [call.kwargs["filter"] for call in sdk.data_sources.query.call_args_list] == [predicate, predicate]


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


def test_general_create_preview_and_apply():
    sdk = sdk_with_pages()
    scheduler = Scheduler(NotionClient(token="test", database_id="database-one", sdk=sdk))
    preview = scheduler.preview_create(title="Pay rent", category=("개인",), plan_date="2026-10-04", memo="Bank transfer")
    sdk.pages.create.assert_not_called()
    assert preview.properties["Plan"] == {"date": {"start": "2026-10-04"}}
    assert preview.properties["상태"] == {"status": {"name": "시작 전"}}
    scheduler.apply(preview)
    assert sdk.pages.create.call_args.kwargs["parent"]["data_source_id"] == "source-one"


def test_sparse_update_can_change_plan_and_status_explicitly():
    sdk = sdk_with_pages()
    scheduler = Scheduler(NotionClient(token="test", database_id="database-one", sdk=sdk))
    preview = scheduler.preview_update(page_id="page-one", plan_date="2026-10-04", status="진행 중")
    assert set(preview.properties) == {"Plan", "상태"}
    scheduler.apply(preview)
    assert set(sdk.pages.update.call_args.kwargs["properties"]) == {"Plan", "상태"}


def test_complete_by_id_and_ambiguous_title_fails_closed():
    sdk = sdk_with_pages()
    scheduler = Scheduler(NotionClient(token="test", database_id="database-one", sdk=sdk))
    preview = scheduler.preview_complete(page_id="page-one")
    assert preview.properties == {"상태": {"status": {"name": "완료"}}}
    scheduler.apply(preview)
    assert sdk.pages.update.call_args.kwargs["properties"] == preview.properties

    sdk.data_sources.query.side_effect = lambda **kwargs: {"results": [page("a"), page("b")], "has_more": False}
    with pytest.raises(InputError, match="exactly one"):
        scheduler.preview_update(lookup_title="Buy groceries", memo="changed")


def test_invalid_option_and_stale_preview_never_write():
    sdk = sdk_with_pages()
    scheduler = Scheduler(NotionClient(token="test", database_id="database-one", sdk=sdk))
    with pytest.raises(InputError, match="Invalid status"):
        scheduler.preview_update(page_id="page-one", status="not a status")
    preview = scheduler.preview_update(page_id="page-one", memo="new note")
    sdk.data_sources.query.side_effect = lambda **kwargs: {"results": [page("page-one", "Renamed")], "has_more": False}
    with pytest.raises(InputError, match="changed"):
        scheduler.apply(preview)
    sdk.pages.update.assert_not_called()
