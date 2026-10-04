# notion-scheduler

Independent Python interface for general tasks in a personal Notion Scheduler. The default transport is the direct Notion API through `notion-client`.

This package has no CoursePilot dependency. Reads and previews are safe; writes require an explicit apply call. The public contract is versioned with the package release.

Version 0.2 follows the current personal Scheduler schema: `이름`, `구분`, `tag`, `DueDate`, `Plan`, `우선순위`, `상태`, and `메모`. The former `선택` property is no longer required or written. `tag` is an optional task value: it can be read or changed explicitly, while CoursePilot academic sync preserves it. The CLI JSON contract is version 2.

## Install and configure

Install from this repository with `pip install .` or `uv tool install .`. Set `NOTION_TOKEN` and one Scheduler target selector: `NOTION_DATA_SOURCE_ID`, `NOTION_DATABASE_ID`, or `NOTION_DATABASE_NAME`. The Notion integration must have access to the target database.

The wheel includes the reusable agent skill in `notion_scheduler/skill`. To install it for Codex, copy that directory to `~/.codex/skills/notion-scheduler` (or your agent's user-level skills directory). For example, after installation:

```powershell
$skillSource = python -c "from pathlib import Path; import notion_scheduler; print(Path(notion_scheduler.__file__).parent / 'skill')"
$codexRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
$skillDestination = Join-Path $codexRoot 'skills/notion-scheduler'
New-Item -ItemType Directory -Force -Path $skillDestination | Out-Null
Copy-Item -LiteralPath (Join-Path $skillSource 'SKILL.md'), (Join-Path $skillSource 'JSON_CONTRACT.md') -Destination $skillDestination
```

See the packaged `SKILL.md` and `JSON_CONTRACT.md` for supported commands and JSON fields.
