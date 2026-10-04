# Direct API vs official remote MCP comparison

The default remains the direct Notion API for CoursePilot's unattended, paginated sync. The official remote MCP is an optional interactive connection. Its OAuth connection requires a user session; rows mode has a 100-row ceiling without a cursor, while SQL and saved-view modes have different plan and pagination behavior. See the [official connection guide](https://developers.notion.com/guides/mcp/get-started-with-mcp) and [supported tools](https://developers.notion.com/guides/mcp/mcp-supported-tools).

## Read-only observation, 2026-10-04

Both connections queried the same personal Scheduler data source with `DueDate >= 2026-07-05 OR 상태 != 완료`, projecting URL, title, DueDate start, and status. The API probe used `python benchmarks/compare.py api-read --env-file PATH --data-source-id ID --cutoff 2026-07-05`. The MCP probe used `notion-query-data-sources` SQL with the same predicate. The commands returned 91 rows each. Values are in [observations-2026-10-04.json](observations-2026-10-04.json); run `python benchmarks/compare.py validate benchmarks/observations-2026-10-04.json` to check evidence completeness.

| Connection | Calls measured | Elapsed | UTF-8 result bytes | Model tokens |
|---|---:|---:|---:|---|
| API | 1 agent command / 1 SDK request | 2,197 ms | 15,951 | Unavailable |
| Official remote MCP | 1 MCP call | 570 ms | 15,176 | Unavailable |

The clocks and result paths differ: the API timer wraps a local SDK query, while the MCP timer wraps a remote tool call. SDK response properties were reduced to four columns before byte counting; MCP returned its own JSON wrapper. These are single warm observations, not a controlled speed distribution or a model-token benchmark. The byte counts do not establish a dramatic token difference. Initial target discovery, schema fetch, OAuth setup, and failed exploratory queries are excluded from these figures.

## Approved isolated write experiment, 2026-10-04

The user approved the reviewed experiment by replying `다음 작업으로 진행하자` to the pending approval question. A temporary database named `Scheduler Transport Benchmark 2026-10-04` was created beneath `Setting for Productivity` (`1aa53280-64be-80aa-82dd-dbec867dff44`). Its database ID was `a5f8d215-7dc9-4ce8-a28d-200fc668f6be` and data source ID was `b16c26fa-617d-4560-ab9d-80760cadf080`. It had only the eight planned Scheduler properties: `이름` title; `선택` select (`루틴`, `이벤트`); `구분` multi-select (`벤치마크`); `DueDate` date; `Plan` date; `우선순위` select (existing P1–P4 labels); `상태` status (`시작 전`, `진행 중`, `완료`, `폐기`); and `메모` text. The fourth status option was added to the temporary data source through the API after the remote database creation tool supplied its three defaults. The package schema validator then passed. The original personal Scheduler was never written.

One page was created through each connection. The titles were `API transport test 2026-10-04` and `MCP transport test 2026-10-04`; otherwise both used `선택=이벤트`, `구분=벤치마크`, `DueDate=2026-10-05`, `우선순위=🔵 보통 (P3)`, `상태=시작 전`, and `메모=benchmark initial`, with `Plan` omitted. Each page was then updated with exactly `Plan=2026-10-06`, `상태=진행 중`, and `메모=benchmark updated`. API list and MCP fetch confirmed both final states. A guarded archive call checked the parent, title, single data source, and exactly these two page titles before setting the temporary database `in_trash=true`; a separate retrieve confirmed that state.

| Workload | API CLI | Official remote MCP | Model tokens |
|---|---:|---:|---|
| Create one page | 3,764 ms; 757 JSON bytes | 1,149 ms; 382 tool-result bytes | Unavailable |
| Update three properties | 5,214 ms; 825 JSON bytes | 1,055 ms; 50 tool-result bytes | Unavailable |

Each measured write used one agent-visible command or MCP call. API timings include process startup, target/schema checks, preview construction, and an apply-time reread. The MCP timings cover the write call after the OAuth connection and schema fetch; a pre-update page fetch was excluded. The paths therefore do not form a normalized latency comparison. MCP's write responses were shorter in this run because it returned a compact result while the API CLI returned the preview context. That is an output-contract choice, not a measured model-token saving attributable to MCP transport. The sample size is one per workload. Character counts and UTF-8 bytes are never labeled model tokens.

The decision remains direct API as the default for unattended paginated CoursePilot sync and the standalone skill, with official remote MCP available for authenticated interactive work. The observations demonstrate functional parity for the approved create/update fields and no evidence of a dramatic inherent model-token difference. A real model usage counter and repeated equivalent end-to-end runs would be needed to quantify tokens or latency.

This is a historical observation made with the temporary eight-property schema used by package 0.1.0. The user's personal Scheduler subsequently removed `선택` and added `tag`; package 0.2.0 follows that current schema. The archived benchmark pages and their measurements are not a live 0.2.0 write test.
