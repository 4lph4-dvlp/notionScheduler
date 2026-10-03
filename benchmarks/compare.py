"""Read-only API probe and evidence validator for API/MCP comparisons.

The write workloads are recorded only after a reviewed disposable target is approved.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import time

from dotenv import dotenv_values
from notion_client import Client, RetryOptions

from notion_scheduler.client import NotionClient
from notion_scheduler.schema import plain_text


OPERATIONS = ("read", "create", "update")
TRANSPORTS = ("api", "mcp")
STATUSES = ("measured", "unavailable", "approval_required")


def validate_report(report: dict) -> None:
    """Reject a comparison that hides a workload, provenance, or write gap."""
    if report.get("schema_version") != 1 or not report.get("access_context"):
        raise ValueError("Report needs schema_version 1 and access_context.")
    entries = report.get("measurements")
    if not isinstance(entries, list):
        raise ValueError("Report needs measurements.")
    indexed = {(entry.get("transport"), entry.get("operation")): entry for entry in entries}
    if len(indexed) != len(entries):
        raise ValueError("Duplicate transport and operation.")
    if any(entry.get("status") == "measured" and entry.get("operation") in ("create", "update") for entry in entries):
        cleanup = report.get("cleanup") or {}
        if not cleanup.get("database_id") or cleanup.get("in_trash") is not True or not cleanup.get("evidence"):
            raise ValueError("Measured write report needs verified disposable database cleanup.")
    for transport in TRANSPORTS:
        for operation in OPERATIONS:
            entry = indexed.get((transport, operation))
            if entry is None:
                raise ValueError(f"Missing {transport} {operation} workload.")
            if entry.get("status") not in STATUSES:
                raise ValueError("Measurement status is required.")
            for key in ("sample_size", "tool_calls", "elapsed_ms", "returned_bytes", "model_tokens", "model_token_source", "metric_source", "evidence"):
                if key not in entry:
                    raise ValueError(f"Missing {key} for {transport} {operation}.")
            if entry["status"] == "measured":
                if any(entry[key] is None for key in ("sample_size", "tool_calls", "elapsed_ms", "returned_bytes")):
                    raise ValueError("Measured workload lacks required values.")
                if not entry["evidence"]:
                    raise ValueError("Measured workload needs evidence.")
            if entry["model_tokens"] is None and entry["model_token_source"] != "unavailable":
                raise ValueError("Unavailable token usage must be identified.")
            if entry["model_tokens"] is not None and entry["model_token_source"] in (None, "unavailable", "character_count"):
                raise ValueError("Token usage needs an actual model usage counter.")
            if operation != "read" and entry["status"] == "measured":
                if not entry.get("approval") or not entry.get("disposable_target") or not entry.get("write_evidence"):
                    raise ValueError("Live write measurement needs approval, disposable target, and write evidence.")


def probe_api_read(*, env_file: Path, data_source_id: str, cutoff: str) -> dict:
    """Query the exact filtered workload without exposing row contents or credentials."""
    datetime.fromisoformat(cutoff)
    values = dotenv_values(env_file)
    token = values.get("NOTION_TOKEN") or values.get("NOTION_API_KEY")
    if not token:
        raise ValueError("Environment file lacks NOTION_TOKEN or NOTION_API_KEY.")
    sdk = Client(auth=token, retry=RetryOptions(max_retries=3))
    counter = {"requests": 0}

    class SourceProxy:
        def query(self, **kwargs):
            counter["requests"] += 1
            return sdk.data_sources.query(**kwargs)

    class SdkProxy:
        data_sources = SourceProxy()

    predicate = {"or": [
        {"property": "DueDate", "date": {"on_or_after": cutoff}},
        {"property": "상태", "status": {"does_not_equal": "완료"}},
    ]}
    client = NotionClient(token=token, sdk=SdkProxy())
    started = time.perf_counter()
    pages = client.query_pages(data_source_id, filter=predicate)
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    projected = [{
        "url": page.get("url"),
        "이름": plain_text(page.get("properties", {}).get("이름", {}).get("title")),
        "date:DueDate:start": (page.get("properties", {}).get("DueDate", {}).get("date") or {}).get("start"),
        "상태": (page.get("properties", {}).get("상태", {}).get("status") or {}).get("name"),
    } for page in pages]
    returned_bytes = len(json.dumps({"results": projected}, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return {
        "transport": "api", "operation": "read", "status": "measured",
        "sample_size": len(pages), "tool_calls": 1, "sdk_requests": counter["requests"],
        "elapsed_ms": elapsed_ms, "returned_bytes": returned_bytes,
        "model_tokens": None, "model_token_source": "unavailable",
        "metric_source": "Python perf_counter; one SDK query; UTF-8 bytes of four-column projected JSON",
        "evidence": "benchmarks/compare.py api-read; exact Notion filter, four projected columns",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    read = sub.add_parser("api-read")
    read.add_argument("--env-file", type=Path, required=True)
    read.add_argument("--data-source-id", required=True)
    read.add_argument("--cutoff", required=True)
    check = sub.add_parser("validate")
    check.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    if args.command == "api-read":
        print(json.dumps(probe_api_read(env_file=args.env_file, data_source_id=args.data_source_id, cutoff=args.cutoff), ensure_ascii=False))
    else:
        validate_report(json.loads(args.report.read_text(encoding="utf-8")))
        print("report valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
