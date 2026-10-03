# Direct API vs official remote MCP comparison

The default remains the direct Notion API for CoursePilot's unattended, paginated sync. The official remote MCP is an optional interactive connection. Its OAuth connection requires a user session; rows mode has a 100-row ceiling without a cursor, while SQL and saved-view modes have different plan and pagination behavior. See the [official connection guide](https://developers.notion.com/guides/mcp/get-started-with-mcp) and [supported tools](https://developers.notion.com/guides/mcp/mcp-supported-tools).

## Read-only observation, 2026-10-04

Both connections queried the same personal Scheduler data source with `DueDate >= 2026-07-05 OR 상태 != 완료`, projecting URL, title, DueDate start, and status. The API probe used `python benchmarks/compare.py api-read --env-file PATH --data-source-id ID --cutoff 2026-07-05`. The MCP probe used `notion-query-data-sources` SQL with the same predicate. The commands returned 91 rows each. Values are in [observations-2026-10-04.json](observations-2026-10-04.json); run `python benchmarks/compare.py validate benchmarks/observations-2026-10-04.json` to check evidence completeness.

| Connection | Calls measured | Elapsed | UTF-8 result bytes | Model tokens |
|---|---:|---:|---:|---|
| API | 1 agent command / 1 SDK request | 2,197 ms | 15,951 | Unavailable |
| Official remote MCP | 1 MCP call | 570 ms | 15,176 | Unavailable |

The clocks and result paths differ: the API timer wraps a local SDK query, while the MCP timer wraps a remote tool call. SDK response properties were reduced to four columns before byte counting; MCP returned its own JSON wrapper. These are single warm observations, not a controlled speed distribution or a model-token benchmark. The byte counts do not establish a dramatic token difference. Initial target discovery, schema fetch, OAuth setup, and failed exploratory queries are excluded from these figures.

## Reviewed write experiment still pending

No live create/update measurement has been run. The proposed isolated target is a new database named `Scheduler Transport Benchmark 2026-10-04` under the existing page `Setting for Productivity` (`1aa53280-64be-80aa-82dd-dbec867dff44`). It would contain only the eight Scheduler properties: `이름` title; `선택` select with `루틴` and `이벤트`; `구분` multi-select with `벤치마크`; `DueDate` date; `Plan` date; `우선순위` select with the four existing P1–P4 labels; `상태` status with `시작 전`, `진행 중`, `완료`, `폐기`; and `메모` text. The existing personal Scheduler is read only throughout the experiment.

After the user approves this exact experiment, create one page by each connection. The two pages differ only in title: `API transport test 2026-10-04` and `MCP transport test 2026-10-04`. Both use `선택=이벤트`, `구분=벤치마크`, `DueDate=2026-10-05`, `우선순위=🔵 보통 (P3)`, `상태=시작 전`, and `메모=benchmark initial`; omit `Plan`. Then update each page with exactly `Plan=2026-10-06`, `상태=진행 중`, and `메모=benchmark updated`. Record page IDs, call counts, elapsed time, returned UTF-8 bytes, and any actual model usage counter. The temporary database and pages should be archived after results are checked, under the same approval.

Do not infer write performance from previews, fake SDK tests, or the read-only result. If the connection or approval is unavailable, keep create/update marked `approval_required` or `unavailable`, and leave SCHD-05 and Phase 16.1 incomplete. Character counts and UTF-8 bytes must never be labeled model tokens.
