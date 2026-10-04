"""CLI contracts with an injected service; no external Notion calls."""

import json
import io
import sys

from notion_scheduler.cli import _emit, main
from notion_scheduler.schema import SchedulerTask, Target
from notion_scheduler.tasks import Preview


class FakeScheduler:
    def __init__(self):
        self.applied = []
        self.args = None

    def list_tasks(self):
        return [SchedulerTask(page_id="one", title="Buy groceries", status="시작 전"), SchedulerTask(page_id="two", title="Call plumber", status="완료")]

    def preview_create(self, **fields):
        self.args = fields
        return Preview("create", Target("db", "source", "Scheduler"), None, None, {"이름": {"title": [{"text": {"content": fields["title"]}}]}})

    def preview_update(self, **fields):
        self.args = fields
        properties = {"Plan": {"date": {"start": fields["plan_date"]}}} if "plan_date" in fields else {"tag": {"multi_select": [{"name": tag} for tag in fields["tags"]]}}
        return Preview("update", Target("db", "source", "Scheduler"), "one", SchedulerTask(page_id="one", title="Buy groceries"), properties)

    def preview_complete(self, **fields):
        self.args = fields
        return Preview("update", Target("db", "source", "Scheduler"), "one", SchedulerTask(page_id="one", title="Buy groceries"), {"상태": {"status": {"name": "완료"}}})

    def apply(self, preview):
        self.applied.append(preview)
        return {"id": "created-or-updated"}


def test_list_and_create_are_versioned_and_create_defaults_to_preview(capsys):
    fake = FakeScheduler()
    assert main(["list"], scheduler=fake) == 0
    listed = json.loads(capsys.readouterr().out)
    assert listed["schema_version"] == 2
    assert listed["tasks"][0]["title"] == "Buy groceries"

    assert main(["create", "--title", "Pay rent", "--category", "일상", "--tag", "상담"], scheduler=fake) == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview["dry_run"] is True
    assert fake.applied == []
    assert fake.args["category"] == ["일상"]
    assert fake.args["tags"] == ["상담"]

    assert main(["create", "--title", "Pay rent", "--apply"], scheduler=fake) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["dry_run"] is False
    assert applied["result"]["id"] == "created-or-updated"
    assert len(fake.applied) == 1


def test_update_plan_and_complete_need_apply(capsys):
    fake = FakeScheduler()
    assert main(["update", "--page-id", "one", "--plan-date", "2026-10-04"], scheduler=fake) == 0
    assert json.loads(capsys.readouterr().out)["properties"]["Plan"]["date"]["start"] == "2026-10-04"
    assert fake.applied == []
    assert main(["complete", "--page-id", "one", "--apply"], scheduler=fake) == 0
    assert json.loads(capsys.readouterr().out)["result"]["id"] == "created-or-updated"


def test_clear_tags_is_explicit(capsys):
    fake = FakeScheduler()
    assert main(["update", "--page-id", "one", "--clear-tags"], scheduler=fake) == 0
    assert fake.args["tags"] == []
    assert json.loads(capsys.readouterr().out)["dry_run"] is True


def test_missing_create_title_is_safe_error(capsys):
    fake = FakeScheduler()
    assert main(["create"], scheduler=fake) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False
    assert result["error"]["code"] == "InputError"
    assert fake.applied == []


def test_list_filters_projects_and_limits_output(capsys):
    fake = FakeScheduler()
    assert main(["list", "--status", "시작 전", "--contains", "GROCER", "--fields", "title,status", "--limit", "1"], scheduler=fake) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["tasks"] == [{"page_id": "one", "title": "Buy groceries", "status": "시작 전"}]
    assert result["matching_count"] == 1
    assert result["count"] == 1
    assert main(["list", "--fields", "unknown"], scheduler=fake) == 2
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "InputError"
    assert main(["list", "--limit", "0"], scheduler=fake) == 2
    assert json.loads(capsys.readouterr().out)["error"]["code"] == "InputError"


def test_json_output_handles_windows_legacy_encoding(monkeypatch):
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="cp949", write_through=True)
    monkeypatch.setattr(sys, "stdout", stream)
    _emit({"ok": True, "priority": "🔵 보통 (P3)"})
    assert json.loads(buffer.getvalue().decode("utf-8"))["priority"] == "🔵 보통 (P3)"
