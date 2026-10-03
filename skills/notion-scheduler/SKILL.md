---
name: notion-scheduler
description: Read, create, edit, and complete tasks in the user's personal Notion Scheduler, including nonacademic work. Use for Scheduler task management requests; use CoursePilot for LMS collection and academic sync.
---

# Notion Scheduler

Use the `notion-scheduler` CLI to manage the personal Scheduler. The direct Notion API is the default path. Configure `NOTION_TOKEN` and exactly one target selector: `NOTION_DATA_SOURCE_ID`, `NOTION_DATABASE_ID`, or `NOTION_DATABASE_NAME`. The optional global `--env-file PATH` can load these values from a local file. Never print the token or include it in a command response.

## Read and write

- `notion-scheduler list` returns versioned JSON with all Scheduler tasks.
- `notion-scheduler create --title "Pay rent" --category 개인 --due-date 2026-10-05` previews a new task. Add `--apply` only when the user requested the write and the preview matches that request.
- `notion-scheduler update --page-id PAGE_ID --plan-date 2026-10-04 --status '진행 중'` previews a sparse edit. Add `--apply` after checking the target page and changed properties. An exact `--lookup-title` is allowed only when it identifies one page.
- `notion-scheduler complete --page-id PAGE_ID` previews a status change to `완료`; add `--apply` for an authorized completion.
- `notion-scheduler preview create|update|complete` explicitly previews the same operations without applying.

For every write request, inspect the JSON preview and summarize the target page and changed fields. Avoid using a title alone when more than one page matches. Explicit user requests may change `Plan` and `상태`. Omitted fields are preserved. The CLI has no delete or archive command.

## Optional remote MCP

An agent with an authenticated official Notion MCP connection may use it for interactive exploration or a user-directed edit. Its OAuth connection requires interactive authorization, and `notion-query-data-sources` rows mode returns at most 100 rows without a cursor; access can depend on the workspace plan. Use the CLI for complete paginated reads and unattended or bulk sync. Do not treat MCP response length as measured model-token use.

Read [JSON_CONTRACT.md](JSON_CONTRACT.md) when parsing CLI output or building an automation.
