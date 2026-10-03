# Notion Scheduler JSON contract

All commands write one JSON object to stdout with `schema_version: 1` and `ok: true|false`. Errors return exit code 2 and `error: {code, message}`. Secrets are never returned.

`list` returns `action: "list"`, `tasks`, `count` (returned rows), and `matching_count` (all rows matching filters before `--limit`). By default task records contain `page_id`, `title`, `selection`, `category`, `due_date`, `plan_date`, `priority`, `status`, and `memo`. `--status` matches one exact status; `--contains` matches title text without case; `--limit` must be positive. `--fields` selects a comma-separated subset of those fields, and `page_id` is always returned.

Create, update, and complete return `action`, `dry_run`, `target`, `page_id`, `before`, `properties`, and `result`. Without `--apply`, `dry_run` is true and `result` is null. With `--apply`, `dry_run` is false and `result.id` is the Notion page ID. `properties` contains only fields proposed for a partial update. A create includes defaults for selection, category, priority, and status.

The global `--env-file PATH` option must appear before the subcommand. The CLI reads `NOTION_TOKEN` or `NOTION_API_KEY`, and one of `NOTION_DATA_SOURCE_ID`, `NOTION_DATABASE_ID`, or `NOTION_DATABASE_NAME`.
