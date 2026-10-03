"""Check that skill examples call real CLI commands."""

from pathlib import Path

from notion_scheduler.cli import _parser


def test_documented_commands_parse_and_skill_has_frontmatter():
    skill = Path(__file__).resolve().parents[1] / "skills" / "notion-scheduler" / "SKILL.md"
    content = skill.read_text(encoding="utf-8")
    assert content.startswith("---\nname: notion-scheduler\n")
    assert "CoursePilot" in content
    parser = _parser()
    for args in (
        ["list"],
        ["list", "--status", "시작 전", "--fields", "page_id,title,due_date,status", "--limit", "20"],
        ["create", "--title", "Pay rent", "--category", "개인"],
        ["update", "--page-id", "one", "--plan-date", "2026-10-04", "--status", "진행 중"],
        ["complete", "--page-id", "one", "--apply"],
        ["preview", "create", "--title", "Pay rent"],
    ):
        parser.parse_args(args)
