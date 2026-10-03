"""CLI contracts with an injected service; no external Notion calls."""

import json

from notion_scheduler.cli import main
from notion_scheduler.schema import SchedulerTask, Target
from notion_scheduler.tasks import Preview


class FakeScheduler:
    def __init__(self):
        self.applied = []
        self.args = None

    def list_tasks(self):
        return [SchedulerTask(page_id="one", title="Buy groceries")]

    def preview_create(self, **fields):
        self.args = fields
        return Preview("create", Target("db", "source", "Scheduler"), None, None, {"이름": {"title": [{"text": {"content": fields["title"]}}]}})

    def preview_update(self, **fields):
        self.args = fields
        return Preview("update", Target("db", "source", "Scheduler"), "one", SchedulerTask(page_id="one", title="Buy groceries"), {"Plan": {"date": {"start": fields["plan_date"]}}})

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
    assert listed["schema_version"] == 1
    assert listed["tasks"][0]["title"] == "Buy groceries"

    assert main(["create", "--title", "Pay rent", "--category", "개인"], scheduler=fake) == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview["dry_run"] is True
    assert fake.applied == []
    assert fake.args["category"] == ["개인"]

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


def test_missing_create_title_is_safe_error(capsys):
    fake = FakeScheduler()
    assert main(["create"], scheduler=fake) == 2
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is False
    assert result["error"]["code"] == "InputError"
    assert fake.applied == []
