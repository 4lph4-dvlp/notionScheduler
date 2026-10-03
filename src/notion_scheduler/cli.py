"""JSON command line interface for the independent Scheduler."""

import argparse
from dataclasses import asdict
import json
import os
import sys

from .client import NotionClient
from .schema import InputError, SchedulerError
from .tasks import Scheduler


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="notion-scheduler")
    parser.add_argument("--env-file", help="Optional file containing Notion environment variables")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List Scheduler tasks")
    for name in ("preview", "create", "update", "complete"):
        command = commands.add_parser(name)
        if name == "preview":
            command.add_argument("operation", choices=("create", "update", "complete"))
        if name != "complete":
            command.add_argument("--title")
            command.add_argument("--selection")
            command.add_argument("--category", action="append")
            command.add_argument("--due-date")
            command.add_argument("--plan-date")
            command.add_argument("--priority")
            command.add_argument("--status")
            command.add_argument("--memo")
        if name != "create":
            command.add_argument("--page-id")
            command.add_argument("--lookup-title")
        if name != "preview":
            command.add_argument("--apply", action="store_true", help="Execute the write after preview")
    return parser


def _fields(args: argparse.Namespace) -> dict:
    names = ("title", "selection", "category", "due_date", "plan_date", "priority", "status", "memo")
    return {name: getattr(args, name) for name in names if hasattr(args, name) and getattr(args, name) is not None}


def _scheduler(args: argparse.Namespace) -> Scheduler:
    if args.env_file:
        from dotenv import load_dotenv

        if not os.path.isfile(args.env_file):
            raise InputError("Environment file was not found.")
        load_dotenv(args.env_file, override=False)
    token = os.getenv("NOTION_TOKEN") or os.getenv("NOTION_API_KEY") or ""
    if not token:
        raise InputError("NOTION_TOKEN or NOTION_API_KEY is required.")
    client = NotionClient(
        token=token,
        database_id=os.getenv("NOTION_DATABASE_ID", ""),
        database_name=os.getenv("NOTION_DATABASE_NAME", ""),
        data_source_id=os.getenv("NOTION_DATA_SOURCE_ID", ""),
    )
    return Scheduler(client)


def _emit(value: dict) -> None:
    print(json.dumps({"schema_version": 1, **value}, ensure_ascii=False, default=str))


def main(argv: list[str] | None = None, *, scheduler: Scheduler | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        service = scheduler or _scheduler(args)
        if args.command == "list":
            tasks = service.list_tasks()
            _emit({"ok": True, "action": "list", "tasks": [asdict(task) for task in tasks], "count": len(tasks)})
            return 0
        operation = args.operation if args.command == "preview" else args.command
        if operation == "create":
            fields = _fields(args)
            if not fields.get("title"):
                raise InputError("--title is required for create.")
            preview = service.preview_create(**fields)
        elif operation == "update":
            fields = _fields(args)
            preview = service.preview_update(page_id=args.page_id, lookup_title=args.lookup_title, **fields)
        else:
            preview = service.preview_complete(page_id=args.page_id, lookup_title=args.lookup_title)
        apply = bool(getattr(args, "apply", False))
        response = service.apply(preview) if apply else None
        _emit({"ok": True, "action": operation, "dry_run": not apply, "target": asdict(preview.target), "page_id": preview.page_id, "before": asdict(preview.before) if preview.before else None, "properties": preview.properties, "result": {"id": str(response.get("id", ""))} if response else None})
        return 0
    except SchedulerError as error:
        _emit({"ok": False, "error": {"code": type(error).__name__, "message": str(error)}})
        return 2


if __name__ == "__main__":
    sys.exit(main())
